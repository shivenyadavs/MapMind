import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import networkx as nx

from cv.preprocessing import generate_synthetic_floorplan
from cv.floorplan_parser import parse_floorplan
from cv.models import FloorPlan, Route
from graph.graph_builder import build_navigation_graph
from graph.pathfinder import (
    astar_path,
    shortest_path,
    get_path_distance,
    get_route_details,
    euclidean_heuristic,
)
from llm.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFoundError,
)
from llm.query_parser import QueryParser, ParsedQuery
from llm.response_generator import (
    NavigationResponseGenerator,
    deterministic_route_explanation,
)
from navigation_service import NavigationService


@pytest.fixture(scope="module")
def phase4_dirs(tmp_path_factory):
    base = tmp_path_factory.mktemp("phase4")
    return base / "raw", base / "processed"


@pytest.fixture(scope="module")
def sample_floorplan(phase4_dirs):
    raw_dir, processed_dir = phase4_dirs
    img_path = generate_synthetic_floorplan(output_dir=raw_dir)
    return parse_floorplan(img_path, output_dir=processed_dir)


@pytest.fixture(scope="module")
def navigation_graph(sample_floorplan):
    return build_navigation_graph(sample_floorplan)


# =========================================================================
# 1. A* Pathfinding Tests
# =========================================================================

def test_astar_cost_matches_dijkstra(navigation_graph):
    """Verify that A* route cost matches NetworkX weighted shortest path across all pairs."""
    nodes = list(navigation_graph.nodes())
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            u, v = nodes[i], nodes[j]
            astar_route = astar_path(navigation_graph, u, v)
            dijkstra_cost = nx.shortest_path_length(navigation_graph, u, v, weight="weight")

            assert pytest.approx(astar_route.total_distance, 0.1) == dijkstra_cost
            assert astar_route.path[0] == u
            assert astar_route.path[-1] == v
            assert astar_route.edge_count == len(astar_route.path) - 1


def test_astar_source_equals_destination(navigation_graph):
    """Test routing when source equals destination."""
    route = astar_path(navigation_graph, "Room_1", "Room_1")
    assert route.path == ["Room_1"]
    assert route.doors == []
    assert route.total_distance == 0.0
    assert route.edge_count == 0


def test_astar_unknown_nodes(navigation_graph):
    """Test error handling when source or destination is not in graph."""
    with pytest.raises(ValueError, match="Source node 'AlienRoom' not found"):
        astar_path(navigation_graph, "AlienRoom", "Room_1")

    with pytest.raises(ValueError, match="Destination node 'AlienRoom' not found"):
        astar_path(navigation_graph, "Room_1", "AlienRoom")


def test_astar_empty_graph():
    """Test error handling when graph is empty."""
    empty_g = nx.Graph()
    with pytest.raises(ValueError, match="Cannot perform pathfinding on an empty or invalid graph"):
        astar_path(empty_g, "Room_1", "Room_2")


def test_astar_unreachable_destination(navigation_graph):
    """Test error handling when graph is disconnected."""
    disconnected_g = navigation_graph.copy()
    disconnected_g.add_node("IsolatedRoom", center=(10, 10))

    with pytest.raises(ValueError, match="No navigable path exists"):
        astar_path(disconnected_g, "Room_1", "IsolatedRoom")


def test_euclidean_heuristic_admissibility(navigation_graph):
    """Verify that Euclidean heuristic never overestimates the actual shortest path cost."""
    nodes = list(navigation_graph.nodes())
    for u in nodes:
        for v in nodes:
            h_val = euclidean_heuristic(u, v, navigation_graph)
            actual_cost = nx.shortest_path_length(navigation_graph, u, v, weight="weight")
            assert h_val <= actual_cost + 1e-5, f"Heuristic overestimated cost between {u} and {v}"


def test_no_fabricated_doors(navigation_graph):
    """Verify that returned doors strictly exist on traversed edges."""
    route = astar_path(navigation_graph, "Room_1", "Room_5")
    for u, v, door in zip(route.path[:-1], route.path[1:], route.doors):
        edge_data = navigation_graph[u][v]
        expected_door = edge_data.get("door_id") or edge_data.get("via_door")
        assert door == expected_door


# =========================================================================
# 2. Ollama Client & Error Handling Tests (Mocked)
# =========================================================================

def test_ollama_status_unavailable():
    """Test Ollama client handling when server is unreachable."""
    client = OllamaClient(base_url="http://localhost:99999", timeout=1)
    is_up, msg = client.check_availability(force_refresh=True)
    assert not is_up
    assert "Cannot connect to Ollama" in msg or "Error" in msg


@patch("urllib.request.urlopen")
def test_ollama_status_available(mock_urlopen):
    """Test Ollama client handling when server is reachable."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps({"models": [{"name": "llama3.2:latest"}]}).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    client = OllamaClient(base_url="http://localhost:11434")
    is_up, msg = client.check_availability(force_refresh=True)
    assert is_up
    assert "active" in msg


@patch("urllib.request.urlopen")
def test_ollama_model_not_found(mock_urlopen):
    """Test Ollama client raising error when model is not installed."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps({"models": [{"name": "mistral:latest"}]}).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    client = OllamaClient(model="nonexistent-model")
    with pytest.raises(OllamaModelNotFoundError, match="is not installed"):
        client.generate("Test prompt")


@patch("urllib.request.urlopen")
def test_ollama_generate_success(mock_urlopen):
    """Test successful text generation from Ollama."""
    mock_resp_tags = MagicMock()
    mock_resp_tags.status = 200
    mock_resp_tags.read.return_value = json.dumps({"models": [{"name": "llama3.2:latest"}]}).encode("utf-8")

    mock_resp_gen = MagicMock()
    mock_resp_gen.status = 200
    mock_resp_gen.read.return_value = json.dumps({"response": "Walk through Door_1 into Corridor_1."}).encode("utf-8")

    # Return tags for check, then response for generate
    mock_urlopen.return_value.__enter__.side_effect = [mock_resp_tags, mock_resp_tags, mock_resp_gen]

    client = OllamaClient(model="llama3.2")
    resp = client.generate("Describe path")
    assert "Door_1" in resp


# =========================================================================
# 3. Query Parser Tests
# =========================================================================

def test_query_parser_benchmark_queries(sample_floorplan):
    """Test parsing standard natural language navigation requests."""
    parser = QueryParser(floorplan=sample_floorplan)

    # 1. "How do I get from Reception to Room 104?"
    q1 = parser.parse("How do I get from Reception to Room 104?")
    assert q1.is_valid
    assert q1.source == "Room_1"
    assert q1.destination == "Room_5"

    # 2. "Navigate from Room 101 to Room 102."
    q2 = parser.parse("Navigate from Room 101 to Room 102.")
    assert q2.is_valid
    assert q2.source == "Room_2"
    assert q2.destination == "Room_3"

    # 3. "Find a route from Room_1 to Room_5."
    q3 = parser.parse("Find a route from Room_1 to Room_5.")
    assert q3.is_valid
    assert q3.source == "Room_1"
    assert q3.destination == "Room_5"


def test_query_parser_missing_destination(sample_floorplan):
    """Test query parser handling missing destination."""
    parser = QueryParser(floorplan=sample_floorplan)
    q = parser.parse("Where is Room 103?")
    assert not q.is_valid
    assert q.destination == "Room_4"
    assert q.source is None
    assert "specify where you are starting from" in q.clarification_needed


def test_query_parser_unrecognized_room(sample_floorplan):
    """Test query parser handling unrecognized location."""
    parser = QueryParser(floorplan=sample_floorplan)
    q = parser.parse("Navigate from Hogwarts to Room 101.")
    assert not q.is_valid
    assert "Unrecognized starting location 'Hogwarts'" in q.clarification_needed


# =========================================================================
# 4. Response Generator & Fallback Tests
# =========================================================================

def test_deterministic_explanation(navigation_graph, sample_floorplan):
    """Test deterministic route explanation formatting."""
    route = astar_path(navigation_graph, "Room_1", "Room_5")
    text = deterministic_route_explanation(route, sample_floorplan)

    assert "Start in Room_1" in text
    assert "Door_1" in text
    assert "Corridor_1" in text
    assert "Door_5" in text
    assert "Arrive at destination: Room_5" in text
    assert "pixel-based estimate" in text


def test_response_generator_fallback(navigation_graph, sample_floorplan):
    """Test NavigationResponseGenerator falling back gracefully when Ollama is unavailable."""
    client = OllamaClient(base_url="http://localhost:99999", timeout=1)
    generator = NavigationResponseGenerator(ollama_client=client)

    route = astar_path(navigation_graph, "Room_2", "Room_3")
    res = generator.generate_explanation(route, sample_floorplan, use_llm=True)

    assert not res["is_llm_generated"]
    assert "deterministic_fallback" in res["method"]
    assert "Start in Room_2" in res["explanation"]


def test_response_generator_rejects_hallucinated_locations(
    navigation_graph, sample_floorplan
):
    client = MagicMock()
    client.check_availability.return_value = (True, "ok")
    client.is_model_installed.return_value = True
    client.model = "fake-model"
    client.timeout = 30
    client.generate.return_value = (
        "Start in Room_1, then walk through Door_1 into Room_99 and turn left."
    )
    generator = NavigationResponseGenerator(ollama_client=client)

    route = astar_path(navigation_graph, "Room_1", "Room_5")
    res = generator.generate_explanation(route, sample_floorplan, use_llm=True)

    assert not res["is_llm_generated"]
    assert "deterministic_fallback" in res["method"]
    assert "Room_99" not in res["explanation"]


# =========================================================================
# 5. Navigation Service Integration Tests
# =========================================================================

def test_navigation_service_end_to_end(sample_floorplan, tmp_path):
    """Test NavigationService query processing pipeline without repo artifacts."""
    from cv.floorplan_parser import save_floorplan_json

    fp_path = tmp_path / "floorplan.json"
    save_floorplan_json(sample_floorplan, fp_path)

    mock_client = MagicMock()
    mock_client.check_availability.return_value = (False, "offline")
    mock_client.is_model_installed.return_value = False
    mock_client.model = "qwen3.5:4b"
    mock_client.timeout = 30

    service = NavigationService(
        floorplan_path=fp_path,
        ollama_client=mock_client,
        auto_load=True,
    )
    res = service.navigate("How do I get from Reception to Room 104?", use_llm=False)

    assert res["status"] == "success"
    assert res["source"] == "Room_1"
    assert res["destination"] == "Room_5"
    assert res["path"] == ["Room_1", "Corridor_1", "Room_3", "Room_5"]
    assert res["doors"] == ["Door_1", "Door_3", "Door_5"]
    assert res["total_distance"] > 0
    assert "Door_1" in res["explanation"]
