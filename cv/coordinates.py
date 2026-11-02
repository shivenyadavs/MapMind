"""Coordinate conversion helpers for working-resolution detections."""

from __future__ import annotations

import math
from typing import List, Tuple

from .models import (
    BoundingBox,
    Connection,
    Corridor,
    Door,
    FloorPlan,
    Room,
    Wall,
)


Point = Tuple[int, int]


def _scale_point(point: Point, sx: float, sy: float, width: int, height: int) -> Point:
    x = int(round(point[0] * sx))
    y = int(round(point[1] * sy))
    return (min(max(x, 0), max(width - 1, 0)), min(max(y, 0), max(height - 1, 0)))


def _scale_box(box: BoundingBox, sx: float, sy: float, width: int, height: int) -> BoundingBox:
    x0 = int(round(box.x * sx))
    y0 = int(round(box.y * sy))
    x1 = int(round(box.x2 * sx))
    y1 = int(round(box.y2 * sy))
    x0 = min(max(x0, 0), max(width - 1, 0))
    y0 = min(max(y0, 0), max(height - 1, 0))
    x1 = min(max(x1, x0 + 1), width)
    y1 = min(max(y1, y0 + 1), height)
    return BoundingBox(x=x0, y=y0, width=x1 - x0, height=y1 - y0)


def _scale_box_to_source(
    box: BoundingBox,
    scale_x: float,
    scale_y: float,
    source_width: int,
    source_height: int,
) -> BoundingBox:
    return _scale_box(box, scale_x, scale_y, source_width, source_height)


def scale_floorplan_to_source(floorplan: FloorPlan) -> FloorPlan:
    """Return a copy of *floorplan* expressed in original-image coordinates.

    ``parse_floorplan`` works on a resized image for speed and stability. The
    returned FloorPlan records the original dimensions and the working scale,
    so debug overlays, the Streamlit UI, and graph visualisations can all use
    the original image without silently mixing coordinate spaces.
    """
    source_width = int(floorplan.source_width or floorplan.image_width)
    source_height = int(floorplan.source_height or floorplan.image_height)
    if source_width <= 0 or source_height <= 0:
        return floorplan.model_copy(deep=True)

    scale_x = source_width / max(floorplan.image_width, 1)
    scale_y = source_height / max(floorplan.image_height, 1)
    distance_scale = (scale_x + scale_y) / 2.0

    rooms: List[Room] = []
    for room in floorplan.rooms:
        box = _scale_box_to_source(room.bounding_box, scale_x, scale_y, source_width, source_height)
        rooms.append(Room(
            id=room.id,
            name=room.name,
            bounding_box=box,
            center=_scale_point(room.center, scale_x, scale_y, source_width, source_height),
            width=box.width,
            height=box.height,
            area=max(1, int(round(room.area * scale_x * scale_y))),
            semantic_label=room.semantic_label,
            label_confidence=room.label_confidence,
            classification_confidence=room.classification_confidence,
            label_source=room.label_source,
        ))

    corridors: List[Corridor] = []
    for corridor in floorplan.corridors:
        box = _scale_box_to_source(
            corridor.bounding_box, scale_x, scale_y, source_width, source_height
        )
        corridors.append(Corridor(
            id=corridor.id,
            name=corridor.name,
            bounding_box=box,
            center=_scale_point(corridor.center, scale_x, scale_y, source_width, source_height),
            area=max(1, int(round(corridor.area * scale_x * scale_y))),
            semantic_label=corridor.semantic_label,
            label_confidence=corridor.label_confidence,
            classification_confidence=corridor.classification_confidence,
            label_source=corridor.label_source,
        ))

    doors: List[Door] = []
    for door in floorplan.doors:
        box = _scale_box_to_source(door.bounding_box, scale_x, scale_y, source_width, source_height)
        doors.append(Door(
            id=door.id,
            name=door.name,
            bounding_box=box,
            center=_scale_point(door.center, scale_x, scale_y, source_width, source_height),
            orientation=door.orientation,
            associated_rooms=list(door.associated_rooms),
            connected_regions=list(door.connected_regions),
            confidence=door.confidence,
            detection_method=door.detection_method,
        ))

    walls: List[Wall] = []
    for wall in floorplan.walls:
        start = _scale_point(wall.start, scale_x, scale_y, source_width, source_height)
        end = _scale_point(wall.end, scale_x, scale_y, source_width, source_height)
        walls.append(Wall(
            id=wall.id,
            start=start,
            end=end,
            length=round(float(math.hypot(end[0] - start[0], end[1] - start[1])), 2),
            orientation=wall.orientation,
            confidence=wall.confidence,
        ))

    connections = [
        Connection(
            source=conn.source,
            destination=conn.destination,
            via_door=conn.via_door,
            distance=round(conn.distance * distance_scale, 1),
            confidence=conn.confidence,
            reason=conn.reason,
        )
        for conn in floorplan.connections
    ]

    return FloorPlan(
        image_path=floorplan.image_path,
        image_width=source_width,
        image_height=source_height,
        rooms=rooms,
        doors=doors,
        corridors=corridors,
        walls=walls,
        connections=connections,
        source_width=source_width,
        source_height=source_height,
        processing_scale_x=1.0,
        processing_scale_y=1.0,
        diagnostics=dict(floorplan.diagnostics),
    )
