import cv2
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import networkx as nx
import numpy as np
from pathlib import Path
from typing import Optional, Tuple

from cv.models import FloorPlan


def visualize_navigation_graph(
    graph: nx.Graph,
    floorplan: FloorPlan,
    background_image: Optional[np.ndarray] = None,
    output_path: Optional[Path] = None,
) -> Path:
    """Create a high-quality visualization of the navigation graph.

    Produces a side-by-side plot:
    1. Left: Spatial Overlay — Graph nodes & edges drawn at their physical floor plan coordinates.
    2. Right: Topological Diagram — Abstract network graph displaying structural connectivity,
       door associations, and distance weights.

    Parameters
    ----------
    graph : nx.Graph
        The navigation graph constructed from the floor plan.
    floorplan : FloorPlan
        The structured floor plan model containing geometry.
    background_image : Optional[np.ndarray]
        BGR floor plan image for background overlay. If None, loaded from floorplan.image_path.
    output_path : Optional[Path]
        Target save path. Defaults to 'data/processed/navigation_graph.png'.

    Returns
    -------
    Path
        Absolute path to the saved visualization image.
    """
    if output_path is None:
        output_path = Path("data/processed/navigation_graph.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load background image if needed
    if background_image is None and floorplan.image_path:
        img_p = Path(floorplan.image_path)
        if img_p.exists():
            background_image = cv2.imread(str(img_p))

    # Set up modern style figure
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, (ax_spatial, ax_topo) = plt.subplots(1, 2, figsize=(18, 8), dpi=150)
    fig.patch.set_facecolor("#0F172A")  # Sleek dark navy background

    # -------------------------------------------------------------
    # 1. LEFT PANEL: Spatial Floor Plan Overlay
    # -------------------------------------------------------------
    ax_spatial.set_facecolor("#1E293B")
    ax_spatial.set_title("Spatial Navigation Graph (Floor Plan Overlay)", fontsize=13, fontweight="bold", color="#F8FAFC", pad=12)

    h = floorplan.image_height or 600
    w = floorplan.image_width or 800

    if background_image is not None:
        rgb_img = cv2.cvtColor(background_image, cv2.COLOR_BGR2RGB)
        ax_spatial.imshow(rgb_img, extent=[0, w, h, 0], alpha=0.55)
    else:
        ax_spatial.set_xlim(0, w)
        ax_spatial.set_ylim(h, 0)

    # Invert Y axis so (0,0) is top-left like OpenCV
    ax_spatial.set_xlim(0, w)
    ax_spatial.set_ylim(h, 0)

    # Draw region bounding boxes subtly
    for room in floorplan.rooms:
        b = room.bounding_box
        rect = patches.Rectangle((b.x, b.y), b.width, b.height, linewidth=1.2, edgecolor="#10B981", facecolor="#10B981", alpha=0.12)
        ax_spatial.add_patch(rect)

    for cor in floorplan.corridors:
        b = cor.bounding_box
        rect = patches.Rectangle((b.x, b.y), b.width, b.height, linewidth=1.2, edgecolor="#F59E0B", facecolor="#F59E0B", alpha=0.12)
        ax_spatial.add_patch(rect)

    # Draw doors on overlay
    for door in floorplan.doors:
        cx, cy = door.center
        ax_spatial.scatter(cx, cy, c="#EC4899", s=45, marker="D", edgecolors="#FFFFFF", linewidth=0.8, zorder=5)
        ax_spatial.text(cx + 8, cy - 6, door.name, fontsize=7.5, color="#F472B6", fontweight="bold", zorder=6)

    # Draw graph edges on spatial overlay
    pos_spatial = {}
    for node_id, data in graph.nodes(data=True):
        pos_spatial[node_id] = data.get("center", (w // 2, h // 2))

    for u, v, data in graph.edges(data=True):
        p1 = pos_spatial[u]
        p2 = pos_spatial[v]
        ax_spatial.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#38BDF8", linestyle="--", linewidth=2.2, alpha=0.9, zorder=3)
        # Midpoint edge badge
        mid_x = (p1[0] + p2[0]) / 2.0
        mid_y = (p1[1] + p2[1]) / 2.0
        door_lbl = data.get("door_id", "")
        dist_lbl = f"{data.get('distance', 0.0):.0f}px"
        lbl = f"{door_lbl}\n({dist_lbl})" if door_lbl else dist_lbl
        ax_spatial.text(
            mid_x, mid_y, lbl,
            fontsize=7, color="#E0F2FE", ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#0369A1", edgecolor="#0284C7", alpha=0.85),
            zorder=4
        )

    # Draw nodes on spatial overlay
    for node_id, data in graph.nodes(data=True):
        pt = pos_spatial[node_id]
        is_corridor = (data.get("type") == "corridor")
        color = "#F59E0B" if is_corridor else "#10B981"
        ax_spatial.scatter(pt[0], pt[1], c=color, s=280, edgecolors="#FFFFFF", linewidth=2, zorder=7)
        ax_spatial.text(
            pt[0], pt[1], node_id,
            fontsize=8.5, fontweight="bold", color="#0F172A",
            ha="center", va="center", zorder=8
        )

    ax_spatial.tick_params(colors="#94A3B8")
    for spine in ax_spatial.spines.values():
        spine.set_color("#334155")

    # -------------------------------------------------------------
    # 2. RIGHT PANEL: Topological Graph Diagram
    # -------------------------------------------------------------
    ax_topo.set_facecolor("#1E293B")
    ax_topo.set_title("Topological Navigation Network", fontsize=13, fontweight="bold", color="#F8FAFC", pad=12)

    # Use spring layout with fixed seed for consistent readable geometry
    pos_topo = nx.spring_layout(graph, seed=42, k=1.4)

    # Draw edges
    for u, v, data in graph.edges(data=True):
        p1 = pos_topo[u]
        p2 = pos_topo[v]
        ax_topo.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#38BDF8", linewidth=2.0, alpha=0.85, zorder=2)
        mid_x = (p1[0] + p2[0]) / 2.0
        mid_y = (p1[1] + p2[1]) / 2.0
        door_lbl = data.get("door_id", "")
        dist_val = f"{data.get('distance', 0.0):.0f}"
        lbl = f"{door_lbl} ({dist_val})" if door_lbl else dist_val
        ax_topo.text(
            mid_x, mid_y, lbl,
            fontsize=8, color="#BAE6FD", ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#0C4A6E", edgecolor="#0284C7", alpha=0.9),
            zorder=3
        )

    # Draw nodes
    for node_id, data in graph.nodes(data=True):
        pt = pos_topo[node_id]
        is_corridor = (data.get("type") == "corridor")
        node_color = "#F59E0B" if is_corridor else "#10B981"
        ax_topo.scatter(pt[0], pt[1], c=node_color, s=550, edgecolors="#FFFFFF", linewidth=2.5, zorder=4)
        ax_topo.text(
            pt[0], pt[1], node_id,
            fontsize=9, fontweight="bold", color="#0F172A",
            ha="center", va="center", zorder=5
        )

    ax_topo.axis("off")

    # Custom Legend
    legend_elements = [
        plt.Line2D([0], [0], marker="o", color="w", label="Room Node", markerfacecolor="#10B981", markersize=11),
        plt.Line2D([0], [0], marker="o", color="w", label="Corridor Node", markerfacecolor="#F59E0B", markersize=11),
        plt.Line2D([0], [0], marker="D", color="w", label="Door Opening", markerfacecolor="#EC4899", markersize=8),
        plt.Line2D([0], [0], color="#38BDF8", lw=2, linestyle="--", label="Navigable Edge"),
    ]
    ax_topo.legend(
        handles=legend_elements, loc="lower right", facecolor="#0F172A",
        edgecolor="#334155", labelcolor="#F8FAFC", fontsize=9, framealpha=0.9
    )

    plt.tight_layout()
    plt.savefig(str(output_path), facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)

    return output_path
