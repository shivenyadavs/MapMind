import math
from typing import List, Optional, Tuple, Dict, Any
import networkx as nx

from cv.models import Route


def euclidean_heuristic(u: str, v: str, graph: nx.Graph) -> float:
    """Admissible and consistent Euclidean distance heuristic between two node centroids.

    Because graph edge weights represent walkable distances through doorway openings
    (d(u, door) + d(door, v)), straight-line Euclidean distance between room centroids
    satisfies the triangle inequality: ||center(u) - center(v)|| <= d*(u, v).
    Therefore, this heuristic never overestimates the true shortest path cost.
    If either node lacks a centroid coordinate, returns 0.0 (reducing A* to Dijkstra).
    """
    if u not in graph or v not in graph:
        return 0.0
    u_center = graph.nodes[u].get("center")
    v_center = graph.nodes[v].get("center")
    if u_center is None or v_center is None:
        return 0.0
    dx = float(u_center[0] - v_center[0])
    dy = float(u_center[1] - v_center[1])
    return math.hypot(dx, dy)


def get_path_distance(graph: nx.Graph, path: List[str]) -> float:
    """Calculate the total cumulative distance along a given path of node IDs.

    Parameters
    ----------
    graph : nx.Graph
        Weighted undirected NetworkX graph.
    path : List[str]
        Ordered sequence of node IDs.

    Returns
    -------
    float
        Cumulative edge weight sum rounded to 1 decimal place.
    """
    if not path or len(path) <= 1:
        return 0.0

    total_dist = 0.0
    for u, v in zip(path[:-1], path[1:]):
        if not graph.has_edge(u, v):
            raise ValueError(f"No direct edge exists between '{u}' and '{v}'.")
        edge_data = graph[u][v]
        total_dist += float(edge_data.get("weight", edge_data.get("distance", 0.0)))

    return round(total_dist, 1)


def get_route_details(graph: nx.Graph, path: List[str]) -> Route:
    """Extract structured route metadata from an ordered node path.

    Parameters
    ----------
    graph : nx.Graph
        Weighted undirected NetworkX graph.
    path : List[str]
        Ordered sequence of node IDs.

    Returns
    -------
    Route
        Structured Route object containing source, destination, path, traversed doors,
        total distance, and edge count.
    """
    if not path:
        raise ValueError("Cannot extract route details from an empty path.")

    source = path[0]
    destination = path[-1]

    if len(path) == 1:
        return Route(
            source=source,
            destination=destination,
            path=path,
            doors=[],
            total_distance=0.0,
            edge_count=0,
        )

    doors: List[str] = []
    total_dist = 0.0

    for u, v in zip(path[:-1], path[1:]):
        if not graph.has_edge(u, v):
            raise ValueError(f"Graph does not contain edge ({u}, {v}).")
        edge_data = graph[u][v]
        door_id = edge_data.get("door_id") or edge_data.get("via_door")
        if door_id:
            doors.append(door_id)
        edge_weight = float(edge_data.get("weight", edge_data.get("distance", 0.0)))
        total_dist += edge_weight

    return Route(
        source=source,
        destination=destination,
        path=path,
        doors=doors,
        total_distance=round(total_dist, 1),
        edge_count=len(path) - 1,
    )


def astar_path(graph: nx.Graph, source: str, destination: str) -> Route:
    """Compute the optimal path between source and destination using the A* search algorithm.

    Parameters
    ----------
    graph : nx.Graph
        Weighted undirected NetworkX graph of navigable regions.
    source : str
        ID of starting room or corridor (e.g. 'Room_1').
    destination : str
        ID of target room or corridor (e.g. 'Room_5').

    Returns
    -------
    Route
        Structured route with source, destination, ordered node path, traversed door IDs,
        total distance cost, and number of edges.

    Raises
    ------
    ValueError
        If the graph is empty, or source/destination does not exist in the graph,
        or if no path exists between the two nodes.
    """
    if graph is None or graph.number_of_nodes() == 0:
        raise ValueError("Cannot perform pathfinding on an empty or invalid graph.")

    if source not in graph:
        raise ValueError(f"Source node '{source}' not found in navigation graph.")
    if destination not in graph:
        raise ValueError(f"Destination node '{destination}' not found in navigation graph.")

    if source == destination:
        return Route(
            source=source,
            destination=destination,
            path=[source],
            doors=[],
            total_distance=0.0,
            edge_count=0,
        )

    # Heuristic lambda bound to current graph and destination target
    h_func = lambda u, v: euclidean_heuristic(u, v, graph)

    try:
        node_path: List[str] = nx.astar_path(
            graph,
            source=source,
            target=destination,
            heuristic=h_func,
            weight="weight",
        )
    except nx.NetworkXNoPath:
        raise ValueError(f"No navigable path exists between '{source}' and '{destination}'.")

    return get_route_details(graph, node_path)


def shortest_path(graph: nx.Graph, source: str, destination: str) -> Route:
    """Compute the shortest navigable path (uses A* pathfinding internally)."""
    return astar_path(graph, source, destination)


def find_path(graph: nx.Graph, start: str, goal: str) -> List[str]:
    """Compatibility wrapper returning just the list of node identifiers."""
    route = astar_path(graph, start, goal)
    return route.path
