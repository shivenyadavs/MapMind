import cv2
import numpy as np
from typing import Tuple

from .models import FloorPlan, BoundingBox


def _draw_badge(
    image: np.ndarray,
    text: str,
    pos: Tuple[int, int],
    bg_color: Tuple[int, int, int],
    text_color: Tuple[int, int, int] = (255, 255, 255),
    font_scale: float = 0.42,
    thickness: int = 1,
) -> None:
    """Draw a clean badge with background rectangle and crisp text."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = pos
    padding = 3

    # Background rect
    cv2.rectangle(
        image,
        (x - padding, y - text_h - padding),
        (x + text_w + padding, y + baseline + padding),
        bg_color,
        -1,
    )
    # Border
    cv2.rectangle(
        image,
        (x - padding, y - text_h - padding),
        (x + text_w + padding, y + baseline + padding),
        (50, 50, 50),
        1,
    )
    # Text
    cv2.putText(
        image,
        text,
        (x, y),
        font,
        font_scale,
        text_color,
        thickness,
        cv2.LINE_AA,
    )


def visualize_floorplan(floorplan: FloorPlan, original_image: np.ndarray) -> np.ndarray:
    """Create a high-quality annotated visualization of the detected floor plan.

    Features:
    - Rooms: Crisp green bounding boxes with neat badges
    - Corridors: Crisp cyan/amber bounding boxes
    - Doors: Distinct magenta markers at door centers with door ID badges
    - Walls: Clean structural red line segments
    """
    vis = original_image.copy()

    # 1. Draw structural walls
    for wall in floorplan.walls:
        cv2.line(vis, wall.start, wall.end, (0, 0, 220), 2)

    # 2. Draw corridors (amber / cyan)
    for cor in floorplan.corridors:
        b = cor.bounding_box
        cv2.rectangle(vis, (b.x, b.y), (b.x2, b.y2), (255, 180, 0), 2)
        _draw_badge(vis, cor.name, (b.x + 8, b.y + 18), bg_color=(220, 140, 0), text_color=(0, 0, 0))

    # 3. Draw rooms (green)
    for room in floorplan.rooms:
        b = room.bounding_box
        cv2.rectangle(vis, (b.x, b.y), (b.x2, b.y2), (0, 180, 0), 2)
        _draw_badge(vis, room.name, (b.x + 8, b.y + 18), bg_color=(0, 140, 0), text_color=(255, 255, 255))

    # 4. Draw doors (magenta markers + badge)
    for door in floorplan.doors:
        cx, cy = door.center
        b = door.bounding_box
        # Draw small door outline
        cv2.rectangle(vis, (b.x, b.y), (b.x2, b.y2), (220, 0, 220), 1)
        # Door center marker
        cv2.circle(vis, (cx, cy), 4, (200, 0, 200), -1)
        cv2.circle(vis, (cx, cy), 5, (255, 255, 255), 1)
        _draw_badge(vis, f"D{door.id}", (cx + 6, cy - 4), bg_color=(180, 0, 180), text_color=(255, 255, 255), font_scale=0.35)

    return vis
