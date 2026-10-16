"""frontend/ui_helpers.py

Stateless helper functions for the MapMind Streamlit UI.

Responsibilities:
- numpy ↔ PIL/bytes conversion for Streamlit image display
- Per-upload working directory management (isolated from built-in demo)
- Route highlighting overlay on floor-plan images
- Matplotlib navigation-graph figure generation for st.pyplot
- Room table data preparation
"""

from __future__ import annotations

import hashlib
import io
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import matplotlib
matplotlib.use("Agg")  # headless backend — must be set before pyplot import
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from PIL import Image

from cv.models import FloorPlan, Route


# ---------------------------------------------------------------------------
# Image Conversion
# ---------------------------------------------------------------------------

def numpy_to_pil(img_bgr: np.ndarray) -> Image.Image:
    """Convert OpenCV BGR numpy array to a PIL Image (RGB)."""
    return Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))


def pil_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    """Serialize a PIL Image to raw bytes."""
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def numpy_to_bytes(img_bgr: np.ndarray, fmt: str = "PNG") -> bytes:
    """Convert OpenCV BGR array straight to PNG bytes for st.image."""
    return pil_to_bytes(numpy_to_pil(img_bgr), fmt=fmt)


def bytes_to_numpy(raw: bytes) -> np.ndarray:
    """Decode uploaded image bytes to an OpenCV BGR array."""
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image — file may be corrupted or unsupported.")
    return img


# ---------------------------------------------------------------------------
# Per-Upload Working Directory
# ---------------------------------------------------------------------------

def upload_hash(raw_bytes: bytes) -> str:
    """Compute a short SHA-256 hex digest of the raw file bytes."""
    return hashlib.sha256(raw_bytes).hexdigest()[:16]


def get_upload_workdir(base_tmp: Path, file_hash: str) -> Path:
    """Return an isolated working directory for a specific upload.

    Creates the directory if it does not exist.
    Uses a unique hash so different uploads never share state.
    """
    workdir = base_tmp / f"mapmind_upload_{file_hash}"
    workdir.mkdir(parents=True, exist_ok=True)
    return workdir


def get_session_tmpdir() -> Path:
    """Return a persistent temp directory for the current Python process.

    Using a module-level singleton avoids re-creating the directory on
    every Streamlit re-run within the same server process.
    """
    if not hasattr(get_session_tmpdir, "_tmpdir"):
        get_session_tmpdir._tmpdir = Path(tempfile.mkdtemp(prefix="mapmind_session_"))
    return get_session_tmpdir._tmpdir  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Route Overlay on Floor Plan Image
# ---------------------------------------------------------------------------

def draw_route_overlay(
    img_bgr: np.ndarray,
    floorplan: FloorPlan,
    route: Route,
) -> np.ndarray:
    """Draw a route highlight directly onto a copy of the annotated floor-plan image.

    Highlights:
    - Source room bounding box (bright green fill + thick border)
    - Destination room bounding box (bright blue fill + thick border)
    - Intermediate rooms/corridors (yellow fill)
    - Door markers that are part of the route (cyan circles)
    - Connecting lines between room centres along the path

    The image is never modified in-place; a copy is returned.
    Does not draw lines through walls — only connects region centres.
    """
    vis = img_bgr.copy()
    path = route.path
    route_doors = set(route.doors)

    # Build lookup: node name → (region object, type)
    region_lookup: Dict[str, Any] = {}
    for r in floorplan.rooms:
        region_lookup[r.name] = ("room", r)
    for c in floorplan.corridors:
        region_lookup[c.name] = ("corridor", c)

    # Draw door markers that are part of this route
    for door in floorplan.doors:
        if door.name in route_doors:
            cx, cy = door.center
            cv2.circle(vis, (cx, cy), 9, (0, 230, 230), -1)
            cv2.circle(vis, (cx, cy), 10, (255, 255, 255), 2)
            cv2.putText(vis, door.name, (cx + 12, cy + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 200, 200), 1, cv2.LINE_AA)

    # Colour scheme for path nodes
    def node_colour(idx: int, total: int) -> Tuple[int, int, int]:
        if idx == 0:
            return (0, 220, 80)       # source: vivid green (BGR)
        if idx == total - 1:
            return (220, 80, 0)       # destination: vivid blue-orange (BGR)
        return (0, 200, 255)          # intermediate: amber/yellow (BGR)

    # Draw filled overlays + thick borders for each path node
    centres: List[Tuple[int, int]] = []
    for idx, node_name in enumerate(path):
        if node_name not in region_lookup:
            continue
        _, region = region_lookup[node_name]
        b = region.bounding_box
        colour = node_colour(idx, len(path))

        # Semi-transparent fill
        overlay = vis.copy()
        cv2.rectangle(overlay, (b.x, b.y), (b.x2, b.y2), colour, -1)
        cv2.addWeighted(overlay, 0.25, vis, 0.75, 0, vis)

        # Thick border
        cv2.rectangle(vis, (b.x, b.y), (b.x2, b.y2), colour, 3)

        cx, cy = region.center
        centres.append((cx, cy))

        # Label badge
        label = f"[{idx}] {node_name}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), bl = cv2.getTextSize(label, font, 0.42, 1)
        lx, ly = b.x + 6, b.y + 22
        cv2.rectangle(vis, (lx - 2, ly - th - 2), (lx + tw + 2, ly + bl + 2), colour, -1)
        cv2.putText(vis, label, (lx, ly), font, 0.42, (0, 0, 0), 1, cv2.LINE_AA)

    # Draw connecting arrows between consecutive region centres
    for (p1, p2) in zip(centres[:-1], centres[1:]):
        cv2.arrowedLine(vis, p1, p2, (255, 220, 0), 2, tipLength=0.2)

    return vis


# ---------------------------------------------------------------------------
# Navigation Graph Figure (Matplotlib → st.pyplot)
# ---------------------------------------------------------------------------

def build_graph_figure(
    graph: nx.Graph,
    floorplan: FloorPlan,
    highlighted_path: Optional[List[str]] = None,
) -> plt.Figure:
    """Return a Matplotlib Figure with a topological navigation graph.

    Parameters
    ----------
    graph : nx.Graph
        The navigation graph.
    floorplan : FloorPlan
        Used for bounding boxes (not used in this view, kept for future).
    highlighted_path : list of str, optional
        Node sequence to highlight in gold.

    Returns
    -------
    matplotlib.figure.Figure
    """
    highlighted_path = highlighted_path or []
    highlighted_set = set(highlighted_path)
    highlighted_edges = set(zip(highlighted_path[:-1], highlighted_path[1:]))

    fig, ax = plt.subplots(figsize=(9, 5), dpi=130)
    fig.patch.set_facecolor("#0F172A")
    ax.set_facecolor("#1E293B")
    ax.set_title("Navigation Graph", fontsize=13, fontweight="bold", color="#F8FAFC", pad=10)

    pos = nx.spring_layout(graph, seed=42, k=1.6)

    # Draw all edges first (background layer)
    for u, v, data in graph.edges(data=True):
        is_route_edge = (u, v) in highlighted_edges or (v, u) in highlighted_edges
        color = "#FBBF24" if is_route_edge else "#38BDF8"
        lw = 3.0 if is_route_edge else 1.5
        alpha = 1.0 if is_route_edge else 0.6
        p1, p2 = pos[u], pos[v]
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color, linewidth=lw, alpha=alpha, zorder=2)

        # Door label on edge midpoint
        door_id = data.get("door_id", "")
        dist_val = data.get("distance", 0.0)
        lbl = f"{door_id}\n({dist_val:.0f}px)" if door_id else f"{dist_val:.0f}px"
        mid_x = (p1[0] + p2[0]) / 2
        mid_y = (p1[1] + p2[1]) / 2
        ax.text(mid_x, mid_y, lbl, fontsize=7, color="#BAE6FD", ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#0C4A6E", edgecolor="#0284C7", alpha=0.85),
                zorder=3)

    # Draw nodes
    for node_id, data in graph.nodes(data=True):
        pt = pos[node_id]
        is_corridor = data.get("type") == "corridor"
        in_path = node_id in highlighted_set
        is_src = highlighted_path and node_id == highlighted_path[0]
        is_dst = highlighted_path and node_id == highlighted_path[-1]

        if is_src:
            node_color = "#22C55E"   # bright green
            edge_color = "#FFFFFF"
            size = 700
        elif is_dst:
            node_color = "#EF4444"   # bright red
            edge_color = "#FFFFFF"
            size = 700
        elif in_path:
            node_color = "#FBBF24"   # gold
            edge_color = "#FFFFFF"
            size = 550
        elif is_corridor:
            node_color = "#F59E0B"
            edge_color = "#FFFFFF"
            size = 480
        else:
            node_color = "#10B981"
            edge_color = "#FFFFFF"
            size = 480

        ax.scatter(pt[0], pt[1], c=node_color, s=size, edgecolors=edge_color,
                   linewidth=2.0, zorder=5)
        ax.text(pt[0], pt[1], node_id, fontsize=8, fontweight="bold", color="#0F172A",
                ha="center", va="center", zorder=6)

    # Legend
    legend_items = [
        plt.Line2D([0], [0], marker="o", color="w", label="Room", markerfacecolor="#10B981", markersize=10),
        plt.Line2D([0], [0], marker="o", color="w", label="Corridor", markerfacecolor="#F59E0B", markersize=10),
        plt.Line2D([0], [0], marker="o", color="w", label="Route node", markerfacecolor="#FBBF24", markersize=10),
        plt.Line2D([0], [0], marker="o", color="w", label="Source", markerfacecolor="#22C55E", markersize=10),
        plt.Line2D([0], [0], marker="o", color="w", label="Destination", markerfacecolor="#EF4444", markersize=10),
        plt.Line2D([0], [0], color="#FBBF24", lw=2.5, label="Route edge"),
        plt.Line2D([0], [0], color="#38BDF8", lw=1.5, label="Graph edge"),
    ]
    ax.legend(handles=legend_items, loc="lower right", facecolor="#0F172A",
              edgecolor="#334155", labelcolor="#F8FAFC", fontsize=8, framealpha=0.9)

    ax.axis("off")
    plt.tight_layout(pad=1.0)
    return fig


# ---------------------------------------------------------------------------
# Room Table Data Preparation
# ---------------------------------------------------------------------------

def rooms_to_table(floorplan: FloorPlan) -> List[Dict[str, Any]]:
    """Return a list of dicts suitable for st.dataframe."""
    rows = []
    for r in floorplan.rooms:
        b = r.bounding_box
        rows.append({
            "ID": r.name,
            "Type": "Room",
            "Center X": r.center[0],
            "Center Y": r.center[1],
            "BBox (x,y,w,h)": f"({b.x}, {b.y}, {b.width}, {b.height})",
            "Area (px²)": r.area,
        })
    for c in floorplan.corridors:
        b = c.bounding_box
        rows.append({
            "ID": c.name,
            "Type": "Corridor",
            "Center X": c.center[0],
            "Center Y": c.center[1],
            "BBox (x,y,w,h)": f"({b.x}, {b.y}, {b.width}, {b.height})",
            "Area (px²)": c.area,
        })
    return rows


def doors_to_table(floorplan: FloorPlan) -> List[Dict[str, Any]]:
    """Return door metadata for st.dataframe."""
    rows = []
    for d in floorplan.doors:
        rows.append({
            "Door ID": d.name,
            "Center": f"({d.center[0]}, {d.center[1]})",
            "Orientation": d.orientation or "—",
            "Connects": " ↔ ".join(d.connected_regions) if d.connected_regions else "—",
        })
    return rows
