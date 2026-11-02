"""
Generate enhanced publication figures for IEEE paper.
Creates Figures 5-8 using ACTUAL system output images.
"""
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import cv2
import json

output_dir = r"C:\Users\shive\mapmind\research_deliverables\ieee_latex\figures"
os.makedirs(output_dir, exist_ok=True)

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 0.8

PROC = r"C:\Users\shive\mapmind\data\processed"
RAW = r"C:\Users\shive\mapmind\data\raw"
SMOKE_APT = os.path.join(PROC, "_smoke_apartment")
SMOKE_OFC = os.path.join(PROC, "_smoke_office")
SMOKE_SMP = os.path.join(PROC, "_smoke_sample")


def safe_load(path):
    """Load image, convert BGR->RGB. Returns None if missing."""
    img = cv2.imread(path)
    if img is not None:
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return None


# =========================================================================
# FIGURE 5: Multi-Plan Annotation Comparison Grid (3x2)
# Shows raw input vs annotated output for all 3 floor plan types
# =========================================================================
def generate_fig5_multiplan_comparison():
    plans = [
        ("Sample Academic", RAW, SMOKE_SMP),
        ("Residential Apartment", RAW, SMOKE_APT),
        ("Commercial Office", RAW, SMOKE_OFC),
    ]
    raw_names = ["sample_floorplan.png", "apartment_floorplan.png", "office_floorplan.png"]

    fig, axes = plt.subplots(3, 2, figsize=(8.5, 10.5), dpi=300)
    fig.suptitle("Multi-Plan Generalization: Raw Input vs. Detected Rooms & Doors",
                 fontsize=12, fontweight='bold', y=0.98, color='#1A252C')

    for i, (label, raw_dir, smoke_dir) in enumerate(plans):
        raw_img = safe_load(os.path.join(raw_dir, raw_names[i]))
        # Try rooms_debug first for annotated view
        ann_img = safe_load(os.path.join(smoke_dir, "doors_debug.png"))
        if ann_img is None:
            ann_img = safe_load(os.path.join(smoke_dir, "rooms_debug.png"))

        for j, (ax, img, sub_label) in enumerate([
            (axes[i, 0], raw_img, f"({chr(97+i*2)}) {label} — Raw Input"),
            (axes[i, 1], ann_img, f"({chr(98+i*2)}) {label} — Detected Annotations")
        ]):
            if img is not None:
                ax.imshow(img)
            else:
                ax.text(0.5, 0.5, "Image Not Available", ha='center', va='center',
                        transform=ax.transAxes, fontsize=10, color='#999')
            ax.set_title(sub_label, fontsize=8.5, fontweight='bold', pad=4, color='#1A252C')
            ax.axis('off')

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out_file = os.path.join(output_dir, "multiplan_comparison.png")
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close()
    print("[SUCCESS] Fig 5 (Multi-Plan Comparison) generated at", out_file)


# =========================================================================
# FIGURE 6: Actual Navigation Graph from NetworkX (Real System Output)
# =========================================================================
def generate_fig6_real_navigation_graph():
    nav_img = safe_load(os.path.join(PROC, "navigation_graph.png"))
    detected_img = safe_load(os.path.join(PROC, "detected_floorplan.png"))

    fig, axes = plt.subplots(1, 2, figsize=(10, 5), dpi=300)
    fig.suptitle("Floor Plan Processing: Annotated Plan & Navigation Graph (Actual System Output)",
                 fontsize=11, fontweight='bold', y=0.99, color='#1A252C')

    panels = [
        (axes[0], detected_img, "(a) Fully Annotated Floor Plan with\nRoom Labels, Door Markers & Wall Segments"),
        (axes[1], nav_img, "(b) NetworkX Navigation Graph\n(Nodes = Room Centroids, Edges = Door Links)")
    ]

    for ax, img, title in panels:
        if img is not None:
            ax.imshow(img)
        else:
            ax.text(0.5, 0.5, "Image Not Available", ha='center', va='center',
                    transform=ax.transAxes, fontsize=10, color='#999')
        ax.set_title(title, fontsize=9, fontweight='bold', pad=6, color='#1A252C')
        ax.axis('off')

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out_file = os.path.join(output_dir, "real_navigation_graph.png")
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close()
    print("[SUCCESS] Fig 6 (Real Navigation Graph) generated at", out_file)


# =========================================================================
# FIGURE 7: Detailed CV Pipeline Intermediate Stages (6-panel)
# Shows wall candidates, segmentation masks, corridors, etc.
# =========================================================================
def generate_fig7_pipeline_details():
    stages = [
        (os.path.join(PROC, "closed_walls_debug.png"),
         "(a) Morphological Wall Closing"),
        (os.path.join(PROC, "wall_candidates_debug.png"),
         "(b) Hough Line Wall Candidates"),
        (os.path.join(PROC, "walls_debug.png"),
         "(c) Merged & Validated Wall Segments"),
        (os.path.join(PROC, "segmentation_masks_debug.png"),
         "(d) Free-Space Segmentation Masks"),
        (os.path.join(PROC, "corridors_debug.png"),
         "(e) Corridor Detection (AR ≥ 4.0)"),
        (os.path.join(PROC, "door_candidates_debug.png"),
         "(f) Door Candidate Blobs & Probing"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(11, 7), dpi=300)
    fig.suptitle("Computer Vision Pipeline: Intermediate Processing Stages (Actual Output)",
                 fontsize=12, fontweight='bold', y=0.99, color='#1A252C')

    for idx, (path, title) in enumerate(stages):
        ax = axes[idx // 3, idx % 3]
        img = safe_load(path)
        if img is not None:
            ax.imshow(img)
        else:
            ax.text(0.5, 0.5, "Not Available", ha='center', va='center',
                    transform=ax.transAxes, fontsize=10, color='#999')
        ax.set_title(title, fontsize=8.5, fontweight='bold', pad=4, color='#1A252C')
        ax.axis('off')

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out_file = os.path.join(output_dir, "pipeline_details.png")
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close()
    print("[SUCCESS] Fig 7 (Pipeline Details) generated at", out_file)


# =========================================================================
# FIGURE 8: Cross-Plan Quantitative Comparison Bar Charts
# =========================================================================
def generate_fig8_cross_plan_metrics():
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(11, 4), dpi=300)
    fig.suptitle("Cross-Plan Structural Detection Metrics",
                 fontsize=12, fontweight='bold', y=1.02, color='#1A252C')

    plans = ['Sample\n(Academic)', 'Apartment\n(Residential)', 'Mall\n(Commercial)']
    x = np.arange(len(plans))

    # (a) Rooms & Corridors
    rooms = [5, 6, 33]
    corridors = [1, 1, 1]
    w = 0.35
    ax1.bar(x - w/2, rooms, w, label='Rooms', color='#3498DB', edgecolor='#1B4F72', alpha=0.9)
    ax1.bar(x + w/2, corridors, w, label='Corridors', color='#E67E22', edgecolor='#935116', alpha=0.9)
    ax1.set_ylabel('Count', fontsize=9, fontweight='bold')
    ax1.set_title('(a) Spatial Units', fontsize=10, fontweight='bold', pad=8)
    ax1.set_xticks(x)
    ax1.set_xticklabels(plans, fontsize=8)
    ax1.legend(fontsize=7.5)
    ax1.grid(axis='y', linestyle=':', alpha=0.5)
    for i, v in enumerate(rooms):
        ax1.text(i - w/2, v + 0.5, str(v), ha='center', fontsize=8, fontweight='bold')

    # (b) Doors & Walls
    doors = [6, 6, 38]
    walls = [16, 60, 118]
    ax2.bar(x - w/2, doors, w, label='Doors', color='#E74C3C', edgecolor='#900C3F', alpha=0.9)
    ax2.bar(x + w/2, walls, w, label='Walls', color='#2ECC71', edgecolor='#196F3D', alpha=0.9)
    ax2.set_ylabel('Count', fontsize=9, fontweight='bold')
    ax2.set_title('(b) Structural Elements', fontsize=10, fontweight='bold', pad=8)
    ax2.set_xticks(x)
    ax2.set_xticklabels(plans, fontsize=8)
    ax2.legend(fontsize=7.5)
    ax2.grid(axis='y', linestyle=':', alpha=0.5)
    for i, v in enumerate(walls):
        ax2.text(i + w/2, v + 1.5, str(v), ha='center', fontsize=8, fontweight='bold')

    # (c) Connectivity percentage
    connectivity = [100, 100, 97.0]  # 32/33 = 97%
    colors_bar = ['#27AE60', '#27AE60', '#F39C12']
    ax3.bar(x, connectivity, 0.5, color=colors_bar, edgecolor='#2C3E50', alpha=0.9)
    ax3.set_ylabel('Connectivity (%)', fontsize=9, fontweight='bold')
    ax3.set_title('(c) Graph Connectivity', fontsize=10, fontweight='bold', pad=8)
    ax3.set_xticks(x)
    ax3.set_xticklabels(plans, fontsize=8)
    ax3.set_ylim(0, 110)
    ax3.axhline(y=100, color='#27AE60', linestyle='--', lw=1, alpha=0.6)
    ax3.grid(axis='y', linestyle=':', alpha=0.5)
    for i, v in enumerate(connectivity):
        ax3.text(i, v + 2, f'{v:.0f}%', ha='center', fontsize=9, fontweight='bold')

    plt.tight_layout()
    out_file = os.path.join(output_dir, "cross_plan_metrics.png")
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close()
    print("[SUCCESS] Fig 8 (Cross-Plan Metrics) generated at", out_file)


if __name__ == "__main__":
    generate_fig5_multiplan_comparison()
    generate_fig6_real_navigation_graph()
    generate_fig7_pipeline_details()
    generate_fig8_cross_plan_metrics()
    print("\n[DONE] All enhanced figures generated successfully.")

