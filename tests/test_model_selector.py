"""Tests for dynamic Ollama model discovery, selection and switching.

Ollama HTTP calls are mocked; no running Ollama server is required.
"""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cv.floorplan_parser import save_floorplan_json
from cv.models import BoundingBox, Connection, Corridor, FloorPlan, Room
from llm.ollama_client import OllamaClient
from navigation_service import NavigationService

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# AppTest harness
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app_module():
    with patch("streamlit.set_page_config"), patch("streamlit.markdown"):
        import frontend.app as module
        module = importlib.reload(module)
    return module


@pytest.fixture()
def restore_client(app_module):
    original = app_module._get_ollama_client
    yield
    app_module._get_ollama_client = original


_FAKE_CLIENT_TEMPLATE = """
class FakeClient:
    def __init__(self, details, is_up, model):
        self.details = details
        self.is_up = is_up
        self.model = model
        self.timeout = 30
        self.last_request_model = None
        self.refresh_calls = 0

    def check_availability(self, force_refresh=False):
        return (self.is_up, "ok" if self.is_up else "offline")

    def list_model_details(self, force_refresh=False):
        self.refresh_calls += 1
        if not self.is_up:
            raise RuntimeError("Cannot connect to Ollama (mocked offline)")
        return [dict(item) for item in self.details]

    def list_models(self, force_refresh=False):
        return [item["name"] for item in self.list_model_details(force_refresh)]

    def is_model_installed(self, model_name=None):
        target = model_name or self.model
        return target in [item["name"] for item in self.details]

    def set_model(self, model):
        self.model = model

    def generate(self, prompt, system=None, model=None, timeout=None, temperature=0.2):
        self.last_request_model = model or self.model
        if not self.is_up:
            raise RuntimeError("Cannot connect to Ollama (mocked offline)")
        if self.last_request_model not in [item["name"] for item in self.details]:
            raise RuntimeError("model not installed")
        return "ready"

    def clear_cache(self):
        return None
"""


def _make_app_test(app_module, details, *, is_up=True, default_model="qwen3.5:4b"):
    script = f"""
import sys
sys.path.insert(0, {str(PROJECT_ROOT)!r})
import streamlit as st
import frontend.app as app

{_FAKE_CLIENT_TEMPLATE}

if "fake_client" not in st.session_state:
    st.session_state.fake_client = FakeClient(
        details={details!r},
        is_up={is_up!r},
        model={default_model!r},
    )

app._get_ollama_client = lambda: st.session_state.fake_client
app.main()
"""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_string(script, default_timeout=120)
    at.run()
    return at


def _sidebar_button(at, key):
    return next(b for b in at.sidebar.button if getattr(b, "key", None) == key)


MODEL_DETAILS = [
    {"name": "qwen3.5:4b", "size": 4_000_000_000},
    {"name": "mistral:latest", "size": 4_500_000_000},
]


# ---------------------------------------------------------------------------
# UI model discovery and selection
# ---------------------------------------------------------------------------

def test_installed_models_populate_selector(app_module, restore_client):
    at = _make_app_test(app_module, MODEL_DETAILS, default_model="qwen3.5:4b")

    assert not at.exception
    assert len(at.sidebar.selectbox) == 1
    selector = at.sidebar.selectbox[0]
    assert selector.options == ["qwen3.5:4b", "mistral:latest"]
    assert selector.value == "qwen3.5:4b"
    assert at.session_state["selected_model"] == "qwen3.5:4b"
    assert at.session_state["fake_client"].model == "qwen3.5:4b"


def test_empty_model_list_shows_actionable_message(app_module, restore_client):
    at = _make_app_test(app_module, [], default_model="qwen3.5:4b")

    assert not at.exception
    assert len(at.sidebar.selectbox) == 0
    assert at.session_state["selected_model"] is None
    warnings = " ".join(w.value for w in at.sidebar.warning)
    assert "No Ollama models are installed" in warnings
    assert "ollama pull" in warnings


def test_ollama_offline_does_not_crash_ui(app_module, restore_client):
    at = _make_app_test(app_module, MODEL_DETAILS, is_up=False)

    assert not at.exception
    assert len(at.sidebar.selectbox) == 0
    errors = " ".join(e.value for e in at.sidebar.error)
    assert "Could not read installed models" in errors
    captions = " ".join(c.value for c in at.sidebar.caption).lower()
    assert "deterministic fallback" in captions


def test_switch_model_updates_shared_client(app_module, restore_client):
    at = _make_app_test(app_module, MODEL_DETAILS)
    at.sidebar.selectbox[0].set_value("mistral:latest")
    at.run()

    assert not at.exception
    assert at.session_state["selected_model"] == "mistral:latest"
    assert at.session_state["fake_client"].model == "mistral:latest"


def test_selected_model_preserved_across_reruns(app_module, restore_client):
    at = _make_app_test(app_module, MODEL_DETAILS)
    at.sidebar.selectbox[0].set_value("mistral:latest")
    at.run()
    at.run()  # ordinary Streamlit rerun

    assert at.session_state["selected_model"] == "mistral:latest"
    assert at.sidebar.selectbox[0].value == "mistral:latest"
    assert at.session_state["fake_client"].model == "mistral:latest"


def test_refresh_discovers_new_models(app_module, restore_client):
    at = _make_app_test(app_module, MODEL_DETAILS)
    client = at.session_state["fake_client"]
    client.details.append({"name": "gemma4:e4b", "size": 5_000_000_000})

    _sidebar_button(at, "refresh_models").click()
    at.run()

    assert not at.exception
    assert at.sidebar.selectbox[0].options == [
        "qwen3.5:4b",
        "mistral:latest",
        "gemma4:e4b",
    ]
    assert at.session_state["selected_model"] == "qwen3.5:4b"


def test_removed_model_is_replaced_and_user_is_informed(app_module, restore_client):
    at = _make_app_test(app_module, MODEL_DETAILS)
    at.sidebar.selectbox[0].set_value("mistral:latest")
    at.run()
    assert at.session_state["selected_model"] == "mistral:latest"

    client = at.session_state["fake_client"]
    client.details = [{"name": "qwen3.5:4b", "size": 4_000_000_000}]

    _sidebar_button(at, "refresh_models").click()
    at.run()

    assert not at.exception
    assert at.session_state["selected_model"] == "qwen3.5:4b"
    assert at.sidebar.selectbox[0].value == "qwen3.5:4b"
    assert at.session_state["fake_client"].model == "qwen3.5:4b"
    info = " ".join(i.value for i in at.sidebar.info)
    assert "no longer installed" in info
    assert "mistral:latest" in info


def test_test_selected_model_button_uses_selected_model(app_module, restore_client):
    at = _make_app_test(app_module, MODEL_DETAILS)
    at.sidebar.selectbox[0].set_value("mistral:latest")
    at.run()

    _sidebar_button(at, "test_selected_model").click()
    at.run()

    assert not at.exception
    client = at.session_state["fake_client"]
    assert client.last_request_model == "mistral:latest"
    assert at.session_state["model_test_result"]["ok"] is True
    assert at.session_state["model_test_result"]["model"] == "mistral:latest"


# ---------------------------------------------------------------------------
# OllamaClient model switching / metadata
# ---------------------------------------------------------------------------

def _tags_response(models):
    response = MagicMock()
    response.status = 200
    response.read.return_value = json.dumps({"models": models}).encode("utf-8")
    return response


def _generate_response(text="ok"):
    response = MagicMock()
    response.status = 200
    response.read.return_value = json.dumps({"response": text}).encode("utf-8")
    return response


@patch("urllib.request.urlopen")
def test_model_switch_changes_actual_generate_payload(mock_urlopen):
    tags = _tags_response(
        [{"name": "model-a:latest"}, {"name": "model-b:latest"}]
    )
    gen = _generate_response("ok")
    mock_urlopen.return_value.__enter__.side_effect = [tags, tags, gen, gen]

    client = OllamaClient(model="model-a:latest")
    client.generate("first")
    client.set_model("model-b:latest")
    client.generate("second")

    generate_requests = [
        call.args[0]
        for call in mock_urlopen.call_args_list
        if getattr(call.args[0], "data", None)
    ]
    payload_models = [
        json.loads(request.data.decode("utf-8"))["model"]
        for request in generate_requests
    ]
    assert payload_models == ["model-a:latest", "model-b:latest"]


@patch("urllib.request.urlopen")
def test_list_model_details_includes_only_supported_metadata(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value = _tags_response(
        [
            {
                "name": "qwen3.5:4b",
                "size": 4_000_000_000,
                "modified_at": "2026-01-01T00:00:00Z",
                "details": {
                    "parameter_size": "4.0B",
                    "quantization_level": "Q4_K_M",
                    "family": "qwen3",
                    "context_length": 123456,  # not forwarded by our parser
                },
            }
        ]
    )

    client = OllamaClient(model="qwen3.5:4b")
    details = client.list_model_details(force_refresh=True)

    assert len(details) == 1
    assert details[0]["name"] == "qwen3.5:4b"
    assert details[0]["size"] == 4_000_000_000
    assert details[0]["parameter_size"] == "4.0B"
    assert details[0]["quantization_level"] == "Q4_K_M"
    assert details[0]["family"] == "qwen3"
    assert "context_length" not in details[0]


def test_set_model_does_not_mutate_environment(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "env-model")
    client = OllamaClient()
    client.set_model("session-model")

    assert client.model == "session-model"
    assert os.environ["OLLAMA_MODEL"] == "env-model"


# ---------------------------------------------------------------------------
# Navigation still uses the graph and preserves fallback
# ---------------------------------------------------------------------------

def _minimal_floorplan() -> FloorPlan:
    return FloorPlan(
        image_path="fake.png",
        image_width=800,
        image_height=600,
        rooms=[
            Room(
                id=1,
                name="Room_1",
                bounding_box=BoundingBox(x=10, y=10, width=100, height=80),
                center=(60, 50),
                width=100,
                height=80,
                area=8000,
            ),
            Room(
                id=2,
                name="Room_2",
                bounding_box=BoundingBox(x=200, y=10, width=100, height=80),
                center=(250, 50),
                width=100,
                height=80,
                area=8000,
            ),
        ],
        corridors=[
            Corridor(
                id=1,
                name="Corridor_1",
                bounding_box=BoundingBox(x=110, y=30, width=90, height=20),
                center=(155, 40),
                area=1800,
            )
        ],
        connections=[
            Connection(
                source="Room_1",
                destination="Corridor_1",
                via_door="Door_1",
                distance=95.0,
            ),
            Connection(
                source="Corridor_1",
                destination="Room_2",
                via_door="Door_2",
                distance=95.0,
            ),
        ],
    )


class _FakeLLM:
    def __init__(self):
        self.installed = {"model-a:latest", "model-b:latest"}
        self.model = "model-a:latest"
        self.timeout = 30
        self.last_generate_model = None
        self.fail_generation = False

    def set_model(self, model):
        self.model = model

    def check_availability(self, force_refresh=False):
        return (True, "ok")

    def is_model_installed(self, model_name=None):
        return (model_name or self.model) in self.installed

    def list_models(self, force_refresh=False):
        return sorted(self.installed)

    def generate(self, prompt, system=None, model=None, timeout=None, temperature=0.2):
        self.last_generate_model = model or self.model
        if self.fail_generation:
            raise RuntimeError("generation failed")
        return f"Explanation from {self.last_generate_model}"


def test_navigation_route_comes_from_graph_and_uses_selected_model(tmp_path):
    fp_path = tmp_path / "floorplan.json"
    save_floorplan_json(_minimal_floorplan(), fp_path)

    client = _FakeLLM()
    service = NavigationService(
        floorplan_path=fp_path,
        ollama_client=client,
        auto_load=True,
    )
    service.set_model("model-b:latest")

    result = service.navigate("from Room_1 to Room_2", use_llm=True)

    assert result["status"] == "success"
    assert result["path"] == ["Room_1", "Corridor_1", "Room_2"]
    assert result["doors"] == ["Door_1", "Door_2"]
    assert client.last_generate_model == "model-b:latest"
    assert result["is_llm_generated"] is True
    assert result["method"] == "ollama (model-b:latest)"
    assert "Explanation from model-b:latest" in result["explanation"]


def test_navigation_fallback_preserved_with_selected_model(tmp_path):
    fp_path = tmp_path / "floorplan.json"
    save_floorplan_json(_minimal_floorplan(), fp_path)

    client = _FakeLLM()
    client.fail_generation = True
    service = NavigationService(
        floorplan_path=fp_path,
        ollama_client=client,
        auto_load=True,
    )
    service.set_model("model-b:latest")

    result = service.navigate("from Room_1 to Room_2", use_llm=True)

    assert result["status"] == "success"
    assert result["path"] == ["Room_1", "Corridor_1", "Room_2"]
    assert result["is_llm_generated"] is False
    assert "deterministic" in result["method"]
    assert "Start in Room_1" in result["explanation"]
