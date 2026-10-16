import json
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from .models import BoundingBox, Room, Door, Wall, Corridor, FloorPlan, Connection
from .preprocessing import (
    load_floorplan,
    resize_image,
    convert_to_grayscale,
    denoise_image,
    save_image,
)


def _merge_lines(raw_lines: np.ndarray, tol_dist: int = 12, gap_tol: int = 20) -> List[Tuple[Tuple[int, int], Tuple[int, int], str]]:
    """Group nearby parallel line segments and merge collinear/overlapping segments.
    Returns a list of ((x1, y1), (x2, y2), orientation).
    """
    if raw_lines is None or len(raw_lines) == 0:
        return []

    lines = raw_lines.reshape(-1, 4)
    h_lines = []
    v_lines = []

    for line in lines:
        x1, y1, x2, y2 = line
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        if dx >= dy:
            # Horizontal line
            if x1 > x2:
                x1, x2 = x2, x1
                y1, y2 = y2, y1
            h_lines.append((min(x1, x2), max(x1, x2), (y1 + y2) / 2.0))
        else:
            # Vertical line
            if y1 > y2:
                y1, y2 = y2, y1
                x1, x2 = x2, x1
            v_lines.append((min(y1, y2), max(y1, y2), (x1 + x2) / 2.0))

    merged_walls = []

    # Merge horizontal lines
    h_groups = []
    for l in sorted(h_lines, key=lambda item: item[2]):
        placed = False
        for group in h_groups:
            if abs(group['y'] - l[2]) <= tol_dist:
                group['lines'].append(l)
                group['y'] = np.mean([item[2] for item in group['lines']])
                placed = True
                break
        if not placed:
            h_groups.append({'y': l[2], 'lines': [l]})

    for group in h_groups:
        sorted_segs = sorted(group['lines'], key=lambda item: item[0])
        cur_x1, cur_x2 = sorted_segs[0][0], sorted_segs[0][1]
        cur_y = int(round(group['y']))
        for seg in sorted_segs[1:]:
            if seg[0] - cur_x2 <= gap_tol:
                cur_x2 = max(cur_x2, seg[1])
            else:
                if cur_x2 - cur_x1 >= 25:
                    merged_walls.append(((int(cur_x1), cur_y), (int(cur_x2), cur_y), "horizontal"))
                cur_x1, cur_x2 = seg[0], seg[1]
        if cur_x2 - cur_x1 >= 25:
            merged_walls.append(((int(cur_x1), cur_y), (int(cur_x2), cur_y), "horizontal"))

    # Merge vertical lines
    v_groups = []
    for l in sorted(v_lines, key=lambda item: item[2]):
        placed = False
        for group in v_groups:
            if abs(group['x'] - l[2]) <= tol_dist:
                group['lines'].append(l)
                group['x'] = np.mean([item[2] for item in group['lines']])
                placed = True
                break
        if not placed:
            v_groups.append({'x': l[2], 'lines': [l]})

    for group in v_groups:
        sorted_segs = sorted(group['lines'], key=lambda item: item[0])
        cur_y1, cur_y2 = sorted_segs[0][0], sorted_segs[0][1]
        cur_x = int(round(group['x']))
        for seg in sorted_segs[1:]:
            if seg[0] - cur_y2 <= gap_tol:
                cur_y2 = max(cur_y2, seg[1])
            else:
                if cur_y2 - cur_y1 >= 25:
                    merged_walls.append(((cur_x, int(cur_y1)), (cur_x, int(cur_y2)), "vertical"))
                cur_y1, cur_y2 = seg[0], seg[1]
        if cur_y2 - cur_y1 >= 25:
            merged_walls.append(((cur_x, int(cur_y1)), (cur_x, int(cur_y2)), "vertical"))

    return merged_walls


def _detect_walls(edge_image: np.ndarray) -> List[Wall]:
    """Detect major structural walls using Hough transform followed by tolerance merging."""
    raw_lines = cv2.HoughLinesP(edge_image, 1, np.pi / 180, threshold=40, minLineLength=30, maxLineGap=10)
    if raw_lines is None:
        return []

    merged = _merge_lines(raw_lines)
    walls: List[Wall] = []
    for idx, (p1, p2, ori) in enumerate(merged, start=1):
        length = float(np.hypot(p2[0] - p1[0], p2[1] - p1[1]))
        walls.append(Wall(
            id=idx,
            start=p1,
            end=p2,
            length=length,
            orientation=ori,
        ))
    return walls


def _detect_doors(walls_bin: np.ndarray, closed_walls: np.ndarray) -> List[Door]:
    """Detect door gaps by taking the difference between closed walls and original wall mask."""
    doors_mask = cv2.bitwise_and(cv2.bitwise_not(walls_bin), closed_walls)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(doors_mask, connectivity=8)

    doors: List[Door] = []
    door_id = 1
    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]
        if area < 80 or area > 1200:
            continue
        if max(w, h) < 18 or min(w, h) > 20:
            continue

        cx, cy = int(round(centroids[i][0])), int(round(centroids[i][1]))
        orientation = "horizontal" if w >= h else "vertical"
        bbox = BoundingBox(x=int(x), y=int(y), width=int(w), height=int(h))

        doors.append(Door(
            id=door_id,
            name=f"Door_{door_id}",
            bounding_box=bbox,
            center=(cx, cy),
            orientation=orientation,
            associated_rooms=[],
            connected_regions=[],
        ))
        door_id += 1

    return doors


def _detect_rooms_and_corridors(
    closed_walls: np.ndarray,
) -> Tuple[List[Room], List[Corridor]]:
    """Identify enclosed free-space regions by excluding the exterior border component.
    Distinguishes corridors (elongated high aspect-ratio spaces) from rooms.
    """
    h, w = closed_walls.shape
    free_space = cv2.bitwise_not(closed_walls)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(free_space, connectivity=8)

    # Collect exterior labels touching any border
    exterior_labels = set(np.unique(np.concatenate([
        labels[0, :], labels[h - 1, :], labels[:, 0], labels[:, w - 1]
    ])))

    candidate_rooms = []
    candidate_corridors = []

    for i in range(1, num_labels):
        if i in exterior_labels:
            continue
        x, y, bw, bh, area = stats[i]
        if area < 2000:
            continue

        aspect = max(bw / bh, bh / bw)
        cx, cy = int(round(centroids[i][0])), int(round(centroids[i][1]))
        bbox = BoundingBox(x=int(x), y=int(y), width=int(bw), height=int(bh))

        # Corridors are elongated connecting spaces (high aspect ratio)
        if aspect >= 4.5:
            candidate_corridors.append({
                "bbox": bbox,
                "center": (cx, cy),
                "area": int(area),
            })
        else:
            candidate_rooms.append({
                "bbox": bbox,
                "center": (cx, cy),
                "width": int(bw),
                "height": int(bh),
                "area": int(area),
            })

    # Sort rooms spatially from top-to-bottom, left-to-right for consistent numbering
    candidate_rooms.sort(key=lambda r: (r["bbox"].y // 50, r["bbox"].x))
    candidate_corridors.sort(key=lambda c: (c["bbox"].y // 50, c["bbox"].x))

    rooms: List[Room] = []
    for idx, r in enumerate(candidate_rooms, start=1):
        rooms.append(Room(
            id=idx,
            name=f"Room_{idx}",
            bounding_box=r["bbox"],
            center=r["center"],
            width=r["width"],
            height=r["height"],
            area=r["area"],
        ))

    corridors: List[Corridor] = []
    for idx, c in enumerate(candidate_corridors, start=1):
        corridors.append(Corridor(
            id=idx,
            name=f"Corridor_{idx}",
            bounding_box=c["bbox"],
            center=c["center"],
            area=c["area"],
        ))

    return rooms, corridors


def _associate_doors_to_regions(
    doors: List[Door],
    rooms: List[Room],
    corridors: List[Corridor],
) -> List[Connection]:
    """Determine what regions each door connects and generate Connection objects.

    Geometric Algorithm:
    1. For each door, sample two probe points perpendicular to the door orientation:
       - Horizontal door: probes at (cx, cy - delta) and (cx, cy + delta)
       - Vertical door:   probes at (cx - delta, cy) and (cx + delta, cy)
    2. Check which navigable region (room or corridor) contains each probe point.
    3. If probe points find two distinct regions, they are the directly connected regions.
    4. Fallback: If probing hits fewer than 2 distinct regions, compute Euclidean distance
       from door center to all region bounding boxes and take the two closest regions.
    5. Construct Connection objects with walking distance calculated via the door center.
    """
    all_regions: List[Dict[str, Any]] = []
    for r in rooms:
        all_regions.append({
            "name": r.name,
            "type": "room",
            "bbox": r.bounding_box,
            "center": r.center,
            "id": r.id,
        })
    for c in corridors:
        all_regions.append({
            "name": c.name,
            "type": "corridor",
            "bbox": c.bounding_box,
            "center": c.center,
            "id": c.id,
        })

    def find_region_containing_point(px: int, py: int, margin: int = 5) -> Optional[Dict[str, Any]]:
        for reg in all_regions:
            b = reg["bbox"]
            if (b.x - margin <= px <= b.x2 + margin) and (b.y - margin <= py <= b.y2 + margin):
                return reg
        return None

    def dist_to_bbox(px: int, py: int, b: BoundingBox) -> float:
        dx = max(b.x - px, 0, px - b.x2)
        dy = max(b.y - py, 0, py - b.y2)
        return float(np.hypot(dx, dy))

    connections: List[Connection] = []

    for door in doors:
        cx, cy = door.center
        delta = 18

        # 1. Normal-probe test
        if door.orientation == "horizontal":
            p1 = (cx, cy - delta)
            p2 = (cx, cy + delta)
        else:
            p1 = (cx - delta, cy)
            p2 = (cx + delta, cy)

        reg1 = find_region_containing_point(p1[0], p1[1])
        reg2 = find_region_containing_point(p2[0], p2[1])

        connected_set: List[Dict[str, Any]] = []
        if reg1 is not None:
            connected_set.append(reg1)
        if reg2 is not None and (not connected_set or reg2["name"] != connected_set[0]["name"]):
            connected_set.append(reg2)

        # 2. Fallback to closest boundary distance if probe didn't resolve two regions
        if len(connected_set) < 2:
            scored_regions = []
            for reg in all_regions:
                d = dist_to_bbox(cx, cy, reg["bbox"])
                scored_regions.append((d, reg))
            scored_regions.sort(key=lambda item: item[0])

            existing_names = {r["name"] for r in connected_set}
            for d, reg in scored_regions:
                if reg["name"] not in existing_names and d <= 25.0:
                    connected_set.append(reg)
                    existing_names.add(reg["name"])
                if len(connected_set) == 2:
                    break

        # Populate Door metadata
                # Populate Door metadata
        door.connected_regions = [r["name"] for r in connected_set]
        door.associated_rooms = [r["id"] for r in connected_set if r["type"] == "room"]

        # Create Connection if two regions are bridged
        if len(connected_set) == 2:
            rA, rB = connected_set[0], connected_set[1]
            # Distance via door center
            d_A = np.hypot(rA["center"][0] - cx, rA["center"][1] - cy)
            d_B = np.hypot(rB["center"][0] - cx, rB["center"][1] - cy)
            total_dist = float(round(d_A + d_B, 1))

            connections.append(Connection(
                source=rA["name"],
                destination=rB["name"],
                via_door=door.name,
                distance=total_dist,
            ))

    return connections


def save_floorplan_json(floorplan: FloorPlan, output_path: Path) -> Path:
    """Serialize the complete FloorPlan model to structured JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json_str = floorplan.model_dump_json(indent=2)
        f.write(json_str)
    return output_path


def parse_floorplan(image_path: Path) -> FloorPlan:
    """Full Phase 2 & 3 Computer Vision and Floor Plan pipeline.
    Extracts rooms, doors, corridors, walls, and door-to-region connections.
    Generates all debugging images and console report.
    """
    img = load_floorplan(image_path)
    img = resize_image(img, max_dim=800)
    gray = convert_to_grayscale(img)
    denoised = denoise_image(gray, ksize=3)

    # 1. Binary representation: walls are 255 (foreground), free space is 0
    # Keep dark, low-saturation pixels as structural candidates.
    # This helps exclude colored furniture and room-fill overlays.
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]

    walls_bin = (
        (value < 110) &
        (saturation < 100)
        ).astype(np.uint8) * 255

    # 2. Close door gaps in walls using morphological closing
    k_h = cv2.getStructuringElement(cv2.MORPH_RECT, (51, 1))
    k_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 51))
    closed_h = cv2.morphologyEx(walls_bin, cv2.MORPH_CLOSE, k_h)
    closed_v = cv2.morphologyEx(walls_bin, cv2.MORPH_CLOSE, k_v)
    closed_walls = cv2.bitwise_or(closed_h, closed_v)

    # 3. Detect structural walls via Canny + Hough + Collinear Merging
    edges = cv2.Canny(walls_bin, 50, 150)
    walls = _detect_walls(edges)

    # 4. Detect doors via wall gap analysis
    doors = _detect_doors(walls_bin, closed_walls)

    # 5. Detect enclosed rooms and corridors
    rooms, corridors = _detect_rooms_and_corridors(closed_walls)

    # 6. Associate doors to regions and construct connections
    connections = _associate_doors_to_regions(doors, rooms, corridors)

    # Generate individual debugging images in data/processed/
    rooms_debug = img.copy()
    for room in rooms:
        b = room.bounding_box
        cv2.rectangle(rooms_debug, (b.x, b.y), (b.x2, b.y2), (0, 220, 0), 2)
        cv2.putText(rooms_debug, room.name, (b.x + 10, b.y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 160, 0), 2)
    save_image(rooms_debug, 'rooms_debug.png')

    doors_debug = img.copy()
    for door in doors:
        b = door.bounding_box
        cv2.rectangle(doors_debug, (b.x, b.y), (b.x2, b.y2), (255, 0, 255), 2)
        cv2.circle(doors_debug, door.center, 4, (0, 0, 255), -1)
        cv2.putText(doors_debug, door.name, (door.center[0] - 15, door.center[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 0, 200), 1)
    save_image(doors_debug, 'doors_debug.png')

    walls_debug = img.copy()
    for wall in walls:
        cv2.line(walls_debug, wall.start, wall.end, (0, 0, 255), 2)
        mid = ((wall.start[0] + wall.end[0]) // 2, (wall.start[1] + wall.end[1]) // 2)
        cv2.putText(walls_debug, f"W{wall.id}", mid, cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 180), 1)
    save_image(walls_debug, 'walls_debug.png')

    corridors_debug = img.copy()
    for cor in corridors:
        b = cor.bounding_box
        cv2.rectangle(corridors_debug, (b.x, b.y), (b.x2, b.y2), (255, 200, 0), 2)
        cv2.putText(corridors_debug, cor.name, (b.x + 15, b.y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 150, 0), 2)
    save_image(corridors_debug, 'corridors_debug.png')

    floorplan = FloorPlan(
        image_path=str(image_path),
        image_width=img.shape[1],
        image_height=img.shape[0],
        rooms=rooms,
        doors=doors,
        corridors=corridors,
        walls=walls,
        connections=connections,
    )

    # Save structured JSON
    processed_dir = Path("data/processed")
    save_floorplan_json(floorplan, processed_dir / "floorplan.json")

    # Console debugging report formatted to user specification
    print("========================================")
    print("MAPMIND FLOOR PLAN DETECTION")
    print("========================================")
    print(f"Image: {image_path}")
    print()
    print(f"Rooms detected: {len(rooms)}")
    print(f"Doors detected: {len(doors)}")
    print(f"Corridors detected: {len(corridors)}")
    print(f"Walls detected: {len(walls)}")
    print(f"Connections detected: {len(connections)}")
    print()
    print("Rooms:")
    for room in rooms:
        b = room.bounding_box
        print(f"{room.name}: bbox=({b.x},{b.y},{b.width},{b.height}), center={room.center}, area={room.area}")
    print()
    print("Doors:")
    for door in doors:
        b = door.bounding_box
        print(f"{door.name}: bbox=({b.x},{b.y},{b.width},{b.height}), center={door.center}, orientation={door.orientation}, connected={door.connected_regions}")
    print()
    print("Corridors:")
    for cor in corridors:
        b = cor.bounding_box
        print(f"{cor.name}: bbox=({b.x},{b.y},{b.width},{b.height}), center={cor.center}, area={cor.area}")
    print()
    print("Connections:")
    for conn in connections:
        print(f"{conn.source} <--> {conn.destination} via {conn.via_door} (dist={conn.distance})")
    print("========================================")

    return floorplan
