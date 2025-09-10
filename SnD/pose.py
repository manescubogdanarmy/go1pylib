from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Tuple

@dataclass
class Pose:
    x: float = 0.0
    y: float = 0.0
    heading_rad: float = 0.0  # 0 = +Y forward convention

    def copy(self) -> 'Pose':
        return Pose(self.x, self.y, self.heading_rad)

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.heading_rad)

TURN_RIGHT = -1
TURN_LEFT = 1

# Simple dead-reckoning updates

def apply_forward(pose: Pose, distance_m: float) -> None:
    # Heading 0 means +Y
    pose.x += math.sin(pose.heading_rad) * distance_m
    pose.y += math.cos(pose.heading_rad) * distance_m


def apply_turn(pose: Pose, radians: float) -> None:
    pose.heading_rad = (pose.heading_rad + radians) % (2*math.pi)
