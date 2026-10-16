from __future__ import annotations

from typing import List, Tuple, Optional
from pydantic import BaseModel, Field, ConfigDict


class BoundingBox(BaseModel):
    x: int = Field(..., description="Top‑left x coordinate")
    y: int = Field(..., description="Top‑left y coordinate")
    width: int = Field(..., description="Width of the box")
    height: int = Field(..., description="Height of the box")

    @property
    def x2(self) -> int:
        return self.x + self.width

    @property
    def y2(self) -> int:
        return self.y + self.height

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def area(self) -> int:
        return self.width * self.height


class Room(BaseModel):
    id: int
    name: str
    bounding_box: BoundingBox
    center: Tuple[int, int]
    width: int
    height: int
    area: int


class Door(BaseModel):
    id: int
    name: str
    bounding_box: BoundingBox
    center: Tuple[int, int]
    orientation: Optional[str] = None  # "horizontal" or "vertical"
    associated_rooms: List[int] = Field(default_factory=list)
    connected_regions: List[str] = Field(default_factory=list)


class Wall(BaseModel):
    id: int
    start: Tuple[int, int]
    end: Tuple[int, int]
    length: float
    orientation: str  # "horizontal" or "vertical"


class Corridor(BaseModel):
    id: int
    name: str
    bounding_box: BoundingBox
    center: Tuple[int, int]
    area: int


class Connection(BaseModel):
    source: str
    destination: str
    via_door: str
    distance: float


class Route(BaseModel):
    source: str
    destination: str
    path: List[str]
    doors: List[str]
    total_distance: float
    edge_count: int = 0


class FloorPlan(BaseModel):
    image_path: str
    image_width: int
    image_height: int
    rooms: List[Room] = Field(default_factory=list)
    doors: List[Door] = Field(default_factory=list)
    corridors: List[Corridor] = Field(default_factory=list)
    walls: List[Wall] = Field(default_factory=list)
    connections: List[Connection] = Field(default_factory=list)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )
