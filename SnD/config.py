from __future__ import annotations
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

CONFIG_PATH_DEFAULT = Path(__file__).with_name("search_config.yaml")

@dataclass
class AreaConfig:
    width_m: float
    height_m: float
    lane_width_m: float

@dataclass
class MovementConfig:
    walk_speed_fraction: float
    max_search_speed_mps: float
    forward_pulse_m: float
    turn_90_ms: int

@dataclass
class VisionConfig:
    enabled: bool
    model: str
    conf_threshold: float
    debounce_frames: int
    min_positive_frames: int
    camera_index: int

@dataclass
class ApproachConfig:
    center_threshold_pct: float
    forward_pulse_ms: int
    stop_distance_m: float

@dataclass
class TimeoutsConfig:
    lost_target_s: float

@dataclass
class InteractionConfig:
    wait_s: float

@dataclass
class ReturnConfig:
    strategy: str  # reverse_log | waypoints (future)

@dataclass
class SafetyConfig:
    min_battery_start_pct: int
    min_battery_runtime_pct: int
    enable_collision_adapter: bool

@dataclass
class LoggingConfig:
    level: str
    telemetry: bool
    telemetry_dir: str

@dataclass
class SimulationConfig:
    enabled: bool

@dataclass
class SearchConfig:
    area: AreaConfig
    movement: MovementConfig
    vision: VisionConfig
    approach: ApproachConfig
    timeouts: TimeoutsConfig
    interaction: InteractionConfig
    return_: ReturnConfig
    safety: SafetyConfig
    logging: LoggingConfig
    simulation: SimulationConfig

    @staticmethod
    def load(path: Path | None = None) -> "SearchConfig":
        p = path or CONFIG_PATH_DEFAULT
        with open(p, 'r', encoding='utf-8') as f:
            raw: Dict[str, Any] = yaml.safe_load(f)
        return SearchConfig(
            area=AreaConfig(**raw['area']),
            movement=MovementConfig(**raw['movement']),
            vision=VisionConfig(**raw['vision']),
            approach=ApproachConfig(**raw['approach']),
            timeouts=TimeoutsConfig(**raw['timeouts']),
            interaction=InteractionConfig(**raw['interaction']),
            return_=ReturnConfig(**raw['return']),
            safety=SafetyConfig(**raw['safety']),
            logging=LoggingConfig(**raw['logging']),
            simulation=SimulationConfig(**raw['simulation']),
        )
