import matplotlib.pyplot as plt
import matplotlib.patches as patches

fig, ax = plt.subplots(1, 1, figsize=(8, 6))
ax.set_xlim(0, 10)
ax.set_ylim(0, 8)
ax.axis('off')

boxes = [
    ("Floor-plan Image", (2, 6), (4, 2)),
    ("Preprocessing", (6, 6), (4, 2)),
    ("Wall Detection", (2, 3), (4, 2)),
    ("Room/Corridor Segmentation", (6, 3), (4, 2)),
    ("Door Detection", (2, 0), (4, 2)),
    ("Location Inventory", (6, 0), (4, 2)),
    ("Navigation Graph", (2, -1), (4, 2)),
    ("Query Parser", (6, -1), (4, 2)),
    ("LLM (Ollama)", (4, -3), (2, 2)),
    ("Route Visualization", (2, -3), (4, 2)),
    ("User Response", (6, -3), (4, 2)),
]

for label, (x, y), (w, h) in boxes:
    box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3", edgecolor='black', facecolor='lightyellow')
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, label, ha='center', va='center', fontsize=6)

arrows = [
    (2+2, 6+2, 6+2, 6+2),
    (6+2, 6+2, 2+2, 3+2),
    (2+2, 3+2, 6+2, 3+2),
    (6+2, 3+2, 2+2, 0+2),
    (2+2, 0+2, 6+2, 0+2),
    (6+2, 0+2, 2+2, -1+2),
    (2+2, -1+2, 6+2, -1+2),
    (6+2, -1+2, 4+2, -3+2),
    (2+2, -3+2, 6+2, -3+2),
    (6+2, -3+2, 2+2, -3+2),
]

for x1, y1, x2, y2 in arrows:
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color='black'))

ax.set_title('System Architecture', fontsize=10)
plt.tight_layout()
plt.savefig(r'C:\Users\shive\mapmind\research_deliverables\ieee_latex\figures\architecture.png', dpi=300, bbox_inches='tight')
plt.close()
print('architecture figure saved')