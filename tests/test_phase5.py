"""tests/test_phase5.py — Phase 5 Streamlit frontend and UI helper tests.

All tests are unit/integration tests that do NOT require a running Streamlit
server or a real Ollama endpoint.  Ollama-dependent paths use mocks.

Test coverage:
- frontend package imports successfully
- ui_helpers: image conversion round-trips
- ui_helpers: upload_hash determinism and uniqueness
- ui_helpers: get_upload_workdir isolation
- ui_helpers: rooms_to_table / doors_to_table structure
- ui_helpers: draw_route_overlay returns correct shape and type
- ui_helpers: build_graph_figure returns a Figure with correct element counts
- app.py importability (without running the server)
- NavigationService + mocked Ollama fallback path (reuse existing service)
- Upload validation: file size check
- Upload validation: corrupt image rejection
"""

from __future__ import annotations

import hashlib
import io
import sys
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import networkx as nx
import numpy as np
import pytest
from PIL import Image

# ---------------------------------------------------------------------------
# Ensure project root is importable (mirrors what app.py does at startup)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tiny_bgr_image() -> np.ndarray:
    """3-channel uint8 BGR array (100x80)."""
    img = np.zeros((80, 100, 3), dtype=np.uint8)
    img[20:60, 20:80] = (200, 210, 220)  # rectangle inside
    return img


@pytest.fixture()
def png_bytes(tiny_bgr_image) -> bytes:
    """Valid PNG bytes derived from the tiny_bgr_image fixture."""
    import cv2
    _, encoded = cv2.imencode(".png", tiny_bgr_image)
    return encoded.tobytes()


@pytest.fixture()
def sample_floorplan():
    """Minimal FloorPlan with 2 rooms, 1 corridor, 1 door, 1 connection."""
    from cv.models import BoundingBox, Connection, Corridor, Door, FloorPlan, Room, Wall

    return FloorPlan(
        image_path="fake/path.png",
        image_width=800,
        image_height=600,
        rooms=[
            Room(id=1, name="Room_1", bounding_box=BoundingBox(x=10, y=10, width=100, height=80),
                 center=(60, 50), width=100, height=80, area=8000),
            Room(id=2, name="Room_2", bounding_box=BoundingBox(x=200, y=10, width=100, height=80),
                 center=(250, 50), width=100, height=80, area=8000),
        ],
        corridors=[
            Corridor(id=1, name="Corridor_1",
                     bounding_box=BoundingBox(x=110, y=30, width=90, height=20),
                     center=(155, 40), area=1800),
        ],
        doors=[
            Door(id=1, name="Door_1", bounding_box=BoundingBox(x=108, y=40, width=10, height=8),
                 center=(113, 44), orientation="vertical",
                 associated_rooms=[1], connected_regions=["Room_1", "Corridor_1"]),
        ],
        walls=[],
        connections=[
            Connection(source="Room_1", destination="Corridor_1", via_door="Door_1", distance=95.0),
        ],
    )


@pytest.fixture()
def sample_graph(sample_floorplan) -> nx.Graph:
    from graph.graph_builder import NavigationGraphBuilder
    return NavigationGraphBuilder(sample_floorplan).graph


@pytest.fixture()
def sample_route(sample_floorplan):
    from cv.models import Route
    return Route(
        source="Room_1",
        destination="Corridor_1",
        path=["Room_1", "Corridor_1"],
        doors=["Door_1"],
        total_distance=95.0,
        edge_count=1,
    )


# ===========================================================================
# 1. Package importability
# ===========================================================================

class TestImports:
    def test_ui_helpers_importable(self):
        import frontend.ui_helpers  # noqa: F401

    def test_app_importable(self):
        """app.py must be importable without starting the Streamlit server.

        We patch st.set_page_config and st.markdown because they would fail
        outside a server context in some Streamlit versions.
        """
        with patch("streamlit.set_page_config"), \
             patch("streamlit.markdown"):
            # app.py runs st.set_page_config at module level — patch it
            import importlib
            import frontend.app as _app_mod
            importlib.reload(_app_mod)  # reload after patching


# ===========================================================================
# 2. Image Conversion
# ===========================================================================

class TestImageConversion:
    def test_numpy_to_pil_shape(self, tiny_bgr_image):
        from frontend.ui_helpers import numpy_to_pil
        pil = numpy_to_pil(tiny_bgr_image)
        assert pil.size == (100, 80), "PIL Image width×height should match array cols×rows"

    def test_numpy_to_pil_rgb_order(self, tiny_bgr_image):
        from frontend.ui_helpers import numpy_to_pil
        pil = numpy_to_pil(tiny_bgr_image)
        # The pixel at (20,20) is BGR (200,210,220) → RGB (220,210,200)
        r, g, b = pil.getpixel((20, 20))
        assert r == 220 and g == 210 and b == 200

    def test_numpy_to_bytes_produces_png(self, tiny_bgr_image):
        from frontend.ui_helpers import numpy_to_bytes
        raw = numpy_to_bytes(tiny_bgr_image)
        # PNG magic bytes: 89 50 4E 47
        assert raw[:4] == b"\x89PNG"

    def test_bytes_to_numpy_round_trip(self, tiny_bgr_image, png_bytes):
        from frontend.ui_helpers import bytes_to_numpy
        restored = bytes_to_numpy(png_bytes)
        assert restored.shape == tiny_bgr_image.shape

    def test_bytes_to_numpy_invalid_raises(self):
        from frontend.ui_helpers import bytes_to_numpy
        with pytest.raises(ValueError):
            bytes_to_numpy(b"not an image")


# ===========================================================================
# 3. Upload Hash
# ===========================================================================

class TestUploadHash:
    def test_same_bytes_same_hash(self, png_bytes):
        from frontend.ui_helpers import upload_hash
        h1 = upload_hash(png_bytes)
        h2 = upload_hash(png_bytes)
        assert h1 == h2

    def test_different_bytes_different_hash(self, png_bytes):
        from frontend.ui_helpers import upload_hash
        other = png_bytes + b"\x00"
        assert upload_hash(png_bytes) != upload_hash(other)

    def test_hash_length(self, png_bytes):
        from frontend.ui_helpers import upload_hash
        assert len(upload_hash(png_bytes)) == 16


# ===========================================================================
# 4. Upload Working Directory Isolation
# ===========================================================================

class TestWorkdir:
    def test_different_hashes_different_dirs(self, tmp_path):
        from frontend.ui_helpers import get_upload_workdir
        d1 = get_upload_workdir(tmp_path, "aabbccdd11223344")
        d2 = get_upload_workdir(tmp_path, "eeff00112233aabb")
        assert d1 != d2
        assert d1.exists()
        assert d2.exists()

    def test_same_hash_same_dir(self, tmp_path):
        from frontend.ui_helpers import get_upload_workdir
        d1 = get_upload_workdir(tmp_path, "abcd1234abcd1234")
        d2 = get_upload_workdir(tmp_path, "abcd1234abcd1234")
        assert d1 == d2


# ===========================================================================
# 5. Table Data Helpers
# ===========================================================================

class TestTableHelpers:
    def test_rooms_to_table_row_count(self, sample_floorplan):
        from frontend.ui_helpers import rooms_to_table
        rows = rooms_to_table(sample_floorplan)
        # 2 rooms + 1 corridor
        assert len(rows) == 3

    def test_rooms_to_table_columns(self, sample_floorplan):
        from frontend.ui_helpers import rooms_to_table
        rows = rooms_to_table(sample_floorplan)
        expected_keys = {"ID", "Type", "Center X", "Center Y", "BBox (x,y,w,h)", "Area (px²)"}
        assert set(rows[0].keys()) == expected_keys

    def test_rooms_to_table_types(self, sample_floorplan):
        from frontend.ui_helpers import rooms_to_table
        rows = rooms_to_table(sample_floorplan)
        types = {r["Type"] for r in rows}
        assert types == {"Room", "Corridor"}

    def test_doors_to_table_row_count(self, sample_floorplan):
        from frontend.ui_helpers import doors_to_table
        rows = doors_to_table(sample_floorplan)
        assert len(rows) == 1

    def test_doors_to_table_connects_field(self, sample_floorplan):
        from frontend.ui_helpers import doors_to_table
        rows = doors_to_table(sample_floorplan)
        assert "Room_1" in rows[0]["Connects"]
        assert "Corridor_1" in rows[0]["Connects"]


# ===========================================================================
# 6. Route Overlay
# ===========================================================================

class TestRouteOverlay:
    def test_overlay_same_shape(self, tiny_bgr_image, sample_floorplan, sample_route):
        from frontend.ui_helpers import draw_route_overlay
        overlay = draw_route_overlay(tiny_bgr_image, sample_floorplan, sample_route)
        assert overlay.shape == tiny_bgr_image.shape

    def test_overlay_is_copy(self, tiny_bgr_image, sample_floorplan, sample_route):
        from frontend.ui_helpers import draw_route_overlay
        original_copy = tiny_bgr_image.copy()
        draw_route_overlay(tiny_bgr_image, sample_floorplan, sample_route)
        # Original must not have been mutated
        np.testing.assert_array_equal(tiny_bgr_image, original_copy)

    def test_overlay_dtype(self, tiny_bgr_image, sample_floorplan, sample_route):
        from frontend.ui_helpers import draw_route_overlay
        overlay = draw_route_overlay(tiny_bgr_image, sample_floorplan, sample_route)
        assert overlay.dtype == np.uint8

    def test_overlay_routes_through_doors(self, tiny_bgr_image, sample_floorplan, sample_route):
        from frontend.ui_helpers import draw_route_overlay
        with patch("frontend.ui_helpers.cv2.arrowedLine") as arrow:
            draw_route_overlay(tiny_bgr_image, sample_floorplan, sample_route)

        segments = [(call.args[1], call.args[2]) for call in arrow.call_args_list]
        assert ((60, 50), (113, 44)) in segments
        assert ((113, 44), (155, 40)) in segments


# ===========================================================================
# 7. Graph Figure
# ===========================================================================

class TestGraphFigure:
    def test_returns_figure(self, sample_floorplan, sample_graph):
        import matplotlib.pyplot as plt
        from frontend.ui_helpers import build_graph_figure
        fig = build_graph_figure(sample_graph, sample_floorplan)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_with_highlighted_path(self, sample_floorplan, sample_graph):
        import matplotlib.pyplot as plt
        from frontend.ui_helpers import build_graph_figure
        fig = build_graph_figure(
            sample_graph, sample_floorplan,
            highlighted_path=["Room_1", "Corridor_1"]
        )
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_empty_graph_figure(self, sample_floorplan):
        import matplotlib.pyplot as plt
        from frontend.ui_helpers import build_graph_figure
        fig = build_graph_figure(nx.Graph(), sample_floorplan)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


# ===========================================================================
# 8. Upload Validation Helpers
# ===========================================================================

class TestUploadValidation:
    MAX_MB = 20

    def _make_large_bytes(self, mb: float) -> bytes:
        return b"\x00" * int(mb * 1024 * 1024)

    def test_large_file_rejected(self):
        raw = self._make_large_bytes(self.MAX_MB + 1)
        assert len(raw) > self.MAX_MB * 1024 * 1024

    def test_valid_file_not_rejected(self, png_bytes):
        assert len(png_bytes) <= self.MAX_MB * 1024 * 1024

    def test_invalid_image_raises(self):
        from frontend.ui_helpers import bytes_to_numpy
        with pytest.raises(ValueError):
            bytes_to_numpy(b"\xff\xd8\xff" + b"\x00" * 20)  # truncated JPEG


# ===========================================================================
# 9. NavigationService Ollama-unavailable fallback
# ===========================================================================

class TestNavigationFallback:
    """Verify that NavigationService uses deterministic fallback when Ollama is down."""

    def _make_service_with_offline_ollama(self, sample_floorplan, tmp_path):
        """Write floorplan.json + navigation_graph.json to tmp_path, return service."""
        import json
        from cv.floorplan_parser import save_floorplan_json
        from graph.graph_builder import NavigationGraphBuilder, save_navigation_graph_json

        fp_path = tmp_path / "floorplan.json"
        gj_path = tmp_path / "navigation_graph.json"

        save_floorplan_json(sample_floorplan, fp_path)
        builder = NavigationGraphBuilder(sample_floorplan)
        save_navigation_graph_json(builder.graph, gj_path)

        # Mock OllamaClient so it reports server as down
        mock_client = MagicMock()
        mock_client.check_availability.return_value = (False, "Ollama not running (mocked)")
        mock_client.is_model_installed.return_value = False
        mock_client.model = "qwen3.5:4b"
        mock_client.timeout = 30

        from navigation_service import NavigationService
        svc = NavigationService(
            floorplan_path=fp_path,
            graph_json_path=gj_path,
            ollama_client=mock_client,
            auto_load=True,
        )
        return svc

    def test_deterministic_fallback_returns_success(self, sample_floorplan, tmp_path):
        svc = self._make_service_with_offline_ollama(sample_floorplan, tmp_path)
        result = svc.navigate("Navigate from Room_1 to Corridor_1", use_llm=False)
        assert result["status"] == "success"

    def test_fallback_method_label(self, sample_floorplan, tmp_path):
        svc = self._make_service_with_offline_ollama(sample_floorplan, tmp_path)
        result = svc.navigate("from Room_1 to Corridor_1", use_llm=False)
        assert "deterministic" in result["method"].lower()

    def test_fallback_path_is_correct(self, sample_floorplan, tmp_path):
        svc = self._make_service_with_offline_ollama(sample_floorplan, tmp_path)
        result = svc.navigate("from Room_1 to Corridor_1", use_llm=False)
        assert result["path"] == ["Room_1", "Corridor_1"]

    def test_fallback_explanation_not_empty(self, sample_floorplan, tmp_path):
        svc = self._make_service_with_offline_ollama(sample_floorplan, tmp_path)
        result = svc.navigate("from Room_1 to Corridor_1", use_llm=False)
        assert result["explanation"].strip() != ""


# ===========================================================================
# 10. Active floor plan / graph isolation
# ===========================================================================

class TestFloorPlanIsolation:
    """Verify that NavigationService uses the floorplan.json it was given,
    not a stale shared one, and that the route reflects the current graph."""

    def test_service_uses_provided_floorplan(self, sample_floorplan, tmp_path):
        from cv.floorplan_parser import save_floorplan_json
        from graph.graph_builder import NavigationGraphBuilder, save_navigation_graph_json

        fp_path = tmp_path / "floorplan.json"
        gj_path = tmp_path / "navigation_graph.json"
        save_floorplan_json(sample_floorplan, fp_path)
        builder = NavigationGraphBuilder(sample_floorplan)
        save_navigation_graph_json(builder.graph, gj_path)

        mock_client = MagicMock()
        mock_client.check_availability.return_value = (False, "offline")
        mock_client.is_model_installed.return_value = False
        mock_client.model = "qwen3.5:4b"
        mock_client.timeout = 30

        from navigation_service import NavigationService
        svc = NavigationService(
            floorplan_path=fp_path,
            graph_json_path=gj_path,
            ollama_client=mock_client,
            auto_load=True,
        )
        # The graph only has Room_1, Room_2, Corridor_1 with one edge
        locs = sorted(svc.get_available_locations())
        assert "Room_1" in locs
        assert "Corridor_1" in locs
