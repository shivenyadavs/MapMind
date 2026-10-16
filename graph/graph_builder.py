import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import networkx as nx

from cv.models import FloorPlan, Connection


class NavigationGraphBuilder:
    """Constructs a NetworkX undirected weighted navigation graph from a FloorPlan."""

    def __init__(self, floorplan: Optional[FloorPlan] = None) -> None:
        self.floorplan = floorplan
        self.graph = nx.Graph()
        if floorplan is not None:
            self.build(floorplan)

    def build(self, floorplan: FloorPlan) -> nx.Graph:
        """Build the navigation graph using rooms, corridors, and detected door connections."""
        self.floorplan = floorplan
        self.graph = nx.Graph()

        # 1. Add Room nodes
        for room in floorplan.rooms:
            b = room.bounding_box
            self.graph.add_node(
                room.name,
                type="room",
                center=room.center,
                bounding_box=[b.x, b.y, b.x2, b.y2],
                width=room.width,
                height=room.height,
                area=room.area,
            )

        # 2. Add Corridor nodes
        for corridor in floorplan.corridors:
            b = corridor.bounding_box
            self.graph.add_node(
                corridor.name,
                type="corridor",
                center=corridor.center,
                bounding_box=[b.x, b.y, b.x2, b.y2],
                width=b.width,
                height=b.height,
                area=corridor.area,
            )

        # 3. Add Edges based on geometric connections
        for conn in floorplan.connections:
            self.graph.add_edge(
                conn.source,
                conn.destination,
                weight=conn.distance,
                distance=conn.distance,
                door_id=conn.via_door,
                via_door=conn.via_door,
            )

        return self.graph

    def to_dict(self) -> Dict[str, Any]:
        """Convert the navigation graph to a structured dictionary representation."""
        nodes = []
        for node_id, data in self.graph.nodes(data=True):
            node_entry = {
                "id": node_id,
                "type": data.get("type", "unknown"),
                "center": list(data.get("center", (0, 0))),
                "area": data.get("area", 0),
            }
            if "bounding_box" in data:
                node_entry["bounding_box"] = data["bounding_box"]
            nodes.append(node_entry)

        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                "door_id": data.get("door_id", ""),
                "weight": data.get("weight", 0.0),
                "distance": data.get("distance", 0.0),
            })

        return {
            "nodes": nodes,
            "edges": edges,
        }

    def save_json(self, output_path: Path) -> Path:
        """Save the graph representation to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        graph_dict = self.to_dict()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(graph_dict, f, indent=2)
        return output_path


def build_navigation_graph(floorplan: FloorPlan) -> nx.Graph:
    """Convenience function to build a NetworkX navigation graph from a FloorPlan."""
    builder = NavigationGraphBuilder(floorplan)
    return builder.graph


def save_navigation_graph_json(graph: nx.Graph, output_path: Path) -> Path:
    """Save any NetworkX navigation graph to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nodes = []
    for node_id, data in graph.nodes(data=True):
        nodes.append({
            "id": node_id,
            "type": data.get("type", "unknown"),
            "center": list(data.get("center", (0, 0))),
            "area": data.get("area", 0),
        })

    edges = []
    for u, v, data in graph.edges(data=True):
        edges.append({
            "source": u,
            "target": v,
            "door_id": data.get("door_id", ""),
            "weight": data.get("weight", 0.0),
            "distance": data.get("distance", 0.0),
        })

    payload = {"nodes": nodes, "edges": edges}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return output_path
