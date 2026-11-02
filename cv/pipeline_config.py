"""Central, configurable parameters for the floor-plan CV pipeline.

The defaults are expressed as ratios of the working image size wherever
possible so the same configuration applies to small apartment drawings and
large mall plans. Callers can pass a different ``CVConfig`` instance to
``parse_floorplan`` without editing thresholds inside the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Dict

from utils.config import DEFAULT_MAX_DIMENSION


@dataclass(frozen=True)
class CVConfig:
    max_dimension: int = DEFAULT_MAX_DIMENSION

    color_saturation_ratio: float = 0.015
    achromatic_delta: int = 28
    wall_value_max: int = 175
    very_dark_value: int = 70
    adaptive_block_ratio: float = 0.045
    adaptive_c: float = 8.0
    min_structure_dim_ratio: float = 0.03
    min_structure_area_ratio: float = 0.00005
    micro_close_ratio: float = 0.0035
    window_border_ratio: float = 0.08
    door_symbol_bgr: tuple = (176, 130, 173)
    door_symbol_tolerance: int = 30
    door_symbol_min_area_ratio: float = 0.0002
    door_symbol_max_aspect_ratio: float = 5.0
    door_symbol_min_side_ratio: float = 0.006

    segmentation_gap_ratio: float = 0.09
    adaptive_segmentation: bool = True
    segmentation_gap_candidates: tuple = (0.03, 0.04, 0.05, 0.06, 0.075, 0.09)
    text_artifact_min_side_ratio: float = 0.006
    text_artifact_max_side_ratio: float = 0.08
    text_artifact_min_fill_ratio: float = 0.25
    text_artifact_max_fill_ratio: float = 0.85
    text_artifact_max_area_ratio: float = 0.0015
    text_artifact_wall_clearance_ratio: float = 0.012
    wall_min_length_ratio: float = 0.02
    hough_threshold_ratio: float = 0.035
    hough_max_gap_ratio: float = 0.0125
    merge_angle_deg: float = 7.5
    merge_distance_ratio: float = 0.012
    merge_gap_ratio: float = 0.012
    wall_support_min: float = 0.52
    wall_support_radius: int = 1

    room_min_area_ratio: float = 0.004
    room_min_dim_ratio: float = 0.022
    room_max_area_ratio: float = 0.80
    corridor_aspect_ratio: float = 4.0
    corridor_max_width_ratio: float = 0.16

    door_merge_distance_ratio: float = 0.055
    door_duplicate_pair_ratio: float = 0.14
    door_min_area_ratio: float = 0.00008
    door_max_area_ratio: float = 0.006
    door_region_gap_min_area_ratio: float = 0.00025
    door_region_gap_max_major_ratio: float = 0.12
    door_min_dim_ratio: float = 0.0075
    door_max_minor_ratio: float = 0.08
    door_probe_step_ratio: float = 0.0075
    door_probe_max_ratio: float = 0.10
    door_association_margin_ratio: float = 0.01
    door_fallback_distance_ratio: float = 0.08

    ocr_min_confidence: float = 35.0
    debug: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {field.name: getattr(self, field.name) for field in fields(self)}
