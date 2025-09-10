from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Iterable
import math

@dataclass
class Lane:
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    index: int

    @property
    def length(self) -> float:
        return math.dist((self.start_x, self.start_y), (self.end_x, self.end_y))


def generate_lanes(width_m: float, height_m: float, lane_width_m: float) -> List[Lane]:
    lanes: List[Lane] = []
    x = 0.0
    direction = 1  # +1 forward along +y, -1 reverse
    index = 0
    while x < width_m - 1e-6:
        if direction == 1:
            lanes.append(Lane(x, 0.0, x, height_m, index))
        else:
            lanes.append(Lane(x, height_m, x, 0.0, index))
        x += lane_width_m
        direction *= -1
        index += 1
    return lanes


def estimate_search_path_length(lanes: Iterable[Lane], turn_penalty_m: float = 0.5) -> float:
    lanes_list = list(lanes)
    if not lanes_list:
        return 0.0
    total = sum(l.length for l in lanes_list)
    # Approximate small penalty for turns (excluding last)
    total += max(0, len(lanes_list)-1) * turn_penalty_m
    return total
