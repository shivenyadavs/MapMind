import pathlib
import pytest
import numpy as np

from cv.preprocessing import generate_synthetic_floorplan, generate_second_floorplan
from cv.floorplan_parser import parse_floorplan
from cv.models import FloorPlan, Room, Door, Corridor, Wall


@pytest.fixture(scope="module")
def sample_floorplan_path():
    return generate_synthetic_floorplan()


@pytest.fixture(scope="module")
def second_floorplan_path():
    return generate_second_floorplan()


def test_parse_floorplan_counts(sample_floorplan_path):
    fp = parse_floorplan(sample_floorplan_path)

    assert isinstance(fp, FloorPlan)
    assert len(fp.rooms) >= 5, f"Expected at least 5 rooms, got {len(fp.rooms)}"
    assert len(fp.doors) >= 5, f"Expected at least 5 doors, got {len(fp.doors)}"
    assert len(fp.corridors) >= 1, f"Expected at least 1 corridor, got {len(fp.corridors)}"
    assert len(fp.walls) > 0, f"Expected detected walls, got {len(fp.walls)}"


def test_rooms_validity(sample_floorplan_path):
    fp = parse_floorplan(sample_floorplan_path)
    total_image_area = fp.image_width * fp.image_height

    for room in fp.rooms:
        assert isinstance(room, Room)
        assert room.area > 0, f"Room {room.name} has non-positive area"
        assert room.area < total_image_area * 0.9, f"Room {room.name} occupies whole image/background"
        
        # Valid bounding box
        bbox = room.bounding_box
        assert bbox.width > 0 and bbox.height > 0
        assert 0 <= bbox.x < fp.image_width
        assert 0 <= bbox.y < fp.image_height
        assert bbox.x2 <= fp.image_width
        assert bbox.y2 <= fp.image_height

        # Valid center inside bounding box
        cx, cy = room.center
        assert bbox.x <= cx <= bbox.x2
        assert bbox.y <= cy <= bbox.y2


def test_doors_validity(sample_floorplan_path):
    fp = parse_floorplan(sample_floorplan_path)

    for door in fp.doors:
        assert isinstance(door, Door)
        cx, cy = door.center
        assert 0 <= cx <= fp.image_width
        assert 0 <= cy <= fp.image_height
        assert door.orientation in {"horizontal", "vertical"}
        assert door.bounding_box.width > 0
        assert door.bounding_box.height > 0


def test_corridors_validity(sample_floorplan_path):
    fp = parse_floorplan(sample_floorplan_path)

    for cor in fp.corridors:
        assert isinstance(cor, Corridor)
        assert cor.area > 0
        bbox = cor.bounding_box
        assert bbox.width > 0 and bbox.height > 0
        # Aspect ratio should be elongated
        aspect = max(bbox.width / bbox.height, bbox.height / bbox.width)
        assert aspect >= 3.0


def test_second_floorplan_generalization(second_floorplan_path):
    """Test on a second distinct architectural floor plan to verify generalizability."""
    fp = parse_floorplan(second_floorplan_path)

    assert len(fp.rooms) >= 4
    assert len(fp.doors) >= 4
    assert len(fp.corridors) >= 1
    assert len(fp.walls) > 0

    for room in fp.rooms:
        assert room.area > 0
    for door in fp.doors:
        assert 0 <= door.center[0] <= fp.image_width
