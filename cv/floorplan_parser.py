"""cv/floorplan_parser.py

Robust floor-plan detection pipeline.

Pipeline stages:
  1. Preprocessing – adaptive binarisation to extract structural walls
  2. Wall mask construction (original + closed/repaired)
  3. Wall segment detection via Hough transform + collinear merging
  4. Room/corridor segmentation from closed-wall free-space regions
  5. Door detection using multi-modal gap analysis and verified symbol boundaries
  6. Door-to-region association via bi-directional boundary probing
  7. Connection graph construction
  8. Debug image generation

All thresholds are computed relative to the image dimensions so the
pipeline generalises across resolutions, line thickness, and drawing
styles.
"""

import re
import cv2
import numpy as np
from dataclasses import replace
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from .coordinates import scale_floorplan_to_source
from .models import BoundingBox, Room, Door, Wall, Corridor, FloorPlan, Connection
from .ocr import OCRToken, extract_text_tokens, normalize_label, normalize_text
from .pipeline_config import CVConfig
from .preprocessing import (
    load_floorplan,
    resize_image,
    save_image,
)
from utils.config import DEFAULT_MAX_DIMENSION, PROCESSED_DATA_DIR


# ── helpers ───────────────────────────────────────────────────────────────

def _scale(value: int, img_dim: int, ref_dim: int = 800) -> int:
    """Scale a pixel value proportionally to image size (reference 800px)."""
    return max(1, int(round(value * img_dim / ref_dim)))


def _odd(n: int) -> int:
    """Ensure *n* is odd and ≥ 3 (required by many OpenCV kernels)."""
    n = max(3, int(n))
    return n if n % 2 == 1 else n + 1


# ── 1. ADAPTIVE WALL BINARISATION ─────────────────────────────────────────

def _suppress_text_artifacts(
    walls_bin: np.ndarray,
    config: Optional[CVConfig] = None,
) -> np.ndarray:
    """Remove isolated printed labels that binarise as short wall fragments.

    Store names such as "Store" are small, dense components that are usually
    detached from the structural wall network. Components that touch a large
    wall fragment are left alone so door jambs, arcs, and short wall stubs are
    not discarded.
    """
    cfg = config or CVConfig()
    h, w = walls_bin.shape[:2]
    dim = max(h, w)
    total_area = h * w
    min_side = max(6, int(round(dim * cfg.text_artifact_min_side_ratio)))
    max_side = dim * cfg.text_artifact_max_side_ratio
    max_area = total_area * cfg.text_artifact_max_area_ratio

    num, labels, stats, _ = cv2.connectedComponentsWithStats(
        walls_bin, connectivity=8
    )
    candidates: List[int] = []
    structural = np.zeros_like(walls_bin)
    for i in range(1, num):
        bw = int(stats[i, cv2.CC_STAT_WIDTH])
        bh = int(stats[i, cv2.CC_STAT_HEIGHT])
        area = int(stats[i, cv2.CC_STAT_AREA])
        side_min, side_max = min(bw, bh), max(bw, bh)
        fill = area / max(bw * bh, 1)
        text_like = (
            side_min >= min_side
            and side_max <= max_side
            and cfg.text_artifact_min_fill_ratio <= fill <= cfg.text_artifact_max_fill_ratio
            and area <= max_area
        )
        if text_like:
            candidates.append(i)
        else:
            structural[labels == i] = 255

    if not candidates:
        return walls_bin

    clearance = _odd(max(11, int(round(dim * cfg.text_artifact_wall_clearance_ratio))))
    near_wall = cv2.dilate(
        structural, cv2.getStructuringElement(cv2.MORPH_RECT, (clearance, clearance))
    )
    cleaned = walls_bin.copy()
    for i in candidates:
        mask = labels == i
        if not np.any(near_wall[mask]):
            cleaned[mask] = 0
    return cleaned


def _binarise_walls(
    img_bgr: np.ndarray,
    config: Optional[CVConfig] = None,
) -> Tuple[np.ndarray, List[Tuple[int, int, int, int]]]:
    """Produce a binary structural mask and locate coloured door symbols.

    The mask deliberately contains only likely architectural line-work. It is
    used for wall candidates and room sealing; door symbols are returned
    separately so they do not become walls.

    Key improvements over the previous version:
      - dark/medium-grey walls are retained, not only near-black lines;
      - coloured fixtures are excluded from the structural mask;
      - green/cyan window symbols are added only on the exterior envelope and
        as outlines, not as filled interior obstacles;
      - small text glyphs and speckles are removed with a size filter scaled
        to the image.
    """
    cfg = config or CVConfig()
    h, w = img_bgr.shape[:2]
    dim = max(h, w)
    total_area = h * w

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]

    channel_spread = np.max(img_bgr.astype(int), axis=2) - np.min(img_bgr.astype(int), axis=2)
    is_achromatic = channel_spread < cfg.achromatic_delta
    is_color_drawing = np.count_nonzero(sat > 35) > (total_area * cfg.color_saturation_ratio)
    door_boxes: List[Tuple[int, int, int, int]] = []

    if is_color_drawing:
        structural = (
            (is_achromatic & (val < cfg.wall_value_max))
            | (val < cfg.very_dark_value)
        ).astype(np.uint8) * 255

        window_mask = (
            (hsv[:, :, 0] >= 35) & (hsv[:, :, 0] <= 95)
            & (sat >= 20) & (sat <= 150)
            & (val >= 135)
        ).astype(np.uint8)
        num_win, labels_win, stats_win, _ = cv2.connectedComponentsWithStats(
            window_mask, connectivity=8
        )
        border_margin = int(round(dim * cfg.window_border_ratio))
        for i in range(1, num_win):
            x, y, bw, bh, area = stats_win[i]
            if area < max(12, int(total_area * 0.00002)):
                continue
            near_border = (
                x <= border_margin
                or y <= border_margin
                or x + bw >= w - border_margin
                or y + bh >= h - border_margin
            )
            elongated = (
                max(bw, bh) >= 2.5 * max(min(bw, bh), 1)
                and min(bw, bh) <= max(4, int(dim * 0.025))
            )
            if not (near_border or elongated):
                continue
            component = (labels_win == i).astype(np.uint8) * 255
            contours, _ = cv2.findContours(component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(structural, contours, -1, 255, 1)

        door_bgr = np.array(cfg.door_symbol_bgr, dtype=int)
        purple_mask = (
            np.abs(img_bgr.astype(int) - door_bgr).max(axis=2)
            < cfg.door_symbol_tolerance
        )
        min_door_symbol_area = max(8, int(total_area * cfg.door_symbol_min_area_ratio))
        num_d, _, stats_d, _ = cv2.connectedComponentsWithStats(
            purple_mask.astype(np.uint8) * 255, connectivity=8
        )
        for i in range(1, num_d):
            area = int(stats_d[i, cv2.CC_STAT_AREA])
            if area < min_door_symbol_area:
                continue
            bx, by, bw, bh = (
                int(stats_d[i, 0]), int(stats_d[i, 1]),
                int(stats_d[i, 2]), int(stats_d[i, 3]),
            )
            aspect = max(bw, bh) / max(min(bw, bh), 1)
            if (
                aspect > cfg.door_symbol_max_aspect_ratio
                or min(bw, bh) < max(2, int(round(dim * cfg.door_symbol_min_side_ratio)))
            ):
                continue
            door_boxes.append((bx, by, bw, bh))
    else:
        k = _odd(_scale(3, dim))
        denoised = cv2.GaussianBlur(gray, (k, k), 0)
        _, otsu = cv2.threshold(
            denoised, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        block = _odd(max(15, int(round(dim * cfg.adaptive_block_ratio))))
        adaptive = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            block,
            cfg.adaptive_c,
        )
        # Union avoids losing faint or thick walls that one method misses.
        structural = cv2.bitwise_or(otsu, adaptive)

    min_dim = max(4, int(round(dim * cfg.min_structure_dim_ratio)))
    num_c, labels_c, stats_c, _ = cv2.connectedComponentsWithStats(
        structural, connectivity=8
    )
    walls_bin = np.zeros_like(structural)
    for i in range(1, num_c):
        if max(stats_c[i, cv2.CC_STAT_WIDTH], stats_c[i, cv2.CC_STAT_HEIGHT]) >= min_dim:
            walls_bin[labels_c == i] = 255

    walls_bin = _suppress_text_artifacts(walls_bin, config=cfg)
    return walls_bin, door_boxes


# ── 2. WALL CLOSING / REPAIR ─────────────────────────────────────────────

def _close_wall_gaps(
    walls_bin: np.ndarray,
    door_boxes: Optional[List[Tuple[int, int, int, int]]] = None,
    config: Optional[CVConfig] = None,
) -> np.ndarray:
    """Repair tiny line breaks, then seal known/suspected door openings.

    A two-stage approach is used deliberately:

    1. A *micro* close repairs 1–5 pixel raster breaks without changing the
       architecture.
    2. Directional closing spans only the configured maximum door width.
       Annotated door symbols contribute a single thin barrier along the
       opening instead of a filled rectangle, avoiding the enclosed door-arc
       pockets produced by the previous implementation.
    """
    cfg = config or CVConfig()
    h, w = walls_bin.shape[:2]
    dim = max(h, w)

    base = walls_bin.copy()
    if door_boxes:
        for (dx, dy, dw, dh) in door_boxes:
            x0 = max(0, dx)
            y0 = max(0, dy)
            x1 = min(w, dx + dw)
            y1 = min(h, dy + dh)
            if x1 <= x0 or y1 <= y0:
                continue
            patch = walls_bin[y0:y1, x0:x1]
            if dw >= dh:
                # The arc bbox is not centred on the wall. Seal along the row
                # inside the bbox that actually contains the wall line.
                row_sums = patch.sum(axis=1)
                y = y0 + int(np.argmax(row_sums)) if row_sums.size else dy + dh // 2
                cv2.line(base, (x0, y), (x1, y), 255, 1)
            else:
                col_sums = patch.sum(axis=0)
                x = x0 + int(np.argmax(col_sums)) if col_sums.size else dx + dw // 2
                cv2.line(base, (x, y0), (x, y1), 255, 1)

    micro = max(1, int(round(dim * cfg.micro_close_ratio)))
    micro_k = cv2.getStructuringElement(cv2.MORPH_RECT, (micro, micro))
    repaired = cv2.morphologyEx(base, cv2.MORPH_CLOSE, micro_k)

    gap_len = max(9, int(round(dim * cfg.segmentation_gap_ratio)))
    k_h = cv2.getStructuringElement(cv2.MORPH_RECT, (gap_len, 1))
    k_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, gap_len))

    closed_h = cv2.morphologyEx(repaired, cv2.MORPH_CLOSE, k_h)
    closed_v = cv2.morphologyEx(repaired, cv2.MORPH_CLOSE, k_v)
    return cv2.bitwise_or(closed_h, closed_v)


def _select_closed_walls(
    walls_bin: np.ndarray,
    door_boxes: Optional[List[Tuple[int, int, int, int]]],
    config: Optional[CVConfig] = None,
) -> np.ndarray:
    """Choose the gap size that yields the most plausible sealed regions.

    A single ratio cannot serve both large apartment rooms and densely packed
    mall units: too small leaves doorways open, while too large bridges short
    store walls. The candidate gap that produces the most valid rooms and
    corridors wins, with ties resolved toward the stronger closure.
    """
    cfg = config or CVConfig()
    if not cfg.adaptive_segmentation:
        return _close_wall_gaps(walls_bin, door_boxes, config=cfg)

    best_closed: Optional[np.ndarray] = None
    best_score = -1
    for ratio in cfg.segmentation_gap_candidates:
        candidate_cfg = replace(
            cfg, segmentation_gap_ratio=float(ratio), adaptive_segmentation=False
        )
        closed = _close_wall_gaps(walls_bin, door_boxes, config=candidate_cfg)
        rooms, corridors, _ = _segment_regions(
            closed, walls_bin, config=candidate_cfg
        )
        score = len(rooms) + len(corridors)
        if score >= best_score:
            best_score = score
            best_closed = closed

    return best_closed if best_closed is not None else walls_bin


# ── 3. WALL SEGMENT DETECTION (Hough + Merge) ────────────────────────────

def _orientation_from_angle(angle_deg: float) -> str:
    angle = angle_deg % 180.0
    if angle <= 22.5 or angle >= 157.5:
        return "horizontal"
    if 67.5 <= angle <= 112.5:
        return "vertical"
    return "diagonal"


def _line_support(
    wall_mask: np.ndarray,
    p1: Tuple[int, int],
    p2: Tuple[int, int],
    radius: int = 1,
    samples: int = 24,
) -> float:
    """Fraction of sampled points lying on the wall mask."""
    length = float(np.hypot(p2[0] - p1[0], p2[1] - p1[1]))
    if length <= 0:
        return 0.0
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1)
    )
    dilated = cv2.dilate(wall_mask, kernel, iterations=1)
    hits = 0
    for i in range(samples):
        t = i / max(samples - 1, 1)
        x = int(round(p1[0] + (p2[0] - p1[0]) * t))
        y = int(round(p1[1] + (p2[1] - p1[1]) * t))
        if 0 <= y < dilated.shape[0] and 0 <= x < dilated.shape[1] and dilated[y, x]:
            hits += 1
    return hits / samples


def _merge_lines(
    raw_lines: np.ndarray,
    angle_tol_deg: float = 7.5,
    tol_dist: int = 10,
    gap_tol: int = 10,
    min_len: int = 20,
) -> List[Tuple[Tuple[int, int], Tuple[int, int], str]]:
    """Cluster near-parallel/collinear Hough lines and merge overlaps.

    Unlike the former horizontal/vertical-only implementation this preserves
    diagonal walls, clusters by angle *and* perpendicular offset, and only
    joins gaps smaller than ``gap_tol`` so door openings remain open.
    """
    if raw_lines is None or len(raw_lines) == 0:
        return []

    parsed: List[Dict[str, float]] = []
    for x1, y1, x2, y2 in raw_lines.reshape(-1, 4):
        length = float(np.hypot(x2 - x1, y2 - y1))
        if length <= 0:
            continue
        angle = float(np.degrees(np.arctan2(y2 - y1, x2 - x1)) % 180.0)
        theta = np.radians(angle)
        dx, dy = float(np.cos(theta)), float(np.sin(theta))
        nx, ny = -dy, dx
        mid_x, mid_y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        offset = mid_x * nx + mid_y * ny
        t1 = x1 * dx + y1 * dy
        t2 = x2 * dx + y2 * dy
        parsed.append({
            "angle": angle,
            "offset": offset,
            "start": min(t1, t2),
            "end": max(t1, t2),
            "length": length,
        })

    groups: List[Dict[str, Any]] = []
    for line in sorted(parsed, key=lambda item: item["length"], reverse=True):
        best_group = None
        best_score = float("inf")
        for group in groups:
            diff = abs(line["angle"] - group["angle"])
            diff = min(diff, 180.0 - diff)
            if diff > angle_tol_deg:
                continue
            dist = abs(line["offset"] - group["offset"])
            if dist > tol_dist:
                continue
            score = diff / max(angle_tol_deg, 1e-6) + dist / max(tol_dist, 1)
            if score < best_score:
                best_group, best_score = group, score
        if best_group is None:
            groups.append({
                "angle": line["angle"],
                "offset": line["offset"],
                "lines": [line],
                "weight": line["length"],
            })
        else:
            weight = best_group["weight"] + line["length"]
            best_group["angle"] = (
                best_group["angle"] * best_group["weight"]
                + line["angle"] * line["length"]
            ) / max(weight, 1e-6)
            best_group["offset"] = (
                best_group["offset"] * best_group["weight"]
                + line["offset"] * line["length"]
            ) / max(weight, 1e-6)
            best_group["weight"] = weight
            best_group["lines"].append(line)

    merged: List[Tuple[Tuple[int, int], Tuple[int, int], str]] = []
    for group in groups:
        theta = np.radians(group["angle"])
        dx, dy = float(np.cos(theta)), float(np.sin(theta))
        nx, ny = -dy, dx
        offset = group["offset"]
        intervals = sorted(
            ((line["start"], line["end"]) for line in group["lines"]),
            key=lambda item: item[0],
        )
        cur_start, cur_end = intervals[0]
        segments: List[Tuple[float, float]] = []
        for start, end in intervals[1:]:
            if start - cur_end <= gap_tol:
                cur_end = max(cur_end, end)
            else:
                segments.append((cur_start, cur_end))
                cur_start, cur_end = start, end
        segments.append((cur_start, cur_end))

        for start, end in segments:
            if end - start < min_len:
                continue
            p1 = (
                int(round(nx * offset + dx * start)),
                int(round(ny * offset + dy * start)),
            )
            p2 = (
                int(round(nx * offset + dx * end)),
                int(round(ny * offset + dy * end)),
            )
            merged.append((p1, p2, _orientation_from_angle(group["angle"])))

    # Remove near-identical segments that can survive from separate angle
    # clusters (e.g. a 0-degree and a 2-degree Hough edge pair).
    deduped: List[Tuple[Tuple[int, int], Tuple[int, int], str]] = []
    for p1, p2, ori in merged:
        duplicate = False
        for q1, q2, _ in deduped:
            if (
                np.hypot(p1[0] - q1[0], p1[1] - q1[1]) <= 2.5
                and np.hypot(p2[0] - q2[0], p2[1] - q2[1]) <= 2.5
            ) or (
                np.hypot(p1[0] - q2[0], p1[1] - q2[1]) <= 2.5
                and np.hypot(p2[0] - q1[0], p2[1] - q1[1]) <= 2.5
            ):
                duplicate = True
                break
        if not duplicate:
            deduped.append((p1, p2, ori))
    return deduped


def _detect_walls(
    walls_bin: np.ndarray,
    config: Optional[CVConfig] = None,
) -> Tuple[List[Wall], List[Tuple[Tuple[int, int], Tuple[int, int]]]]:
    """Detect structural wall centre-lines with Hough + geometric merging."""
    cfg = config or CVConfig()
    h, w = walls_bin.shape[:2]
    dim = max(h, w)

    edges = cv2.Canny(walls_bin, 50, 150)
    min_line_len = max(8, int(round(dim * cfg.wall_min_length_ratio)))
    max_line_gap = max(3, int(round(dim * cfg.hough_max_gap_ratio)))
    hough_thresh = max(8, int(round(dim * cfg.hough_threshold_ratio)))

    raw_lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=hough_thresh,
        minLineLength=min_line_len,
        maxLineGap=max_line_gap,
    )
    if raw_lines is None:
        return [], []

    candidates = [
        ((int(x1), int(y1)), (int(x2), int(y2)))
        for x1, y1, x2, y2 in raw_lines.reshape(-1, 4)
    ]
    tol_dist = max(4, int(round(dim * cfg.merge_distance_ratio)))
    gap_tol = max(3, int(round(dim * cfg.merge_gap_ratio)))
    min_len = max(8, int(round(dim * cfg.wall_min_length_ratio)))
    merged = _merge_lines(
        raw_lines,
        angle_tol_deg=cfg.merge_angle_deg,
        tol_dist=tol_dist,
        gap_tol=gap_tol,
        min_len=min_len,
    )

    walls: List[Wall] = []
    for p1, p2, ori in merged:
        support = _line_support(
            walls_bin, p1, p2, radius=cfg.wall_support_radius
        )
        if support < cfg.wall_support_min:
            continue
        length = float(np.hypot(p2[0] - p1[0], p2[1] - p1[1]))
        walls.append(Wall(
            id=len(walls) + 1,
            start=p1,
            end=p2,
            length=length,
            orientation=ori,
            confidence=round(float(support), 3),
        ))
    return walls, candidates


# ── 4. ROOM / CORRIDOR DETECTION ─────────────────────────────────────────

def _segment_regions(
    closed_walls: np.ndarray,
    walls_bin: np.ndarray,
    config: Optional[CVConfig] = None,
) -> Tuple[List[Room], List[Corridor], Dict[str, Dict[str, Any]]]:
    """Segment enclosed free-space regions and return their actual masks.

    The masks are kept so doors can be associated with the regions they
    actually touch instead of whichever region bounding box happens to
    contain a probe point. Region shape (minimum-area rectangle) rather than
    an axis-aligned bbox is used for corridor classification.
    """
    cfg = config or CVConfig()
    h, w = closed_walls.shape[:2]
    dim = max(h, w)
    total_area = h * w

    free_space = cv2.bitwise_not(closed_walls)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        free_space, connectivity=8,
    )
    exterior_labels = set(np.unique(np.concatenate([
        labels[0, :], labels[h - 1, :], labels[:, 0], labels[:, w - 1],
    ])))

    min_area = max(160, int(total_area * cfg.room_min_area_ratio))
    max_area = int(total_area * cfg.room_max_area_ratio)
    min_dim = max(8, int(round(dim * cfg.room_min_dim_ratio)))

    candidates: List[Dict[str, Any]] = []
    for i in range(1, num_labels):
        if i in exterior_labels:
            continue
        x, y, bw, bh, area = stats[i]
        if area < min_area or area > max_area or min(bw, bh) < min_dim:
            continue

        mask = (labels == i).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        contour = max(contours, key=cv2.contourArea)
        (_, _), (rect_w, rect_h), _ = cv2.minAreaRect(contour)
        long_side = max(rect_w, rect_h)
        short_side = max(min(rect_w, rect_h), 1.0)
        aspect = long_side / short_side
        solidity = float(area) / max(long_side * short_side, 1.0)
        cx, cy = int(round(centroids[i][0])), int(round(centroids[i][1]))

        candidates.append({
            "label": i,
            "bbox": BoundingBox(x=int(x), y=int(y), width=int(bw), height=int(bh)),
            "center": (cx, cy),
            "width": int(bw),
            "height": int(bh),
            "area": int(area),
            "mask": mask,
            "aspect": aspect,
            "short_side": short_side,
            "solidity": solidity,
        })

    filtered: List[Dict[str, Any]] = []
    for i, cand in enumerate(candidates):
        nested = False
        b1 = cand["bbox"]
        for j, other in enumerate(candidates):
            if i == j:
                continue
            b2 = other["bbox"]
            if (
                b2.x <= b1.x and b2.y <= b1.y
                and b1.x2 <= b2.x2 and b1.y2 <= b2.y2
                and cand["area"] < other["area"] * 0.5
            ):
                nested = True
                break
        if not nested:
            filtered.append(cand)

    candidate_rooms: List[Dict[str, Any]] = []
    candidate_corridors: List[Dict[str, Any]] = []
    for cand in filtered:
        is_corridor = (
            cand["aspect"] >= cfg.corridor_aspect_ratio
            and cand["short_side"] <= dim * cfg.corridor_max_width_ratio
            and cand["solidity"] >= 0.20
        )
        (candidate_corridors if is_corridor else candidate_rooms).append(cand)

    row_bucket = max(1, dim // 16)
    candidate_rooms.sort(key=lambda r: (r["bbox"].y // row_bucket, r["bbox"].x))
    candidate_corridors.sort(key=lambda c: (c["bbox"].y // row_bucket, c["bbox"].x))

    rooms: List[Room] = []
    region_data: Dict[str, Dict[str, Any]] = {}
    for idx, cand in enumerate(candidate_rooms, start=1):
        name = f"Room_{idx}"
        rooms.append(Room(
            id=idx,
            name=name,
            bounding_box=cand["bbox"],
            center=cand["center"],
            width=cand["width"],
            height=cand["height"],
            area=cand["area"],
        ))
        region_data[name] = {"type": "room", "mask": cand["mask"]}

    corridors: List[Corridor] = []
    for idx, cand in enumerate(candidate_corridors, start=1):
        name = f"Corridor_{idx}"
        corridors.append(Corridor(
            id=idx,
            name=name,
            bounding_box=cand["bbox"],
            center=cand["center"],
            area=cand["area"],
        ))
        region_data[name] = {"type": "corridor", "mask": cand["mask"]}

    return rooms, corridors, region_data


def _detect_rooms_and_corridors(
    closed_walls: np.ndarray,
    walls_bin: np.ndarray,
    config: Optional[CVConfig] = None,
) -> Tuple[List[Room], List[Corridor]]:
    """Backward-compatible wrapper returning only room/corridor models."""
    rooms, corridors, _ = _segment_regions(closed_walls, walls_bin, config=config)
    return rooms, corridors


def _group_ocr_lines(tokens: List[OCRToken]) -> List[OCRToken]:
    grouped: List[OCRToken] = []
    groups: Dict[str, List[OCRToken]] = {}
    for token in tokens:
        key = token.line_key or f"single:{token.bbox}"
        groups.setdefault(key, []).append(token)
    for line_tokens in groups.values():
        ordered = sorted(line_tokens, key=lambda item: item.bbox[0])
        text = " ".join(item.text for item in ordered)
        confidence = min(item.confidence for item in ordered)
        x0 = min(item.bbox[0] for item in ordered)
        y0 = min(item.bbox[1] for item in ordered)
        x1 = max(item.bbox[0] + item.bbox[2] for item in ordered)
        y1 = max(item.bbox[1] + item.bbox[3] for item in ordered)
        grouped.append(OCRToken(
            text=text,
            confidence=confidence,
            bbox=(x0, y0, x1 - x0, y1 - y0),
            line_key=ordered[0].line_key,
        ))
    return grouped


def _safe_label_name(text: str) -> str:
    value = normalize_text(text)
    value = re.sub(r"[^A-Za-z0-9&' .-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .-")
    if value and value.islower():
        value = value.title()
    return value[:48]


def _assign_semantic_labels(
    rooms: List[Room],
    corridors: List[Corridor],
    region_data: Dict[str, Dict[str, Any]],
    tokens: List[OCRToken],
) -> Dict[str, Dict[str, Any]]:
    """Associate OCR lines with the region masks they overlap.

    OCR confidence and semantic-class confidence remain separate. Unknown
    but legible shop names are retained as printed names with zero
    classification confidence instead of being invented into a category.
    """
    if not tokens:
        return region_data

    lines = _group_ocr_lines(tokens)
    best: Dict[str, Tuple[float, OCRToken]] = {}
    for token in lines:
        x, y, w, h = token.bbox
        if w <= 0 or h <= 0:
            continue
        for name, data in region_data.items():
            mask = data["mask"]
            height, width = mask.shape[:2]
            x0, y0 = max(0, x), max(0, y)
            x1, y1 = min(width, x + w), min(height, y + h)
            if x1 <= x0 or y1 <= y0:
                continue
            token_area = max(w * h, 1)
            overlap = int(np.count_nonzero(mask[y0:y1, x0:x1]))
            score = overlap / token_area
            if score < 0.20:
                continue
            weighted = score * (token.confidence / 100.0)
            current = best.get(name)
            if current is None or weighted > current[0]:
                best[name] = (weighted, token)

    if not best:
        return region_data

    used_names = {room.name for room in rooms} | {corridor.name for corridor in corridors}
    final_names: Dict[str, str] = {}
    for region_name in list(region_data.keys()):
        if region_name not in best:
            continue
        _, token = best[region_name]
        canonical, class_base_conf = normalize_label(token.text)
        raw_base = _safe_label_name(token.text)
        base = canonical or raw_base
        if not base:
            continue
        candidate = base
        suffix = 2
        while candidate in used_names and candidate != region_name:
            candidate = f"{base} {suffix}"
            suffix += 1
        used_names.discard(region_name)
        used_names.add(candidate)
        final_names[region_name] = candidate

        label_conf = max(0.0, min(1.0, token.confidence / 100.0))
        classification_conf = round(class_base_conf * label_conf, 3)
        for room in rooms:
            if room.name == region_name:
                room.name = candidate
                room.semantic_label = base
                room.label_confidence = round(label_conf, 3)
                room.classification_confidence = classification_conf
                room.label_source = "ocr"
                break
        for corridor in corridors:
            if corridor.name == region_name:
                corridor.name = candidate
                corridor.semantic_label = base
                corridor.label_confidence = round(label_conf, 3)
                corridor.classification_confidence = classification_conf
                corridor.label_source = "ocr"
                break

    if not final_names:
        return region_data
    updated: Dict[str, Dict[str, Any]] = {}
    for old_name, data in region_data.items():
        updated[final_names.get(old_name, old_name)] = data
    return updated


# ── 5. DOOR DETECTION & ASSOCIATION ──────────────────────────────────────

def _detect_and_associate_doors(
    walls_bin: np.ndarray,
    closed_walls: np.ndarray,
    rooms: List[Room],
    corridors: List[Corridor],
    door_boxes: Optional[List[Tuple[int, int, int, int]]] = None,
    region_data: Optional[Dict[str, Dict[str, Any]]] = None,
    config: Optional[CVConfig] = None,
) -> Tuple[List[Door], List[Connection], List[Dict[str, Any]]]:
    """Detect door candidates and associate them with actual region masks.

    Symbols and wall-gap candidates are combined, spatially deduplicated, and
    then validated by probing both sides of the opening in the segmentation
    label map. A door is accepted only when it touches two distinct regions.
    """
    cfg = config or CVConfig()
    h, w = walls_bin.shape[:2]
    dim = max(h, w)

    all_regions: List[Dict[str, Any]] = []
    for r in rooms:
        all_regions.append({
            "name": r.name, "type": "room", "bbox": r.bounding_box,
            "center": r.center, "id": r.id,
        })
    for c in corridors:
        all_regions.append({
            "name": c.name, "type": "corridor", "bbox": c.bounding_box,
            "center": c.center, "id": c.id,
        })
    region_by_name = {reg["name"]: reg for reg in all_regions}

    if region_data is None:
        region_data = {}
        for reg in all_regions:
            b = reg["bbox"]
            mask = np.zeros((h, w), dtype=np.uint8)
            mask[max(0, b.y):min(h, b.y2), max(0, b.x):min(w, b.x2)] = 1
            region_data[reg["name"]] = {"type": reg["type"], "mask": mask}

    label_map = np.zeros((h, w), dtype=np.int32)
    label_names: List[str] = []
    for idx, (name, data) in enumerate(region_data.items(), start=1):
        mask = data["mask"]
        label_map[mask > 0] = idx
        label_names.append(name)

    def label_at(x: int, y: int) -> Optional[str]:
        if x < 0 or x >= w or y < 0 or y >= h:
            return None
        value = int(label_map[y, x])
        if value <= 0 or value > len(label_names):
            return None
        return label_names[value - 1]

    candidates: List[Dict[str, Any]] = []

    def add_box_candidates(boxes: List[Tuple[int, int, int, int]], method: str, confidence: float) -> None:
        merged: List[Dict[str, int]] = []
        merge_dist = max(10, int(round(dim * cfg.door_merge_distance_ratio)))
        for bx, by, bw, bh in boxes:
            cx, cy = bx + bw // 2, by + bh // 2
            placed = False
            for item in merged:
                if np.hypot(cx - item["cx"], cy - item["cy"]) <= merge_dist:
                    x0 = min(bx, item["x"])
                    y0 = min(by, item["y"])
                    x1 = max(bx + bw, item["x"] + item["w"])
                    y1 = max(by + bh, item["y"] + item["h"])
                    item["x"], item["y"] = x0, y0
                    item["w"], item["h"] = x1 - x0, y1 - y0
                    item["cx"], item["cy"] = (x0 + x1) // 2, (y0 + y1) // 2
                    placed = True
                    break
            if not placed:
                merged.append({
                    "x": bx, "y": by, "w": bw, "h": bh, "cx": cx, "cy": cy,
                })
        for item in merged:
            bbox = BoundingBox(
                x=item["x"], y=item["y"], width=item["w"], height=item["h"]
            )
            candidates.append({
                "bbox": bbox,
                "center": (item["cx"], item["cy"]),
                "orientation": "horizontal" if item["w"] >= item["h"] else "vertical",
                "confidence": confidence,
                "method": method,
            })

    if door_boxes:
        add_box_candidates(door_boxes, "door_symbol", 0.90)

    # Pairwise region-gap candidates: only pixels that are (a) added by
    # segmentation closing, (b) not actual walls, and (c) near two different
    # region masks. This avoids the old whole-image gap mask, whose antialiased
    # wall outlines looked like enormous "door" components.
    min_door_area = max(12, int(round(h * w * cfg.door_min_area_ratio)))
    max_door_area = max(min_door_area + 1, int(round(h * w * cfg.door_max_area_ratio)))
    min_region_gap_area = max(
        min_door_area,
        int(round(h * w * cfg.door_region_gap_min_area_ratio)),
    )
    max_region_gap_major = max(
        12,
        int(round(dim * cfg.door_region_gap_max_major_ratio)),
    )
    min_door_dim = max(3, int(round(dim * cfg.door_min_dim_ratio)))
    max_door_minor = max(8, int(round(dim * cfg.door_max_minor_ratio)))
    dilate_radius = max(3, int(round(dim * cfg.door_probe_max_ratio / 2.0)))
    dilate_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (2 * dilate_radius + 1, 2 * dilate_radius + 1),
    )
    region_names = list(region_data.keys())
    dilated_masks = {
        name: cv2.dilate(region_data[name]["mask"].astype(np.uint8), dilate_kernel)
        for name in region_names
    }
    # Ignore antialiased one-pixel outlines around real walls; only pixels
    # well away from an actual wall can be a morphological door bridge.
    wall_clearance = cv2.dilate(
        walls_bin,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
        iterations=1,
    )
    not_near_wall = cv2.bitwise_not(wall_clearance)
    for i in range(len(region_names)):
        for j in range(i + 1, len(region_names)):
            name_a = region_names[i]
            name_b = region_names[j]
            zone = cv2.bitwise_and(
                cv2.bitwise_and(dilated_masks[name_a], dilated_masks[name_b]),
                cv2.bitwise_and(closed_walls, not_near_wall),
            )
            if not np.any(zone):
                continue
            num_zones, _, zone_stats, zone_centroids = cv2.connectedComponentsWithStats(
                zone, connectivity=8
            )
            for k in range(1, num_zones):
                x, y, cw, ch, area = zone_stats[k]
                if area < min_region_gap_area or area > max_door_area:
                    continue
                if max(cw, ch) < min_door_dim or max(cw, ch) > max_region_gap_major:
                    continue
                if min(cw, ch) > max_door_minor:
                    continue
                bbox = BoundingBox(x=int(x), y=int(y), width=int(cw), height=int(ch))
                candidates.append({
                    "bbox": bbox,
                    "center": (
                        int(round(zone_centroids[k][0])),
                        int(round(zone_centroids[k][1])),
                    ),
                    "orientation": "horizontal" if cw >= ch else "vertical",
                    "confidence": 0.78,
                    "method": "region_gap",
                    "preset_pair": (name_a, name_b),
                })

    # Spatially deduplicate candidates from symbols and gap analysis before
    # validation. Symbol candidates are sorted first and win ties.
    candidates.sort(key=lambda item: (-item["confidence"], -item["bbox"].area))
    merge_dist = max(10, int(round(dim * cfg.door_merge_distance_ratio)))
    deduped: List[Dict[str, Any]] = []
    for cand in candidates:
        cx, cy = cand["center"]
        duplicate = False
        for kept in deduped:
            kx, ky = kept["center"]
            if np.hypot(cx - kx, cy - ky) <= merge_dist:
                duplicate = True
                break
        if not duplicate:
            deduped.append(cand)

    probe_step = max(2, int(round(dim * cfg.door_probe_step_ratio)))
    max_probe = max(20, int(round(dim * cfg.door_probe_max_ratio)))
    margin = max(2, int(round(dim * cfg.door_association_margin_ratio)))
    fallback_dist = max(15, int(round(dim * cfg.door_fallback_distance_ratio)))

    valid_doors: List[Door] = []
    connections: List[Connection] = []
    accepted_pair_centers: Dict[Tuple[str, str], List[Tuple[int, int]]] = {}
    same_pair_distance = max(10, int(round(dim * cfg.door_duplicate_pair_ratio)))
    has_symbol_candidates = any(item["method"] == "door_symbol" for item in deduped)

    parent = {name: name for name in region_data}

    def find(name: str) -> str:
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    def union(name_a: str, name_b: str) -> None:
        root_a, root_b = find(name_a), find(name_b)
        if root_a != root_b:
            parent[root_b] = root_a

    for cand in deduped:
        cand["accepted"] = False
        bbox = cand["bbox"]
        cx, cy = cand["center"]
        found: List[str] = []
        found_orientation = cand["orientation"]
        used_fallback = False
        used_preset = False

        orientations_to_try = [
            (
                cand["orientation"],
                (0, 1) if cand["orientation"] == "horizontal" else (1, 0),
            ),
            (
                "vertical" if cand["orientation"] == "horizontal" else "horizontal",
                (1, 0) if cand["orientation"] == "horizontal" else (0, 1),
            ),
        ]
        orientation_pairs: List[Tuple[str, List[str]]] = []
        for ori_name, (dx, dy) in orientations_to_try:
            current: List[str] = []
            half_span = (bbox.height / 2.0) if ori_name == "horizontal" else (bbox.width / 2.0)
            start = int(round(half_span + margin))
            for sign in (-1, 1):
                for dist in range(max(1, start), max_probe + 1, probe_step):
                    name = label_at(int(round(cx + sign * dx * dist)), int(round(cy + sign * dy * dist)))
                    if name and name not in current:
                        current.append(name)
                        break
            if len(current) >= 2 and current[:2] not in [pair for _, pair in orientation_pairs]:
                orientation_pairs.append((ori_name, current[:2]))

        if orientation_pairs:
            def pair_cost(item: Tuple[str, List[str]]) -> float:
                return sum(
                    float(np.hypot(
                        region_by_name[name]["center"][0] - cx,
                        region_by_name[name]["center"][1] - cy,
                    ))
                    for name in item[1]
                )

            found_orientation, found = min(orientation_pairs, key=pair_cost)

        if len(found) < 2 and cand.get("preset_pair"):
            preset_a, preset_b = cand["preset_pair"]
            if preset_a != preset_b:
                found = [preset_a, preset_b]
                used_preset = True

        if len(found) < 2:
            # Last resort: nearest actual region masks, not bbox proximity.
            scored: List[Tuple[float, str]] = []
            for name, data in region_data.items():
                mask = data["mask"]
                ys, xs = np.nonzero(mask)
                if xs.size == 0:
                    continue
                distance = float(np.min(np.hypot(xs - cx, ys - cy)))
                scored.append((distance, name))
            scored.sort(key=lambda item: item[0])
            for distance, name in scored:
                if distance <= fallback_dist and name not in found:
                    found.append(name)
                if len(found) == 2:
                    break
            used_fallback = len(found) == 2

        if len(found) != 2 or found[0] == found[1]:
            continue

        if (
            has_symbol_candidates
            and cand["method"] == "region_gap"
            and find(found[0]) == find(found[1])
        ):
            continue

        pair_key = tuple(sorted(found))
        if any(
            np.hypot(cx - px, cy - py) <= same_pair_distance
            for px, py in accepted_pair_centers.get(pair_key, [])
        ):
            continue

        base_conf = float(cand["confidence"])
        confidence = (
            base_conf
            if (used_fallback or used_preset)
            else min(0.98, base_conf + 0.05)
        )
        door = Door(
            id=len(valid_doors) + 1,
            name=f"Door_{len(valid_doors) + 1}",
            bounding_box=bbox,
            center=(cx, cy),
            orientation=found_orientation,
            associated_rooms=[
                region_by_name[name]["id"]
                for name in found
                if region_by_name.get(name, {}).get("type") == "room"
            ],
            connected_regions=found,
            confidence=round(confidence, 3),
            detection_method=cand["method"],
        )
        valid_doors.append(door)
        cand["accepted"] = True
        accepted_pair_centers.setdefault(pair_key, []).append((cx, cy))
        union(found[0], found[1])

        rA = region_by_name[found[0]]
        rB = region_by_name[found[1]]
        d_A = float(np.hypot(rA["center"][0] - cx, rA["center"][1] - cy))
        d_B = float(np.hypot(rB["center"][0] - cx, rB["center"][1] - cy))
        connections.append(Connection(
            source=found[0],
            destination=found[1],
            via_door=door.name,
            distance=float(round(d_A + d_B, 1)),
            confidence=round(confidence, 3),
            reason=(
                f"{cand['method']} candidate bridged {found[0]} and {found[1]}"
                + (
                    " via nearest-mask fallback"
                    if used_fallback
                    else (" via region-gap adjacency" if used_preset else " via mask probing")
                )
            ),
        ))

    # Number doors in stable row-major order rather than candidate confidence
    # order. This keeps IDs intuitive and preserves the established sample-plan
    # IDs while still allowing confidence-based acceptance/merging.
    ordered = sorted(
        zip(valid_doors, connections),
        key=lambda pair: (pair[0].center[1], pair[0].center[0]),
    )
    valid_doors = []
    connections = []
    for idx, (door, conn) in enumerate(ordered, start=1):
        new_name = f"Door_{idx}"
        door.id = idx
        door.name = new_name
        conn.via_door = new_name
        valid_doors.append(door)
        connections.append(conn)

    return valid_doors, connections, deduped


# ── 6. DEBUG IMAGE GENERATION ─────────────────────────────────────────────

def _promote_hub_to_corridor(
    rooms: List[Room],
    corridors: List[Corridor],
    doors: List[Door],
    connections: List[Connection],
    region_data: Dict[str, Dict[str, Any]],
) -> Tuple[List[Room], List[Corridor]]:
    """Promote a high-degree hub to a corridor/hall without renumbering.

    Existing room IDs and names remain stable; only the promoted region is
    renamed. This avoids the old behaviour where unrelated rooms were
    renumbered after door detection.
    """
    if corridors or len(rooms) <= 1:
        return rooms, corridors

    degree: Dict[str, int] = {}
    for conn in connections:
        degree[conn.source] = degree.get(conn.source, 0) + 1
        degree[conn.destination] = degree.get(conn.destination, 0) + 1

    hub = None
    for room in rooms:
        if degree.get(room.name, 0) >= 3:
            if hub is None or degree.get(room.name, 0) > degree.get(hub.name, 0):
                hub = room
    if hub is None:
        return rooms, corridors

    old_name = hub.name
    new_name = old_name if hub.label_source == "ocr" else "Corridor_1"
    existing_names = {r.name for r in rooms if r.name != old_name} | {c.name for c in corridors}
    suffix = 2
    while new_name in existing_names:
        new_name = f"Corridor_{suffix}"
        suffix += 1

    promoted = Corridor(
        id=1,
        name=new_name,
        bounding_box=hub.bounding_box,
        center=hub.center,
        area=hub.area,
        semantic_label=hub.semantic_label,
        label_confidence=hub.label_confidence,
        classification_confidence=hub.classification_confidence,
        label_source=hub.label_source,
    )
    rooms = [room for room in rooms if room.name != old_name]
    corridors = [promoted]

    for door in doors:
        door.connected_regions = [new_name if n == old_name else n for n in door.connected_regions]
        door.associated_rooms = [
            room.id for room in rooms if room.name in door.connected_regions
        ]
    for conn in connections:
        conn.source = new_name if conn.source == old_name else conn.source
        conn.destination = new_name if conn.destination == old_name else conn.destination

    if old_name in region_data:
        region_data[new_name] = region_data.pop(old_name)
        region_data[new_name]["type"] = "corridor"

    return rooms, corridors


def _renumber_rooms(
    rooms: List[Room],
    doors: List[Door],
    connections: List[Connection],
    region_data: Dict[str, Dict[str, Any]],
) -> List[Room]:
    """Make fallback room IDs contiguous after a semantic promotion.

    OCR names are preserved verbatim; only generated ``Room_N`` fallback
    names are remapped. Door/connection references and debug region keys are
    updated consistently.
    """
    mapping: Dict[str, str] = {}
    renumbered: List[Room] = []
    for idx, room in enumerate(rooms, start=1):
        old_name = room.name
        new_name = old_name if room.label_source == "ocr" else f"Room_{idx}"
        mapping[old_name] = new_name
        renumbered.append(room.model_copy(update={"id": idx, "name": new_name}))

    if all(old == new for old, new in mapping.items()):
        return rooms

    for door in doors:
        door.connected_regions = [mapping.get(name, name) for name in door.connected_regions]
        door.associated_rooms = [
            room.id for room in renumbered if room.name in door.connected_regions
        ]
    for conn in connections:
        conn.source = mapping.get(conn.source, conn.source)
        conn.destination = mapping.get(conn.destination, conn.destination)

    for old_name, new_name in mapping.items():
        if old_name != new_name and old_name in region_data:
            region_data[new_name] = region_data.pop(old_name)

    return renumbered


def _save_debug_images(
    img: np.ndarray,
    walls_bin: np.ndarray,
    closed_walls: np.ndarray,
    rooms: List[Room],
    corridors: List[Corridor],
    doors: List[Door],
    walls: List[Wall],
    output_dir: Path,
    wall_candidates: Optional[List[Tuple[Tuple[int, int], Tuple[int, int]]]] = None,
    door_candidates: Optional[List[Dict[str, Any]]] = None,
    region_data: Optional[Dict[str, Dict[str, Any]]] = None,
    source_img: Optional[np.ndarray] = None,
    scale_x: float = 1.0,
    scale_y: float = 1.0,
) -> None:
    """Generate segmentation, candidate, and source-resolution debug views."""

    save_image(walls_bin, "walls_bin_debug.png", output_dir=output_dir)
    save_image(closed_walls, "closed_walls_debug.png", output_dir=output_dir)

    rooms_debug = img.copy()
    for room in rooms:
        b = room.bounding_box
        cv2.rectangle(rooms_debug, (b.x, b.y), (b.x2, b.y2), (0, 220, 0), 2)
        cv2.putText(rooms_debug, room.name, (b.x + 10, b.y + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 160, 0), 2)
    save_image(rooms_debug, "rooms_debug.png", output_dir=output_dir)

    doors_debug = img.copy()
    for door in doors:
        b = door.bounding_box
        cv2.rectangle(doors_debug, (b.x, b.y), (b.x2, b.y2), (255, 0, 255), 2)
        cv2.circle(doors_debug, door.center, 4, (0, 0, 255), -1)
        cv2.putText(doors_debug, door.name,
                    (door.center[0] - 15, door.center[1] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 0, 200), 1)
    save_image(doors_debug, "doors_debug.png", output_dir=output_dir)

    walls_debug = img.copy()
    for wall in walls:
        cv2.line(walls_debug, wall.start, wall.end, (0, 0, 255), 2)
        mid = ((wall.start[0] + wall.end[0]) // 2,
               (wall.start[1] + wall.end[1]) // 2)
        cv2.putText(walls_debug, f"W{wall.id}", mid,
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 180), 1)
    save_image(walls_debug, "walls_debug.png", output_dir=output_dir)

    corridors_debug = img.copy()
    for cor in corridors:
        b = cor.bounding_box
        cv2.rectangle(corridors_debug, (b.x, b.y), (b.x2, b.y2), (255, 200, 0), 2)
        cv2.putText(corridors_debug, cor.name, (b.x + 15, b.y + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 150, 0), 2)
    save_image(corridors_debug, "corridors_debug.png", output_dir=output_dir)

    if region_data:
        regions_debug = img.copy()
        overlay = img.copy()
        palette = [
            (60, 180, 75), (230, 190, 60), (65, 130, 220),
            (180, 80, 200), (60, 190, 190), (220, 90, 90),
        ]
        for idx, (region_name, data) in enumerate(region_data.items()):
            mask = data["mask"]
            color = palette[idx % len(palette)]
            overlay[mask > 0] = color
            ys, xs = np.nonzero(mask)
            if xs.size:
                cv2.putText(
                    regions_debug, region_name,
                    (int(xs.mean()) - 20, int(ys.mean())),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (20, 20, 20), 1,
                )
        regions_debug = cv2.addWeighted(overlay, 0.35, regions_debug, 0.65, 0)
        for room in rooms:
            b = room.bounding_box
            cv2.putText(regions_debug, room.name, (b.x + 5, b.y + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 80, 0), 1)
        for cor in corridors:
            b = cor.bounding_box
            cv2.putText(regions_debug, cor.name, (b.x + 5, b.y + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 60, 160), 1)
        save_image(regions_debug, "segmentation_masks_debug.png", output_dir=output_dir)

    if wall_candidates is not None:
        candidates_debug = img.copy()
        for p1, p2 in wall_candidates:
            cv2.line(candidates_debug, p1, p2, (0, 200, 0), 1)
        for wall in walls:
            cv2.line(candidates_debug, wall.start, wall.end, (0, 0, 255), 2)
        save_image(candidates_debug, "wall_candidates_debug.png", output_dir=output_dir)

    if door_candidates is not None:
        door_candidates_debug = img.copy()
        for cand in door_candidates:
            b = cand["bbox"]
            color = (0, 200, 0) if cand.get("accepted") else (0, 165, 255)
            cv2.rectangle(door_candidates_debug, (b.x, b.y), (b.x2, b.y2), color, 2)
            cv2.putText(
                door_candidates_debug, cand.get("method", "?"),
                (b.x, max(10, b.y - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1,
            )
        save_image(door_candidates_debug, "door_candidates_debug.png", output_dir=output_dir)

    if source_img is not None:
        source_overlay = source_img.copy()
        for wall in walls:
            p1 = (int(round(wall.start[0] * scale_x)), int(round(wall.start[1] * scale_y)))
            p2 = (int(round(wall.end[0] * scale_x)), int(round(wall.end[1] * scale_y)))
            cv2.line(source_overlay, p1, p2, (0, 0, 255), 2)
        for room in rooms:
            b = room.bounding_box
            cv2.rectangle(
                source_overlay,
                (int(round(b.x * scale_x)), int(round(b.y * scale_y))),
                (int(round(b.x2 * scale_x)), int(round(b.y2 * scale_y))),
                (0, 220, 0), 2,
            )
            cv2.putText(
                source_overlay, room.name,
                (int(round(b.x * scale_x)) + 8, int(round(b.y * scale_y)) + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 160, 0), 2,
            )
        for cor in corridors:
            b = cor.bounding_box
            cv2.rectangle(
                source_overlay,
                (int(round(b.x * scale_x)), int(round(b.y * scale_y))),
                (int(round(b.x2 * scale_x)), int(round(b.y2 * scale_y))),
                (255, 200, 0), 2,
            )
            cv2.putText(
                source_overlay, cor.name,
                (int(round(b.x * scale_x)) + 8, int(round(b.y * scale_y)) + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 150, 0), 2,
            )
        for door in doors:
            b = door.bounding_box
            cv2.rectangle(
                source_overlay,
                (int(round(b.x * scale_x)), int(round(b.y * scale_y))),
                (int(round(b.x2 * scale_x)), int(round(b.y2 * scale_y))),
                (255, 0, 255), 2,
            )
        save_image(source_overlay, "source_overlay_debug.png", output_dir=output_dir)


# ── 7. MAIN PIPELINE ─────────────────────────────────────────────────────

def save_floorplan_json(floorplan: FloorPlan, output_path: Path) -> Path:
    """Serialize the complete FloorPlan model to structured JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json_str = floorplan.model_dump_json(indent=2)
        f.write(json_str)
    return output_path


def parse_floorplan(
    image_path: Path | str,
    output_dir: Optional[Path] = None,
    config: Optional[CVConfig] = None,
) -> FloorPlan:
    """Full CV pipeline: extract rooms, doors, corridors, walls, and
    door-to-region connections from a floor-plan image.

    Parameters
    ----------
    image_path:
        Input floor-plan image.
    output_dir:
        Directory for debug images and ``floorplan.json``. Defaults to
        ``utils.config.PROCESSED_DATA_DIR``. Callers such as the Streamlit
        frontend pass a per-upload directory so concurrent uploads cannot
        overwrite each other's artifacts.
    config:
        Optional ``CVConfig``. Thresholds are ratio-based so the same
        configuration works for small apartment plans and large mall plans.
    """
    cfg = config or CVConfig()
    out_dir = Path(output_dir) if output_dir is not None else PROCESSED_DATA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    source_img = load_floorplan(Path(image_path) if isinstance(image_path, str) else image_path)
    source_height, source_width = source_img.shape[:2]
    img = resize_image(source_img, max_dim=cfg.max_dimension)
    working_height, working_width = img.shape[:2]
    scale_x = working_width / max(source_width, 1)
    scale_y = working_height / max(source_height, 1)

    # 1. Binarise walls (adaptive, resolution-aware, multi-modal)
    walls_bin, door_boxes = _binarise_walls(img, config=cfg)

    # 2. Close wall gaps for room segmentation
    closed_walls = _select_closed_walls(walls_bin, door_boxes, config=cfg)

    # 3. Detect structural wall segments and keep candidate lines for debug
    walls, wall_candidates = _detect_walls(walls_bin, config=cfg)

    # 4. Detect enclosed rooms and corridors, retaining real region masks
    rooms, corridors, region_data = _segment_regions(closed_walls, walls_bin, config=cfg)

    # 5. Optional OCR semantic labels (never guesses when no text is read)
    ocr_tokens, ocr_diagnostics = extract_text_tokens(
        img, min_confidence=cfg.ocr_min_confidence
    )
    region_data = _assign_semantic_labels(rooms, corridors, region_data, ocr_tokens)

    # 6. Detect doors and associate them using region masks, not bboxes alone
    doors, connections, door_candidates = _detect_and_associate_doors(
        walls_bin,
        closed_walls,
        rooms,
        corridors,
        door_boxes,
        region_data=region_data,
        config=cfg,
    )

    # 7. Promote a high-degree hub to a corridor/hall without renumbering
    rooms, corridors = _promote_hub_to_corridor(
        rooms, corridors, doors, connections, region_data
    )
    rooms = _renumber_rooms(rooms, doors, connections, region_data)

    diagnostics: Dict[str, Any] = {
        "config": cfg.to_dict(),
        "source_size": [source_width, source_height],
        "working_size": [working_width, working_height],
        "processing_scale": [round(scale_x, 4), round(scale_y, 4)],
        "wall_candidates": len(wall_candidates),
        "walls_accepted": len(walls),
        "regions": len(region_data),
        "door_candidates": len(door_candidates),
        "doors_accepted": len(doors),
        "ocr": ocr_diagnostics,
    }

    # 8. Debug images (working coordinates plus source-resolution overlay)
    if cfg.debug:
        _save_debug_images(
            img,
            walls_bin,
            closed_walls,
            rooms,
            corridors,
            doors,
            walls,
            out_dir,
            wall_candidates=wall_candidates,
            door_candidates=door_candidates,
            region_data=region_data,
            source_img=source_img,
            scale_x=1.0 / max(scale_x, 1e-9),
            scale_y=1.0 / max(scale_y, 1e-9),
        )

    # 9. Build FloorPlan model
    floorplan = FloorPlan(
        image_path=str(image_path),
        image_width=working_width,
        image_height=working_height,
        source_width=source_width,
        source_height=source_height,
        processing_scale_x=round(scale_x, 4),
        processing_scale_y=round(scale_y, 4),
        rooms=rooms,
        doors=doors,
        corridors=corridors,
        walls=walls,
        connections=connections,
        diagnostics=diagnostics,
    )

    # Save structured JSON into the same output directory as the debug images
    save_floorplan_json(floorplan, out_dir / "floorplan.json")

    # Console report
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
