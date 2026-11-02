"""Regression tests for the reliability/bug-fix pass.

These tests cover:
- per-upload artifact isolation
- image-coordinate alignment (small and large images)
- session-state reset / failed-upload deduplication
- duplicate-door graph merging
- NavigationService not requiring a graph JSON artifact
- Ollama status/model caching
- new natural-language query phrasings
- Streamlit quick-example buttons and upload processing path
- CLI error handling
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import pytest

from cv.floorplan_parser import parse_floorplan, save_floorplan_json
from cv.pipeline_config import CVConfig
from cv.models import BoundingBox, Connection, Corridor, FloorPlan, Room
from cv.preprocessing import (
    generate_second_floorplan,
    generate_synthetic_floorplan,
    load_floorplan,
    resize_image,
)
from cv.visualization import visualize_floorplan
from frontend.ui_helpers import draw_route_overlay
from graph.graph_builder import NavigationGraphBuilder
from graph.pathfinder import shortest_path
from llm.ollama_client import OllamaClient
from llm.query_parser import QueryParser
from navigation_service import NavigationService
from utils.config import DEFAULT_MAX_DIMENSION

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _room(idx: int, name: str | None = None) -> Room:
    return Room(
        id=idx,
        name=name or f"Room_{idx}",
        bounding_box=BoundingBox(x=0, y=0, width=10, height=10),
        center=(5, 5),
        width=10,
        height=10,
        area=100,
    )


def _alias_floorplan() -> FloorPlan:
    """Five rooms + one corridor, matching the parser's sample aliases."""
    return FloorPlan(
        image_path="fake/path.png",
        image_width=800,
        image_height=600,
        rooms=[_room(i) for i in range(1, 6)],
        corridors=[
            Corridor(
                id=1,
                name="Corridor_1",
                bounding_box=BoundingBox(x=0, y=0, width=100, height=20),
                center=(50, 10),
                area=2000,
            )
        ],
    )


def _offline_client() -> MagicMock:
    client = MagicMock()
    client.check_availability.return_value = (False, "offline")
    client.is_model_installed.return_value = False
    client.model = "qwen3.5:4b"
    client.timeout = 30
    return client


def _make_image(tmp_path: Path, name: str = "plan.png") -> Path:
    raw_dir = tmp_path / f"raw_{name}"
    raw_dir.mkdir(parents=True, exist_ok=True)
    return generate_synthetic_floorplan(filename=name, output_dir=raw_dir)


# ---------------------------------------------------------------------------
# 1. Per-upload artifact isolation
# ---------------------------------------------------------------------------

def test_parse_floorplan_output_dir_isolation(tmp_path):
    repo_artifact = PROJECT_ROOT / "data" / "processed" / "floorplan.json"
    before = repo_artifact.stat().st_mtime_ns if repo_artifact.exists() else None

    img_a = _make_image(tmp_path / "a", "a.png")
    img_b = generate_second_floorplan(
        filename="b.png", output_dir=tmp_path / "b" / "raw"
    )

    out_a = tmp_path / "out_a"
    out_b = tmp_path / "out_b"
    fp_a = parse_floorplan(img_a, output_dir=out_a)
    fp_b = parse_floorplan(img_b, output_dir=out_b)

    for out_dir in (out_a, out_b):
        assert (out_dir / "floorplan.json").is_file()
        for debug_name in (
            "walls_bin_debug.png",
            "closed_walls_debug.png",
            "rooms_debug.png",
            "doors_debug.png",
            "walls_debug.png",
            "corridors_debug.png",
        ):
            assert (out_dir / debug_name).is_file()

    data_a = json.loads((out_a / "floorplan.json").read_text(encoding="utf-8"))
    data_b = json.loads((out_b / "floorplan.json").read_text(encoding="utf-8"))
    assert data_a["image_path"] != data_b["image_path"]
    assert fp_a.image_path != fp_b.image_path

    after = repo_artifact.stat().st_mtime_ns if repo_artifact.exists() else None
    assert after == before, "parse_floorplan must not write to the shared data/processed dir"


# ---------------------------------------------------------------------------
# 2. Image-coordinate alignment
# ---------------------------------------------------------------------------

def _assert_coordinates_within_floorplan(fp: FloorPlan) -> None:
    for room in fp.rooms:
        b = room.bounding_box
        assert 0 <= b.x < fp.image_width
        assert 0 <= b.y < fp.image_height
        assert b.x2 <= fp.image_width
        assert b.y2 <= fp.image_height
    for door in fp.doors:
        assert 0 <= door.center[0] <= fp.image_width
        assert 0 <= door.center[1] <= fp.image_height


@pytest.mark.parametrize("target_size", [(640, 480), (1600, 1200)], ids=["small", "large"])
def test_image_coordinate_alignment(tmp_path, target_size):
    source = _make_image(tmp_path)
    src_img = load_floorplan(source)
    target = cv2.resize(src_img, target_size, interpolation=cv2.INTER_AREA)
    resized_path = tmp_path / f"resized_{target_size[0]}x{target_size[1]}.png"
    assert cv2.imwrite(str(resized_path), target)

    out_dir = tmp_path / "out"
    fp = parse_floorplan(resized_path, output_dir=out_dir)

    # The parser's coordinate space must match the image we render on.
    processed_img = resize_image(load_floorplan(resized_path), max_dim=DEFAULT_MAX_DIMENSION)
    assert (fp.image_width, fp.image_height) == (
        processed_img.shape[1],
        processed_img.shape[0],
    )
    _assert_coordinates_within_floorplan(fp)

    annotated = visualize_floorplan(fp, processed_img)
    assert annotated.shape == processed_img.shape

    graph = NavigationGraphBuilder(fp).graph
    if graph.number_of_edges() > 0:
        u, v = next(iter(graph.edges()))
        route = shortest_path(graph, u, v)
        overlay = draw_route_overlay(annotated, fp, route)
        assert overlay.shape == annotated.shape


# ---------------------------------------------------------------------------
# 3. Session-state reset and failed-upload deduplication
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app_module():
    """Import frontend.app with Streamlit page-level calls patched out."""
    with patch("streamlit.set_page_config"), patch("streamlit.markdown"):
        import frontend.app as module
        module = importlib.reload(module)
    return module


def test_reset_processing_state_clears_stale_results(app_module):
    state = {key: object() for key in app_module.PROCESSING_STATE_KEYS}
    state["upload_hash"] = "old-hash"

    assert app_module._begin_upload(state, "new-hash") is True
    for key in app_module.PROCESSING_STATE_KEYS:
        assert state[key] is None
    assert state["upload_hash"] == "new-hash"

    # A failed upload must not be reprocessed on the next rerun.
    assert app_module._begin_upload(state, "new-hash") is False

    # ...but stale results can still be explicitly cleared.
    state["floorplan"] = "stale"
    state["nav_result"] = {"status": "success"}
    state["route_img_bytes"] = b"stale"
    app_module._reset_processing_state(state)
    assert state["floorplan"] is None
    assert state["nav_result"] is None
    assert state["route_img_bytes"] is None
    assert state["upload_hash"] == "new-hash"


# ---------------------------------------------------------------------------
# 4. Duplicate doors between the same two regions
# ---------------------------------------------------------------------------

def test_duplicate_doors_are_merged_and_shortest_is_canonical():
    fp = FloorPlan(
        image_path="fake.png",
        image_width=800,
        image_height=600,
        rooms=[_room(1), _room(2)],
        connections=[
            Connection(source="Room_1", destination="Room_2", via_door="Door_1", distance=100.0),
            Connection(source="Room_1", destination="Room_2", via_door="Door_2", distance=60.0),
            Connection(source="Room_1", destination="Room_2", via_door="Door_1", distance=100.0),
        ],
    )
    graph = NavigationGraphBuilder(fp).graph

    assert graph.number_of_edges() == 1
    data = graph["Room_1"]["Room_2"]
    assert data["weight"] == 60.0
    assert data["distance"] == 60.0
    assert data["door_id"] == "Door_2"
    assert set(data["doors"]) == {"Door_1", "Door_2"}

    route = shortest_path(graph, "Room_1", "Room_2")
    assert route.doors == ["Door_2"]


# ---------------------------------------------------------------------------
# 5. NavigationService only needs floorplan.json
# ---------------------------------------------------------------------------

def test_navigation_service_does_not_require_graph_json(tmp_path):
    fp = FloorPlan(
        image_path="fake.png",
        image_width=800,
        image_height=600,
        rooms=[_room(1), _room(2)],
        connections=[
            Connection(source="Room_1", destination="Room_2", via_door="Door_1", distance=50.0)
        ],
    )
    fp_path = tmp_path / "floorplan.json"
    save_floorplan_json(fp, fp_path)
    assert not (tmp_path / "navigation_graph.json").exists()

    service = NavigationService(
        floorplan_path=fp_path,
        ollama_client=_offline_client(),
        auto_load=True,
    )
    assert service.graph is not None
    assert service.graph.has_edge("Room_1", "Room_2")


# ---------------------------------------------------------------------------
# 6. Ollama status/model caching
# ---------------------------------------------------------------------------

@patch("urllib.request.urlopen")
def test_ollama_status_and_model_results_are_cached(mock_urlopen):
    response = MagicMock()
    response.status = 200
    response.read.return_value = json.dumps(
        {"models": [{"name": "qwen3.5:4b"}]}
    ).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = response

    client = OllamaClient(base_url="http://localhost:11434")

    assert client.check_availability()[0] is True
    assert client.check_availability()[0] is True
    assert mock_urlopen.call_count == 1

    assert client.list_models() == ["qwen3.5:4b"]
    assert client.list_models() == ["qwen3.5:4b"]
    assert mock_urlopen.call_count == 2

    client.clear_cache()
    client.check_availability()
    assert mock_urlopen.call_count == 3


# ---------------------------------------------------------------------------
# 7. Query parsing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "query,source,destination",
    [
        ("How do I get from Reception to Room 104?", "Room_1", "Room_5"),
        ("Navigate from Room 101 to Room 102.", "Room_2", "Room_3"),
        ("Find a route from Room_1 to Room_5.", "Room_1", "Room_5"),
        ("How do I reach the corridor from Room 103?", "Room_4", "Corridor_1"),
        ("How do I get to Room 104 from Reception?", "Room_1", "Room_5"),
        ("Walk to Room 102 from Room 101.", "Room_2", "Room_3"),
    ],
)
def test_query_parser_valid_phrasings(query, source, destination):
    parser = QueryParser(floorplan=_alias_floorplan())
    parsed = parser.parse(query)
    assert parsed.is_valid, parsed.clarification_needed
    assert parsed.source == source
    assert parsed.destination == destination


def test_query_parser_missing_destination():
    parser = QueryParser(floorplan=_alias_floorplan())
    parsed = parser.parse("Navigate to Room 104.")
    assert not parsed.is_valid
    assert parsed.source is None
    assert parsed.destination == "Room_5"
    assert "starting from" in (parsed.clarification_needed or "")


def test_query_parser_unknown_start_room():
    parser = QueryParser(floorplan=_alias_floorplan())
    parsed = parser.parse("Navigate from Hogwarts to Room 101.")
    assert not parsed.is_valid
    assert parsed.source is None
    assert "Unrecognized starting location 'Hogwarts'" in (
        parsed.clarification_needed or ""
    )


def test_query_parser_unknown_destination():
    parser = QueryParser(floorplan=_alias_floorplan())
    parsed = parser.parse("Navigate from Room_1 to Narnia.")
    assert not parsed.is_valid
    assert parsed.source == "Room_1"
    assert parsed.destination is None
    assert "Unrecognized destination 'Narnia'" in (
        parsed.clarification_needed or ""
    )


def test_demo_aliases_do_not_leak_to_larger_uploaded_plan():
    floorplan = FloorPlan(
        image_path="uploaded/mall.png",
        image_width=800,
        image_height=600,
        rooms=[_room(i) for i in range(1, 7)],
        corridors=[
            Corridor(
                id=1,
                name="Corridor_1",
                bounding_box=BoundingBox(x=0, y=0, width=100, height=20),
                center=(50, 10),
                area=2000,
            )
        ],
    )
    parser = QueryParser(floorplan=floorplan)

    assert parser.resolve_node_id("Reception") is None
    assert parser.resolve_node_id("Room 101") is None
    parsed = parser.parse("How do I get from Reception to Room 6?")
    assert not parsed.is_valid
    assert "Unrecognized starting location 'Reception'" in (
        parsed.clarification_needed or ""
    )


# ---------------------------------------------------------------------------
# 8. Streamlit quick-example buttons and upload-processing path
# ---------------------------------------------------------------------------

def test_quick_example_buttons_do_not_crash():
    pytest.importorskip("streamlit.testing.v1")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(
        str(PROJECT_ROOT / "frontend" / "app.py"), default_timeout=300
    )
    at.run()
    assert not at.exception

    demo_buttons = [b for b in at.sidebar.button if "Load Demo" in b.label]
    assert demo_buttons, "demo button not found"
    demo_buttons[0].click()
    at.run()
    assert not at.exception

    example_buttons = [b for b in at.button if b.label.startswith('"')]
    assert len(example_buttons) == 4

    for idx in range(len(example_buttons)):
        buttons = [b for b in at.button if b.label.startswith('"')]
        expected = buttons[idx].label.strip('"')
        buttons[idx].click()
        at.run()
        assert not at.exception, f"example button {idx} crashed: {[str(e.value) for e in at.exception]}"
        assert at.session_state["nav_query_input"] == expected


def test_frontend_processes_an_uploaded_image(tmp_path):
    pytest.importorskip("streamlit.testing.v1")
    from streamlit.testing.v1 import AppTest

    image_path = _make_image(tmp_path, "upload.png")
    workdir = tmp_path / "work"

    script = f"""
import sys
sys.path.insert(0, {str(PROJECT_ROOT)!r})
import streamlit as st
from pathlib import Path
from frontend.app import _process_floorplan

_process_floorplan(Path({str(image_path)!r}), Path({str(workdir)!r}))
st.write("processed")
"""
    at = AppTest.from_string(script, default_timeout=300)
    at.run()

    assert not at.exception, [str(e.value) for e in at.exception]
    fp = at.session_state["floorplan"]
    assert fp is not None
    assert len(fp.rooms) >= 5
    assert (workdir / "floorplan.json").is_file()
    assert (workdir / "navigation_graph.json").is_file()
    assert at.session_state["annotated_img_bytes"]


# ---------------------------------------------------------------------------
# 9. CLI error handling
# ---------------------------------------------------------------------------

def test_cli_invalid_direct_route_prints_error(monkeypatch, capsys, tmp_path):
    import main as main_mod

    fp = FloorPlan(
        image_path="fake.png",
        image_width=800,
        image_height=600,
        rooms=[_room(1), _room(2)],
        connections=[
            Connection(source="Room_1", destination="Room_2", via_door="Door_1", distance=50.0)
        ],
    )
    fp_path = tmp_path / "floorplan.json"
    save_floorplan_json(fp, fp_path)

    client = _offline_client()
    service = NavigationService(floorplan_path=fp_path, ollama_client=client)

    monkeypatch.setattr(main_mod, "OllamaClient", lambda: client)
    monkeypatch.setattr(main_mod, "NavigationService", lambda **kwargs: service)
    monkeypatch.setattr(
        sys,
        "argv",
        ["main.py", "--source", "Nope", "--destination", "Room_1", "--no-llm"],
    )

    main_mod.main()  # must not raise

    out = capsys.readouterr().out
    assert "Status:" in out and "Error" in out
    assert "Nope" in out
    assert "Traceback" not in out


def test_cli_partial_direct_arguments_are_rejected(monkeypatch):
    import main as main_mod

    monkeypatch.setattr(sys, "argv", ["main.py", "--source", "Room_1", "--no-llm"])
    with pytest.raises(SystemExit) as exc_info:
        main_mod.main()
    assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# 10. parse_floorplan accepts string paths (README-documented usage)
# ---------------------------------------------------------------------------

def test_parse_floorplan_accepts_string_image_path(tmp_path):
    img_path = _make_image(tmp_path / "raw", "strpath.png")

    fp_path = parse_floorplan(img_path, output_dir=tmp_path / "out_path",
                              config=CVConfig(debug=False))
    fp_str = parse_floorplan(str(img_path), output_dir=tmp_path / "out_str",
                             config=CVConfig(debug=False))

    assert fp_path.rooms and fp_str.rooms
    assert len(fp_path.rooms) == len(fp_str.rooms)
    assert len(fp_path.doors) == len(fp_str.doors)
    assert len(fp_path.connections) == len(fp_str.connections)
