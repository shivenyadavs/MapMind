import json
import pytest
from pathlib import Path
import networkx as nx

from cv.preprocessing import generate_synthetic_floorplan, generate_second_floorplan
from cv.floorplan_parser import parse_floorplan
from cv.models import FloorPlan, Route
from graph.graph_builder import NavigationGraphBuilder, build_navigation_graph
from graph.pathfinder import shortest_path, get_path_distance


@pytest.fixture(scope="module")
def graph_test_dirs(tmp_path_factory):
    base = tmp_path_factory.mktemp("graph")
    return base / "raw", base / "processed"


@pytest.fixture(scope="module")
def sample_floorplan(graph_test_dirs):
    raw_dir, processed_dir = graph_test_dirs
    img_path = generate_synthetic_floorplan(output_dir=raw_dir)
    return parse_floorplan(img_path, output_dir=processed_dir)


@pytest.fixture(scope="module")
def navigation_graph(sample_floorplan):
    return build_navigation_graph(sample_floorplan)


@pytest.fixture(scope="module")
def second_floorplan(graph_test_dirs):
    raw_dir, processed_dir = graph_test_dirs
    img_path = generate_second_floorplan(output_dir=raw_dir)
    return parse_floorplan(img_path, output_dir=processed_dir)


def test_floorplan_json_serialization(sample_floorplan, tmp_path):
    """Verify that FloorPlan can be serialized to JSON and deserialized back."""
    json_path = tmp_path / "floorplan_test.json"
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(sample_floorplan.model_dump_json(indent=2))

    assert json_path.exists()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "rooms" in data and len(data["rooms"]) >= 5
    assert "doors" in data and len(data["doors"]) >= 5
    assert "corridors" in data and len(data["corridors"]) >= 1
    assert "connections" in data and len(data["connections"]) >= 5

    # Test reloading into model
    reloaded = FloorPlan.model_validate(data)
    assert len(reloaded.rooms) == len(sample_floorplan.rooms)
    assert len(reloaded.connections) == len(sample_floorplan.connections)


def test_door_region_associations(sample_floorplan):
    """Verify that every door connects valid, distinct navigable regions."""
    for door in sample_floorplan.doors:
        assert len(door.connected_regions) == 2, f"Door {door.name} does not connect exactly 2 regions"
        assert door.connected_regions[0] != door.connected_regions[1]


def test_graph_nodes_and_edges(navigation_graph):
    """Verify the topology of the navigation graph."""
    assert isinstance(navigation_graph, nx.Graph)
    # At least 5 rooms + 1 corridor = 6 nodes
    assert navigation_graph.number_of_nodes() >= 6
    assert navigation_graph.number_of_edges() >= 5

    # Check node attributes
    room_nodes = [n for n, d in navigation_graph.nodes(data=True) if d.get("type") == "room"]
    corridor_nodes = [n for n, d in navigation_graph.nodes(data=True) if d.get("type") == "corridor"]
    assert len(room_nodes) >= 5
    assert len(corridor_nodes) >= 1

    # Check edge attributes
    for u, v, data in navigation_graph.edges(data=True):
        assert "weight" in data and data["weight"] > 0
        assert "distance" in data and data["distance"] > 0
        assert "door_id" in data and data["door_id"].startswith("Door_")


@pytest.mark.parametrize("src, dst", [
    ("Room_1", "Room_2"),
    ("Room_1", "Room_3"),
    ("Room_1", "Room_4"),
    ("Room_1", "Room_5"),
    ("Room_2", "Room_5"),
])
def test_pathfinding_required_routes(navigation_graph, src, dst):
    """Verify pathfinding across all 5 specified benchmark routes."""
    route = shortest_path(navigation_graph, src, dst)

    assert isinstance(route, Route)
    assert route.source == src
    assert route.destination == dst
    assert route.path[0] == src
    assert route.path[-1] == dst
    assert route.total_distance > 0

    # Every node in the path must exist in the graph
    for node in route.path:
        assert node in navigation_graph

    # Every consecutive pair of nodes must have an edge
    for u, v in zip(route.path[:-1], route.path[1:]):
        assert navigation_graph.has_edge(u, v)

    # Number of traversed doors should equal number of edge hops
    assert len(route.doors) == len(route.path) - 1

    # get_path_distance must match route total_distance
    calc_dist = get_path_distance(navigation_graph, route.path)
    assert pytest.approx(calc_dist, 0.1) == route.total_distance


def test_pathfinding_errors(navigation_graph):
    """Verify error handling for invalid node queries."""
    with pytest.raises(ValueError, match="Source node 'GhostRoom' not found"):
        shortest_path(navigation_graph, "GhostRoom", "Room_1")

    with pytest.raises(ValueError, match="Destination node 'GhostRoom' not found"):
        shortest_path(navigation_graph, "Room_1", "GhostRoom")


def test_same_node_path(navigation_graph):
    """Verify routing from a node to itself."""
    route = shortest_path(navigation_graph, "Room_1", "Room_1")
    assert route.path == ["Room_1"]
    assert route.doors == []
    assert route.total_distance == 0.0


def test_second_floorplan_graph(second_floorplan):
    """Verify navigation graph construction on the second architectural floor plan."""
    builder = NavigationGraphBuilder(second_floorplan)
    G = builder.graph

    assert G.number_of_nodes() >= 5
    assert G.number_of_edges() >= 4

    # Test route between two rooms on second floor plan
    route = shortest_path(G, "Room_1", "Room_3")
    assert len(route.path) >= 2
    assert route.total_distance > 0
