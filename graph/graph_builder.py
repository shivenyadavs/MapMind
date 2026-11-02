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
        warnings: List[str] = []
        rejected_connections: List[Dict[str, Any]] = []

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
                semantic_label=room.semantic_label,
                label_confidence=room.label_confidence,
                classification_confidence=room.classification_confidence,
                label_source=room.label_source,
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
                semantic_label=corridor.semantic_label,
                label_confidence=corridor.label_confidence,
                classification_confidence=corridor.classification_confidence,
                label_source=corridor.label_source,
            )

        valid_nodes = set(self.graph.nodes)

        # 3. Add Edges based on geometric connections.
        #    Multiple doors can connect the same pair of regions. A plain
        #    nx.Graph can only hold one edge per pair, so merge duplicates:
        #    keep every doorway in ``doors`` and use the shortest doorway as
        #    the canonical edge weight/door_id. This preserves all detected
        #    information without changing the pathfinding API.
        for conn in floorplan.connections:
            u, v = conn.source, conn.destination
            if u not in valid_nodes or v not in valid_nodes:
                rejected_connections.append({
                    "source": u,
                    "destination": v,
                    "via_door": conn.via_door,
                    "reason": "endpoint not present in floorplan regions",
                })
                warnings.append(
                    f"Rejected connection {u} -> {v} via {conn.via_door}: "
                    "endpoint not present in floorplan regions"
                )
                continue
            if u == v:
                rejected_connections.append({
                    "source": u,
                    "destination": v,
                    "via_door": conn.via_door,
                    "reason": "self-loop",
                })
                warnings.append(
                    f"Rejected self-loop connection at {u} via {conn.via_door}"
                )
                continue
            if self.graph.has_edge(u, v):
                data = self.graph[u][v]
                doors = list(data.get("doors", []))
                existing_door = data.get("door_id")
                if existing_door and existing_door not in doors:
                    doors.append(existing_door)
                if conn.via_door not in doors:
                    doors.append(conn.via_door)
                data["doors"] = doors

                if conn.distance < float(data.get("weight", float("inf"))):
                    data["weight"] = conn.distance
                    data["distance"] = conn.distance
                    data["door_id"] = conn.via_door
                    data["via_door"] = conn.via_door
            else:
                self.graph.add_edge(
                    u,
                    v,
                    weight=conn.distance,
                    distance=conn.distance,
                    door_id=conn.via_door,
                    via_door=conn.via_door,
                    doors=[conn.via_door],
                )

        isolated_nodes = sorted(nx.isolates(self.graph))
        for node in isolated_nodes:
            warnings.append(f"Isolated region has no traversable door: {node}")

        self.graph.graph["warnings"] = warnings
        self.graph.graph["isolated_nodes"] = isolated_nodes
        self.graph.graph["rejected_connections"] = rejected_connections
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
                "semantic_label": data.get("semantic_label"),
                "label_source": data.get("label_source"),
                "label_confidence": data.get("label_confidence", 0.0),
                "classification_confidence": data.get("classification_confidence", 0.0),
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
                "doors": list(data.get("doors", [])),
                "weight": data.get("weight", 0.0),
                "distance": data.get("distance", 0.0),
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "warnings": list(self.graph.graph.get("warnings", [])),
            "isolated_nodes": list(self.graph.graph.get("isolated_nodes", [])),
            "rejected_connections": list(self.graph.graph.get("rejected_connections", [])),
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
            "doors": list(data.get("doors", [])),
            "weight": data.get("weight", 0.0),
            "distance": data.get("distance", 0.0),
        })

    payload = {"nodes": nodes, "edges": edges}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return output_path
