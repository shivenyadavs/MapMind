import shutil
from pathlib import Path

from cv.preprocessing import generate_synthetic_floorplan, load_floorplan
from cv.floorplan_parser import parse_floorplan, save_floorplan_json
from graph.graph_builder import NavigationGraphBuilder, save_navigation_graph_json
from graph.pathfinder import shortest_path
from graph.graph_visualizer import visualize_navigation_graph

ARTIFACT_DIR = Path(r"C:\Users\shive\.gemini\antigravity-ide\brain\06f8d4de-7323-458f-b65c-4250738f0e40")
PROCESSED_DIR = Path("data/processed")


def main():
    print("Executing MapMind Phase 3 Pipeline...")

    # 1. Regenerate synthetic floor plan (clean architectural baseline)
    sample_path = generate_synthetic_floorplan()
    orig_img = load_floorplan(sample_path)

    # 2. Run CV floor-plan understanding pipeline (Phase 2 + Phase 3 connections)
    fp = parse_floorplan(sample_path)

    # 3. Save structured FloorPlan JSON
    floorplan_json_path = PROCESSED_DIR / "floorplan.json"
    save_floorplan_json(fp, floorplan_json_path)

    # 4. Build NetworkX Navigation Graph
    builder = NavigationGraphBuilder(fp)
    G = builder.graph

    # 5. Save Navigation Graph JSON
    graph_json_path = PROCESSED_DIR / "navigation_graph.json"
    builder.save_json(graph_json_path)

    # 6. Generate Visualization
    graph_viz_path = PROCESSED_DIR / "navigation_graph.png"
    visualize_navigation_graph(G, fp, background_image=orig_img, output_path=graph_viz_path)

    # 7. Test Example Routes
    routes_to_test = [
        ("Room_1", "Room_2"),
        ("Room_1", "Room_3"),
        ("Room_1", "Room_4"),
        ("Room_1", "Room_5"),
        ("Room_2", "Room_5"),
    ]
    computed_routes = {}
    for src, dst in routes_to_test:
        computed_routes[f"{src} -> {dst}"] = shortest_path(G, src, dst)

    # 8. Mirror files to IDE Artifact Directory
    if ARTIFACT_DIR.exists():
        for fname in ["floorplan.json", "navigation_graph.json", "navigation_graph.png", "detected_floorplan.png"]:
            src_f = PROCESSED_DIR / fname
            if src_f.exists():
                shutil.copy(src_f, ARTIFACT_DIR / fname)

    # 9. Formatted Console Report
    print()
    print("========================================")
    print("MAPMIND NAVIGATION GRAPH")
    print("========================================")
    print("Nodes:")
    for node_id, data in G.nodes(data=True):
        print(f" - {node_id} (type: {data.get('type')}, center: {data.get('center')}, area: {data.get('area')})")

    print()
    print("Edges:")
    for u, v, data in G.edges(data=True):
        print(f" - {u} <---> {v} | via: {data.get('door_id')} | weight/distance: {data.get('weight')}")

    print()
    print("Detected Door-to-Region Associations:")
    for door in fp.doors:
        print(f" - {door.name} ({door.orientation}): connects {door.connected_regions} [center: {door.center}]")

    print()
    print("Connections:")
    for conn in fp.connections:
        print(f" - {conn.source} <--> {conn.destination} via {conn.via_door} (dist={conn.distance})")

    print()
    print("Example routes:")
    for route_name, route in computed_routes.items():
        print(f" {route_name}:")
        print(f"   Path:     {' -> '.join(route.path)}")
        print(f"   Doors:    {route.doors}")
        print(f"   Distance: {route.total_distance}")

    print("========================================")
    print(f"Artifacts saved:")
    print(f" - {floorplan_json_path}")
    print(f" - {graph_json_path}")
    print(f" - {graph_viz_path}")
    print("========================================")

    return fp, G, computed_routes


if __name__ == "__main__":
    main()
