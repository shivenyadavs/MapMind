import matplotlib.pyplot as plt
import cv2
import numpy as np
from pathlib import Path

orig_path = r'C:\Users\shive\mapmind\data\raw\apartment_floorplan.png'
debug_path = r'C:\Users\shive\AppData\Local\Temp\mapmind_session_khmz8zhp\mapmind_upload_565f3158a6cb3971\doors_debug.png'

orig = cv2.imread(orig_path)
debug = cv2.imread(debug_path)

# resize both to same height for side-by-side
target_h = 500
orig_h, orig_w = orig.shape[:2]
ratio = target_h / orig_h
orig_resized = cv2.resize(orig, (int(orig_w * ratio), target_h))
debug_resized = cv2.resize(debug, (int(debug.shape[1] * ratio), target_h))

# convert to rgb
orig_rgb = cv2.cvtColor(orig_resized, cv2.COLOR_BGR2RGB)
debug_rgb = cv2.cvtColor(debug_resized, cv2.COLOR_BGR2RGB)

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
axes[0].imshow(orig_rgb)
axes[0].set_title('Original Floor Plan')
axes[0].axis('off')
axes[1].imshow(debug_rgb)
axes[1].set_title('Detected Doors (debug)')
axes[1].axis('off')
plt.tight_layout()
plt.savefig(r'C:\Users\shive\mapmind\research_deliverables\ieee_latex\figures\floorplan_detections.png', dpi=300, bbox_inches='tight')
plt.close()
print('floorplan_detections figure saved')