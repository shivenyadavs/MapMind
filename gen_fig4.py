import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(1, 1, figsize=(7, 4))
ax.set_xlim(0, 10)
ax.set_ylim(0, 5)
ax.axis('off')

# table data
rows = [
    ("Metric", "Value"),
    ("Test Suite", "117 / 117 passed"),
    ("Apartment Rooms", "6"),
    ("Apartment Corridors", "1"),
    ("Apartment Doors", "6"),
    ("Apartment Walls", "60"),
    ("Mall Rooms", "33"),
    ("Mall Corridors", "1"),
    ("Mall Doors", "38"),
    ("Mall Walls", "118"),
    ("Mall Isolated Nodes", "Room_26"),
]

table = ax.table(cellText=rows, loc='center', cellLoc='center', fontsize=10)
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 1.5)

ax.set_title('Experimental Results Summary', fontsize=12, pad=10)
plt.tight_layout()
plt.savefig(r'C:\Users\shive\mapmind\research_deliverables\ieee_latex\figures\results_table.png', dpi=300, bbox_inches='tight')
plt.close()
print('results_table figure saved')