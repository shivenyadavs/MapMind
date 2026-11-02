from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import cv2
import networkx as nx
import numpy as np
import pytest

from cv.coordinates import scale_floorplan_to_source
from cv.floorplan_parser import (
    _assign_semantic_labels,
    _binarise_walls,
    _close_wall_gaps,
    _segment_regions,
    _select_closed_walls,
    _suppress_text_artifacts,
    parse_floorplan,
)
from cv.models import BoundingBox, Connection, Corridor, FloorPlan, Room
from cv.ocr import OCRToken, extract_text_tokens
from cv.pipeline_config import CVConfig
from cv.preprocessing import generate_synthetic_floorplan
from graph.graph_builder import NavigationGraphBuilder
from graph.pathfinder import shortest_path


@pytest.fixture(scope="module")
def synthetic_parse(tmp_path_factory):
    base_dir = tmp_path_factory.mktemp("cv_synthetic")
    image_path = generate_synthetic_floorplan(
        width=800,
        height=600,
        filename="synthetic.png",
        output_dir=base_dir,
    )
    out_dir = base_dir / "processed"
    return parse_floorplan(image_path, output_dir=out_dir), out_dir


def test_synthetic_plan_has_consistent_door_pairs_and_graph(synthetic_parse):
    fp, _ = synthetic_parse
    assert len(fp.rooms) == 5
    assert len(fp.corridors) == 1
    assert len(fp.doors) == 6

    pairs = [tuple(sorted(door.connected_regions)) for door in fp.doors]
    assert len(pairs) == len(set(pairs)), f"duplicate region-pair doors: {pairs}"

    valid_regions = {room.name for room in fp.rooms} | {
        corridor.name for corridor in fp.corridors
    }
    assert all(conn.source in valid_regions for conn in fp.connections)
    assert all(conn.destination in valid_regions for conn in fp.connections)

    graph = NavigationGraphBuilder(fp).graph
    assert nx.is_connected(graph)
    assert graph.graph["isolated_nodes"] == []


def test_ambiguous_door_uses_regions_on_its_opening_axis(tmp_path):
    image_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "raw"
        / "apartment_floorplan.png"
    )
    fp = parse_floorplan(
        image_path,
        output_dir=tmp_path / "apartment",
        config=CVConfig(debug=False),
    )

    pairs = {tuple(sorted(door.connected_regions)) for door in fp.doors}
    assert ("Corridor_1", "Room_3") in pairs

    graph = NavigationGraphBuilder(fp).graph
    route = shortest_path(graph, "Room_2", "Room_3")
    assert route.path == ["Room_2", "Corridor_1", "Room_3"]


def test_source_coordinates_round_trip_and_debug_overlay(tmp_path):
    raw_dir = tmp_path / "raw"
    base_path = generate_synthetic_floorplan(
        width=800,
        height=600,
        filename="base.png",
        output_dir=raw_dir,
    )
    base = cv2.imread(str(base_path))
    upscaled = cv2.resize(base, (1600, 1200), interpolation=cv2.INTER_NEAREST)
    upscaled_path = raw_dir / "upscaled.png"
    assert cv2.imwrite(str(upscaled_path), upscaled)
    out_dir = tmp_path / "processed"

    fp = parse_floorplan(upscaled_path, output_dir=out_dir)
    assert fp.source_width == 1600
    assert fp.source_height == 1200
    assert fp.image_width == 1200
    assert fp.image_height == 900
    assert fp.processing_scale_x == pytest.approx(0.75)
    assert fp.processing_scale_y == pytest.approx(0.75)
    assert fp.diagnostics["source_size"] == [1600, 1200]
    assert fp.diagnostics["working_size"] == [1200, 900]
    assert (out_dir / "source_overlay_debug.png").exists()

    source_fp = scale_floorplan_to_source(fp)
    assert source_fp.image_width == 1600
    assert source_fp.image_height == 1200
    assert source_fp.processing_scale_x == 1.0
    for room in source_fp.rooms:
        assert 0 <= room.bounding_box.x < room.bounding_box.x2 <= 1600
        assert 0 <= room.bounding_box.y < room.bounding_box.y2 <= 1200
    for door in source_fp.doors:
        assert 0 <= door.center[0] <= 1600
        assert 0 <= door.center[1] <= 1200


def test_config_controls_working_resolution_and_debug_output(tmp_path):
    image_path = generate_synthetic_floorplan(
        width=800,
        height=600,
        filename="config.png",
        output_dir=tmp_path / "raw",
    )
    out_dir = tmp_path / "processed"
    fp = parse_floorplan(
        image_path,
        output_dir=out_dir,
        config=CVConfig(max_dimension=400, debug=False),
    )

    assert max(fp.image_width, fp.image_height) == 400
    assert fp.diagnostics["config"]["max_dimension"] == 400
    assert fp.diagnostics["working_size"] == [400, 300]
    assert not (out_dir / "rooms_debug.png").exists()


@pytest.mark.parametrize("kind", ["blank", "noise", "wide"])
def test_degenerate_images_return_valid_empty_models(tmp_path, kind):
    if kind == "blank":
        image = np.full((120, 80, 3), 255, dtype=np.uint8)
    elif kind == "noise":
        rng = np.random.default_rng(0)
        image = rng.integers(0, 256, (120, 80, 3), dtype=np.uint8)
    else:
        image = np.full((80, 1000, 3), 255, dtype=np.uint8)
    image_path = tmp_path / f"{kind}.png"
    assert cv2.imwrite(str(image_path), image)

    fp = parse_floorplan(image_path, output_dir=tmp_path / kind)

    assert fp.image_width == image.shape[1]
    assert fp.image_height == image.shape[0]
    assert fp.rooms == []
    assert fp.corridors == []
    assert fp.doors == []
    assert fp.connections == []
    graph = NavigationGraphBuilder(fp).graph
    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0


def _label_component(x: int, y: int, width: int = 30, height: int = 8) -> np.ndarray:
    patch = np.zeros((height, width), dtype=np.uint8)
    patch[::2, :] = 1
    patch[:, :2] = 1
    return patch


def test_isolated_text_labels_are_removed_from_wall_mask():
    mask = np.zeros((400, 400), dtype=np.uint8)
    mask[40:360, 60:66] = 255

    isolated = _label_component(250, 200)
    mask[200:208, 250:280] = isolated * 255

    near_wall = _label_component(70, 200)
    mask[200:208, 70:100] = near_wall * 255

    cleaned = _suppress_text_artifacts(mask, CVConfig())

    assert np.all(cleaned[40:360, 60:66] == 255)
    assert np.all(cleaned[200:208, 250:280] == 0)
    assert np.any(cleaned[200:208, 70:100] == 255)


def test_adaptive_gap_maximises_valid_region_count(tmp_path):
    image_path = generate_synthetic_floorplan(
        width=800,
        height=600,
        filename="adaptive.png",
        output_dir=tmp_path,
    )
    image = cv2.imread(str(image_path))
    cfg = CVConfig()
    walls_bin, door_boxes = _binarise_walls(image, cfg)
    selected = _select_closed_walls(walls_bin, door_boxes, cfg)

    selected_rooms, selected_corridors, _ = _segment_regions(
        selected, walls_bin, cfg
    )
    selected_count = len(selected_rooms) + len(selected_corridors)

    candidate_counts = []
    for ratio in cfg.segmentation_gap_candidates:
        candidate_cfg = replace(
            cfg, segmentation_gap_ratio=ratio, adaptive_segmentation=False
        )
        closed = _close_wall_gaps(walls_bin, door_boxes, candidate_cfg)
        rooms, corridors, _ = _segment_regions(closed, walls_bin, candidate_cfg)
        candidate_counts.append(len(rooms) + len(corridors))

    assert selected_count == max(candidate_counts)
    assert selected_count > candidate_counts[0]

    fixed = _select_closed_walls(
        walls_bin,
        door_boxes,
        replace(cfg, adaptive_segmentation=False, segmentation_gap_ratio=0.09),
    )
    expected = _close_wall_gaps(
        walls_bin,
        door_boxes,
        replace(cfg, adaptive_segmentation=False, segmentation_gap_ratio=0.09),
    )
    assert np.array_equal(fixed, expected)


def _region_data_for_labels() -> tuple[Room, Corridor, dict]:
    room_mask = np.zeros((100, 220), dtype=np.uint8)
    room_mask[10:90, 10:90] = 1
    corridor_mask = np.zeros((100, 220), dtype=np.uint8)
    corridor_mask[10:90, 120:210] = 1
    room = Room(
        id=1,
        name="Room_1",
        bounding_box=BoundingBox(x=10, y=10, width=80, height=80),
        center=(50, 50),
        width=80,
        height=80,
        area=6400,
    )
    corridor = Corridor(
        id=1,
        name="Corridor_1",
        bounding_box=BoundingBox(x=120, y=10, width=90, height=80),
        center=(165, 50),
        area=7200,
    )
    region_data = {
        "Room_1": {"type": "room", "mask": room_mask},
        "Corridor_1": {"type": "corridor", "mask": corridor_mask},
    }
    return room, corridor, region_data


def test_ocr_line_grouping_and_semantic_assignment():
    room, corridor, region_data = _region_data_for_labels()
    tokens = [
        OCRToken(text="Mall", confidence=92.0, bbox=(20, 30, 20, 10), line_key="1:1:1"),
        OCRToken(text="Office", confidence=88.0, bbox=(45, 30, 35, 10), line_key="1:1:1"),
    ]

    updated = _assign_semantic_labels([room], [corridor], region_data, tokens)

    assert room.name == "Mall Office"
    assert room.semantic_label == "Mall Office"
    assert room.label_source == "ocr"
    assert room.classification_confidence > 0
    assert "Mall Office" in updated


def test_unknown_ocr_text_is_kept_without_fake_classification():
    room, corridor, region_data = _region_data_for_labels()
    tokens = [
        OCRToken(text="ZARA", confidence=91.0, bbox=(25, 30, 30, 12), line_key="1:1:1"),
    ]

    _assign_semantic_labels([room], [corridor], region_data, tokens)

    assert room.name == "ZARA"
    assert room.semantic_label == "ZARA"
    assert room.label_source == "ocr"
    assert room.classification_confidence == 0.0


def test_ocr_injected_backend_filters_numeric_text():
    image = np.zeros((40, 80, 3), dtype=np.uint8)

    def backend(_image):
        return {
            "text": ["Restroom", "1234"],
            "conf": [95.0, 99.0],
            "left": [5, 40],
            "top": [5, 5],
            "width": [35, 30],
            "height": [12, 12],
            "block_num": [1, 1],
            "par_num": [1, 1],
            "line_num": [1, 1],
        }

    tokens, diagnostics = extract_text_tokens(image, backend=backend)

    assert diagnostics["available"] is True
    assert diagnostics["backend"] == "injected"
    assert [token.text for token in tokens] == ["Restroom"]


def test_graph_rejects_missing_endpoints_and_reports_isolated_nodes():
    room_1 = Room(
        id=1,
        name="Room_1",
        bounding_box=BoundingBox(x=0, y=0, width=40, height=40),
        center=(20, 20),
        width=40,
        height=40,
        area=1600,
    )
    room_2 = Room(
        id=2,
        name="Room_2",
        bounding_box=BoundingBox(x=60, y=0, width=40, height=40),
        center=(80, 20),
        width=40,
        height=40,
        area=1600,
    )
    fp = FloorPlan(
        image_path="synthetic.png",
        image_width=100,
        image_height=100,
        rooms=[room_1, room_2],
        connections=[
            Connection(
                source="Room_1",
                destination="Missing_Room",
                via_door="Door_1",
                distance=10.0,
            ),
            Connection(
                source="Room_2",
                destination="Room_2",
                via_door="Door_2",
                distance=5.0,
            ),
        ],
    )

    graph = NavigationGraphBuilder(fp).graph

    assert "Missing_Room" not in graph
    assert graph.number_of_edges() == 0
    assert graph.graph["isolated_nodes"] == ["Room_1", "Room_2"]
    assert any("Missing_Room" in warning for warning in graph.graph["warnings"])
    assert len(graph.graph["rejected_connections"]) == 2
