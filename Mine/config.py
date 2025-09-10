from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml
from typing import Any, Dict

CONFIG_PATH_DEFAULT = Path(__file__).with_name("mine_config.yaml")

@dataclass
class MineVisionConfig:
    enabled: bool
    camera_index: int
    blur_kernel: int
    canny_low: int
    canny_high: int
    dp: float
    min_dist: int
    param1: int
    param2: int
    min_radius: int
    max_radius: int
    save_dir: str

@dataclass
class MineSearchAreaConfig:
    width_m: float
    height_m: float
    lane_width_m: float

@dataclass
class MineMovementConfig:
    walk_speed_fraction: float
    forward_pulse_m: float
    turn_90_ms: int
    max_search_speed_mps: float

@dataclass
class MineLoggingConfig:
    level: str
    telemetry: bool
    telemetry_dir: str

@dataclass
class MineSimulationConfig:
    enabled: bool

@dataclass
class MineConfig:
    vision: MineVisionConfig
    logging: MineLoggingConfig
    simulation: MineSimulationConfig
    area: MineSearchAreaConfig
    movement: MineMovementConfig

    @staticmethod
    def load(path: Path | None = None) -> "MineConfig":
        p = path or CONFIG_PATH_DEFAULT
        with open(p, 'r', encoding='utf-8') as f:
            raw: Dict[str, Any] = yaml.safe_load(f)
        return MineConfig(
            vision=MineVisionConfig(**raw['vision']),
            logging=MineLoggingConfig(**raw['logging']),
            simulation=MineSimulationConfig(**raw['simulation']),
            area=MineSearchAreaConfig(**raw['area']),
            movement=MineMovementConfig(**raw['movement'])
        )
