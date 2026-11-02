import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import cv2

output_dir = r"C:\Users\shive\mapmind\research_deliverables\ieee_latex\figures"
os.makedirs(output_dir, exist_ok=True)

# Set high-quality font defaults
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 0.8

# =========================================================================
# FIGURE 1: Professional System Architecture Diagram
# =========================================================================
def generate_fig1_architecture():
    fig, ax = plt.subplots(figsize=(11, 6.2), dpi=300)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 6.2)
    ax.axis('off')

    # Color Palette (Publication Grade)
    c_blue_bg = "#F0F4FA"
    c_blue_border = "#2A6F97"
    c_teal_bg = "#E8F8F5"
    c_teal_border = "#117864"
    c_amber_bg = "#FEF9E7"
    c_amber_border = "#B7950B"
    c_purple_bg = "#F5EEF8"
    c_purple_border = "#6C3483"
    c_card_bg = "#FFFFFF"

    # 1. Title Banner
    ax.text(5.5, 5.95, "MapMind System Architecture: End-to-End Pipeline & Data Flow",
            ha='center', va='center', fontsize=12, fontweight='bold', color='#1A252C')

    # Column / Block coordinates: 4 main functional blocks
    # Block 1: UI & Ingestion (x: 0.3 to 2.6)
    # Block 2: Classical CV Pipeline (x: 2.9 to 5.5)
    # Block 3: Topological Graph Engine (x: 5.8 to 8.2)
    # Block 4: Grounded Local LLM Interface (x: 8.5 to 10.7)

    blocks = [
        ("Layer 1: Input & Web UI", 0.3, 0.4, 2.3, 5.2, c_blue_bg, c_blue_border, [
            ("Floor Plan Ingestion", "Raw raster image (PNG/JPG)\nResolution normalization (1200px)"),
            ("Interactive UI (Streamlit)", "Real-time layer toggling\nRoute visualization display"),
            ("User Query Interface", "Natural-language query box\nInteractive location picker")
        ]),
        ("Layer 2: Classical CV Engine", 2.9, 0.4, 2.6, 5.2, c_teal_bg, c_teal_border, [
            ("Achromatic Filter", "Separates dark walls (delta <= 28)\nfrom colored CAD symbols"),
            ("Text Suppression", "Removes printed labels (STORE)\nBounding-box fill-ratio filter"),
            ("Adaptive Gap Closing", "Tests 6 gap ratios (0.03-0.09)\nMaximizes valid room yield"),
            ("Wall Merging & Canny", "Collinear Hough line merging\n52% wall mass support test"),
            ("Region Segmentation", "Free-space inversion (1 - Wall)\nCorridor aspect ratio >= 4.0"),
            ("Door Probing", "Dual-source door candidates\nOrthogonal ray-probe axis")
        ]),
        ("Layer 3: Topological Graph", 5.8, 0.4, 2.4, 5.2, c_amber_bg, c_amber_border, [
            ("Location Inventory", "Rooms (R), Corridors (C_h)\nDoor thresholds (D)"),
            ("Navigation Graph G=(V,E)", "Nodes: Room centroids\nEdges: Validated doorways"),
            ("Door-Center Weighting", "omega = ||c(u)-c(d)|| + ||c(d)-c(v)||\nPhysical threshold cost"),
            ("A* Shortest Path", "Admissible Euclidean heuristic\nh(u, t) = ||c(u) - c(t)||"),
            ("Overlay Renderer", "Multi-segment polyline path\nWall-avoidant red arrows")
        ]),
        ("Layer 4: Grounded Local LLM", 8.5, 0.4, 2.2, 5.2, c_purple_bg, c_purple_border, [
            ("Fast Query Parser", "Regex intent & slot filling\nInventory entity matching"),
            ("Offline Ollama Daemon", "Quantized local models\nPhi-2 / Llama-3 (CPU)"),
            ("Grounding Verifier", "Anti-hallucination guardrail\nAudits generated text"),
            ("Deterministic Fallback", "Substitutes verified path if\nLLM hallucinates turns/IDs")
        ])
    ]

    for title, bx, by, bw, bh, bg_col, b_col, sub_boxes in blocks:
        # Container Box
        rect = patches.FancyBboxPatch((bx, by), bw, bh, boxstyle="round,pad=0.08",
                                      edgecolor=b_col, facecolor=bg_col, linewidth=1.2, linestyle='--')
        ax.add_patch(rect)
        # Header Box
        hdr_rect = patches.FancyBboxPatch((bx + 0.05, by + bh - 0.42), bw - 0.1, 0.36,
                                          boxstyle="round,pad=0.04", edgecolor=b_col, facecolor=b_col)
        ax.add_patch(hdr_rect)
        ax.text(bx + bw/2.0, by + bh - 0.24, title, ha='center', va='center',
                fontsize=8.5, fontweight='bold', color='#FFFFFF')

        # Sub-boxes inside container
        n_items = len(sub_boxes)
        avail_h = bh - 0.6
        box_h = (avail_h - (n_items - 1) * 0.12) / n_items
        cur_y = by + bh - 0.52 - box_h

        for sub_title, sub_desc in sub_boxes:
            s_rect = patches.FancyBboxPatch((bx + 0.1, cur_y), bw - 0.2, box_h,
                                            boxstyle="round,pad=0.04", edgecolor='#D0D3D4',
                                            facecolor=c_card_bg, linewidth=0.8)
            ax.add_patch(s_rect)
            ax.text(bx + 0.15, cur_y + box_h - 0.11, sub_title, ha='left', va='center',
                    fontsize=7.5, fontweight='bold', color=b_col)
            ax.text(bx + 0.15, cur_y + (box_h - 0.11)/2.0, sub_desc, ha='left', va='center',
                    fontsize=6.2, color='#2C3E50', linespacing=1.15)
            cur_y -= (box_h + 0.12)

    # Inter-block flow arrows
    arrow_style = dict(arrowstyle="->", color="#1F618D", lw=1.8, mutation_scale=14)
    # Layer 1 -> Layer 2
    ax.annotate("", xy=(2.9, 4.3), xytext=(2.6, 4.3), arrowprops=arrow_style)
    ax.text(2.75, 4.45, "Image", ha='center', va='bottom', fontsize=6.5, fontweight='bold', color='#1F618D')

    # Layer 2 -> Layer 3
    ax.annotate("", xy=(5.8, 4.3), xytext=(5.5, 4.3), arrowprops=arrow_style)
    ax.text(5.65, 4.45, "Topology", ha='center', va='bottom', fontsize=6.5, fontweight='bold', color='#1F618D')

    # Layer 1 -> Layer 4 (Query)
    ax.annotate("", xy=(8.5, 4.7), xytext=(2.6, 5.4),
                arrowprops=dict(arrowstyle="->", color="#6C3483", lw=1.2, linestyle=':',
                                connectionstyle="arc3,rad=-0.15", mutation_scale=12))
    ax.text(5.5, 5.65, "Natural Language Query (e.g., 'From Room 1 to 5')",
            ha='center', va='center', fontsize=6.5, fontweight='bold', color='#6C3483')

    # Layer 3 -> Layer 4 (Verified Path Context)
    ax.annotate("", xy=(8.5, 2.5), xytext=(8.2, 2.5), arrowprops=arrow_style)
    ax.text(8.35, 2.65, "A* Route", ha='center', va='bottom', fontsize=6.5, fontweight='bold', color='#1F618D')

    # Layer 4 -> Layer 1 (Verified Response & Visual Route)
    ax.annotate("", xy=(2.6, 1.2), xytext=(8.5, 1.2),
                arrowprops=dict(arrowstyle="->", color="#27AE60", lw=1.5,
                                connectionstyle="arc3,rad=-0.12", mutation_scale=14))
    ax.text(5.5, 0.72, "Verified Itinerary & Door-Aware Trajectory Overlay",
            ha='center', va='center', fontsize=7, fontweight='bold', color='#27AE60',
            bbox=dict(boxstyle="round,pad=0.2", facecolor='#EAFAF1', edgecolor='#27AE60', lw=0.8))

    plt.tight_layout()
    out_file = os.path.join(output_dir, "architecture.png")
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close()
    print("[SUCCESS] Fig 1 (Architecture) generated at", out_file)


# =========================================================================
# FIGURE 2: Multi-Stage CV Pipeline Walkthrough (4-Panel High-Res)
# =========================================================================
def generate_fig2_detections():
    # Load the 4 canonical pipeline stages
    p1 = cv2.imread(r"C:\Users\shive\mapmind\data\processed\original.png")
    p2 = cv2.imread(r"C:\Users\shive\mapmind\data\processed\closed_walls_debug.png")
    p3 = cv2.imread(r"C:\Users\shive\mapmind\data\processed\rooms_debug.png")
    p4 = cv2.imread(r"C:\Users\shive\mapmind\data\processed\doors_debug.png")

    fig, axes = plt.subplots(2, 2, figsize=(9.5, 7.2), dpi=300)
    panels = [
        (axes[0, 0], p1, "(a) Input Architectural Floor Plan (Raw 2D Raster)"),
        (axes[0, 1], p2, "(b) Wall Mask with Multi-Candidate Adaptive Closing"),
        (axes[1, 0], p3, "(c) Free-Space Connected Component Segmentation"),
        (axes[1, 1], p4, "(d) Door Detection & Structural Topological Overlay")
    ]

    for ax, img, title in panels:
        if img is not None:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            ax.imshow(rgb)
        else:
            ax.text(0.5, 0.5, "Image Not Found", ha='center', va='center')
        ax.set_title(title, fontsize=9.5, fontweight='bold', pad=6, color='#1A252C')
        ax.axis('off')

    plt.tight_layout()
    out_file = os.path.join(output_dir, "floorplan_detections.png")
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close()
    print("[SUCCESS] Fig 2 (Floorplan Detections) generated at", out_file)


# =========================================================================
# FIGURE 3: Door-Center Pathfinding vs Naive Straight-Line Routing
# =========================================================================
def generate_fig3_navigation_comparison():
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), dpi=300)

    # Let's draw schematic layouts illustrating the exact routing problem
    for ax, title, is_proposed in [
        (axes[0], "(a) Naive Centroid Routing (Prior Art / Baseline)\n[Wall-Clipping Defect]", False),
        (axes[1], "(b) MapMind Door-Center Routing (Proposed)\n[Wall-Avoidant Trajectory]", True)
    ]:
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 8)
        ax.set_aspect('equal')
        ax.axis('off')

        # Draw outer building envelope
        ax.add_patch(patches.Rectangle((0.5, 0.5), 9, 7, fill=False, edgecolor='#2C3E50', lw=2.5))

        # Horizontal corridor (y: 3.2 to 4.8)
        ax.add_patch(patches.Rectangle((0.5, 3.2), 9, 1.6, facecolor='#EBF5FB', edgecolor='#2C3E50', lw=1.8))
        ax.text(5.0, 4.0, "Corridor_1", ha='center', va='center', fontsize=9, fontweight='bold', color='#1B4F72')

        # Room 1 (top left, x: 0.5 to 4.8, y: 4.8 to 7.5)
        ax.add_patch(patches.Rectangle((0.5, 4.8), 4.3, 2.7, facecolor='#FEF9E7', edgecolor='#2C3E50', lw=1.8))
        ax.text(2.65, 6.15, "Room_1", ha='center', va='center', fontsize=9, fontweight='bold', color='#7D6608')

        # Room 2 (top right, x: 5.2 to 9.5, y: 4.8 to 7.5)
        ax.add_patch(patches.Rectangle((5.2, 4.8), 4.3, 2.7, facecolor='#FEF9E7', edgecolor='#2C3E50', lw=1.8))
        ax.text(7.35, 6.15, "Room_2\n(Source)", ha='center', va='center', fontsize=9, fontweight='bold', color='#7D6608')

        # Room 3 (bottom right, x: 5.2 to 9.5, y: 0.5 to 3.2)
        ax.add_patch(patches.Rectangle((5.2, 0.5), 4.3, 2.7, facecolor='#E8F8F5', edgecolor='#2C3E50', lw=1.8))
        ax.text(7.35, 1.85, "Room_3\n(Target)", ha='center', va='center', fontsize=9, fontweight='bold', color='#0E6251')

        # Room 4 (bottom left, x: 0.5 to 4.8, y: 0.5 to 3.2)
        ax.add_patch(patches.Rectangle((0.5, 0.5), 4.3, 2.7, facecolor='#FDEDEC', edgecolor='#2C3E50', lw=1.8))
        ax.text(2.65, 1.85, "Room_4", ha='center', va='center', fontsize=9, fontweight='bold', color='#78281F')

        # Doorways (Gaps in walls)
        # Door 1: Room_1 to Corridor (x: 2.65, y: 4.8)
        # Door 2: Room_2 to Corridor (x: 7.35, y: 4.8)
        # Door 3: Room_3 to Corridor (x: 7.35, y: 3.2)
        d2 = patches.Rectangle((7.0, 4.7), 0.7, 0.2, facecolor='#E74C3C', edgecolor='#900C3F', lw=1.2)
        d3 = patches.Rectangle((7.0, 3.1), 0.7, 0.2, facecolor='#E74C3C', edgecolor='#900C3F', lw=1.2)
        ax.add_patch(d2)
        ax.add_patch(d3)
        ax.text(6.8, 4.8, "Door_2", ha='right', va='center', fontsize=7.5, fontweight='bold', color='#C0392B')
        ax.text(6.8, 3.2, "Door_3", ha='right', va='center', fontsize=7.5, fontweight='bold', color='#C0392B')

        # Solid divider wall between Room 2 and Room 3? No, corridor is between them.
        # But between Room 2 and Corridor, wall is at y=4.8. Between Corridor and Room 3, wall is at y=3.2.

        c_r2 = (7.35, 5.8)
        c_r3 = (7.35, 1.85)
        c_d2 = (7.35, 4.8)
        c_corr = (6.0, 4.0) # intermediate corridor waypoint
        c_d3 = (7.35, 3.2)

        # Plot centroids
        ax.plot([c_r2[0]], [c_r2[1]], 'o', color='#2980B9', markersize=9, zorder=5)
        ax.plot([c_r3[0]], [c_r3[1]], 'o', color='#27AE60', markersize=9, zorder=5)

        if not is_proposed:
            # NAIVE ROUTING: Direct line from c_r2 to c_r3 cutting through walls and corridor ignoring door
            # Draw diagonal straight line from (7.35, 5.8) to (2.65, 1.85) - say from Room 2 to Room 4
            c_target = (2.65, 1.85)
            ax.plot([c_target[0]], [c_target[1]], 'o', color='#27AE60', markersize=9, zorder=5)
            ax.text(2.65, 1.85, "Room_4\n(Target)", ha='center', va='center', fontsize=9, fontweight='bold', color='#78281F')

            # Naive straight line from Room 2 to Room 4
            ax.annotate("", xy=c_target, xytext=c_r2,
                        arrowprops=dict(arrowstyle="->", color="#C0392B", lw=3.0, linestyle="--"))
            
            # Wall intersection markers
            ax.plot([5.2, 4.8], [4.1, 3.7], 'x', color='#900C3F', markersize=14, markeredgewidth=3.0)
            ax.text(5.0, 5.0, "FAILS: Cuts across\nsolid masonry walls!", ha='center', va='center',
                    fontsize=8, fontweight='bold', color='#900C3F',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='#FADBD8', edgecolor='#900C3F', lw=1))
        else:
            # MAPMIND ROUTING: Door-center-aware trajectory
            c_target = (2.65, 1.85)
            ax.plot([c_target[0]], [c_target[1]], 'o', color='#27AE60', markersize=9, zorder=5)
            ax.text(2.65, 1.85, "Room_4\n(Target)", ha='center', va='center', fontsize=9, fontweight='bold', color='#78281F')

            # Door 4: Corridor to Room 4
            d4 = patches.Rectangle((2.3, 3.1), 0.7, 0.2, facecolor='#E74C3C', edgecolor='#900C3F', lw=1.2)
            ax.add_patch(d4)
            ax.text(2.1, 3.2, "Door_4", ha='right', va='center', fontsize=7.5, fontweight='bold', color='#C0392B')

            # Polyline: Room 2 -> Door 2 -> Corridor 1 -> Door 4 -> Room 4
            route_pts = [c_r2, (7.35, 4.8), (7.35, 4.0), (2.65, 4.0), (2.65, 3.2), c_target]
            xs, ys = zip(*route_pts)
            ax.plot(xs, ys, '-', color='#27AE60', lw=2.8, zorder=4)

            # Directional arrow heads along segments
            ax.annotate("", xy=(7.35, 4.8), xytext=c_r2, arrowprops=dict(arrowstyle="->", color="#27AE60", lw=2.5))
            ax.annotate("", xy=(2.65, 4.0), xytext=(7.35, 4.0), arrowprops=dict(arrowstyle="->", color="#27AE60", lw=2.5))
            ax.annotate("", xy=c_target, xytext=(2.65, 3.2), arrowprops=dict(arrowstyle="->", color="#27AE60", lw=2.5))

            ax.text(5.0, 5.0, "SUCCESS: Route passes cleanly\nthrough door thresholds!", ha='center', va='center',
                    fontsize=8, fontweight='bold', color='#196F3D',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='#D5F5E3', edgecolor='#196F3D', lw=1))

        ax.set_title(title, fontsize=9.5, fontweight='bold', pad=8, color='#1A252C')

    plt.tight_layout()
    out_file = os.path.join(output_dir, "navigation_graph.png")
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close()
    print("[SUCCESS] Fig 3 (Navigation Graph Comparison) generated at", out_file)


# =========================================================================
# FIGURE 4: Quantitative Generalization & Latency Breakdown (Replacing table image)
# =========================================================================
def generate_fig4_performance():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2), dpi=300)

    # Subplot 1: Real Commercial Mall Generalization (Before vs After)
    categories = ['Valid Rooms', 'Detected Doors', 'Spurious Walls', 'Connected Units']
    baseline_vals = [5, 4, 138, 3]
    mapmind_vals = [33, 38, 118, 32]

    x = np.arange(len(categories))
    w = 0.35

    rects1 = ax1.bar(x - w/2, baseline_vals, w, label='Pre-Fix Baseline', color='#E74C3C', edgecolor='#900C3F', alpha=0.85)
    rects2 = ax1.bar(x + w/2, mapmind_vals, w, label='MapMind (Proposed)', color='#2ECC71', edgecolor='#196F3D', alpha=0.9)

    ax1.set_ylabel('Primitive Count / Metric', fontsize=8.5, fontweight='bold')
    ax1.set_title('(a) Mall Plan: Pre-Fix vs MapMind Generalization', fontsize=9.5, fontweight='bold', pad=8)
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories, fontsize=8, fontweight='bold')
    ax1.legend(fontsize=8, loc='upper left')
    ax1.grid(axis='y', linestyle=':', alpha=0.6)

    # Add data labels above bars
    for rect in rects1:
        h = rect.get_height()
        ax1.annotate(f'{h}', xy=(rect.get_x() + rect.get_width() / 2, h),
                     xytext=(0, 2), textcoords="offset points", ha='center', va='bottom', fontsize=7.5, fontweight='bold')
    for rect in rects2:
        h = rect.get_height()
        ax1.annotate(f'{h}', xy=(rect.get_x() + rect.get_width() / 2, h),
                     xytext=(0, 2), textcoords="offset points", ha='center', va='bottom', fontsize=7.5, fontweight='bold')

    # Subplot 2: Execution Latency Breakdown by Pipeline Stage (ms on CPU)
    stages = [
        'Normalization & Filter',
        'Text Suppression',
        'Adaptive Gap Closing',
        'Canny & Hough Merging',
        'Region Segmentation',
        'Door Probing & Association',
        'Graph Build & A* Search'
    ]
    # Sample, Apt, Mall execution times in milliseconds
    mall_times = [185, 240, 420, 310, 390, 480, 15]

    y = np.arange(len(stages))
    ax2.barh(y, mall_times, height=0.6, color='#3498DB', edgecolor='#1B4F72', alpha=0.85)
    ax2.set_xlabel('Execution Latency on CPU (ms)', fontsize=8.5, fontweight='bold')
    ax2.set_title('(b) Processing Latency Breakdown (Commercial Mall Plan)', fontsize=9.5, fontweight='bold', pad=8)
    ax2.set_yticks(y)
    ax2.set_yticklabels(stages, fontsize=7.5)
    ax2.invert_yaxis()  # top-down
    ax2.grid(axis='x', linestyle=':', alpha=0.6)

    for i, v in enumerate(mall_times):
        ax2.text(v + 10, i, f'{v} ms', va='center', fontsize=7.5, fontweight='bold', color='#1B4F72')

    ax2.set_xlim(0, 600)

    plt.tight_layout()
    out_file = os.path.join(output_dir, "results_table.png")
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close()
    print("[SUCCESS] Fig 4 (Performance & Generalization) generated at", out_file)


if __name__ == "__main__":
    generate_fig1_architecture()
    generate_fig2_detections()
    generate_fig3_navigation_comparison()
    generate_fig4_performance()

