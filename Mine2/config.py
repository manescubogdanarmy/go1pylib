from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml

@dataclass
class CamSource:
    name: str
    uri: str  # RTSP/UDP URL or device index string like "0"
    enabled: bool = True
    width: Optional[int] = None
    height: Optional[int] = None
    rotate_deg: int = 0  # optional rotation

@dataclass
class VisionParams:
    blur_kernel: int = 5
    canny_low: int = 50
    canny_high: int = 150
    dp: float = 1.2
    min_dist: int = 40
    param1: int = 120
    param2: int = 30
    min_radius: int = 10
    max_radius: int = 160

@dataclass
class DatasetPaths:
    root: str
    mine_dir: str
    not_mine_dir: str
    unsorted_dir: str

@dataclass
class Mine2Config:
    cameras: List[CamSource]
    vision: VisionParams
    dataset: DatasetPaths
    logging_level: str = "INFO"

    @staticmethod
    def load(path: Path) -> "Mine2Config":
        raw: Dict[str, Any] = yaml.safe_load(path.read_text(encoding='utf-8'))
        cams = [CamSource(**c) for c in raw.get('cameras', [])]
        vis = VisionParams(**raw.get('vision', {}))
        ds = DatasetPaths(**raw.get('dataset', {
            'root': 'Mine2/dataset',
            'mine_dir': 'Mine2/dataset/mine',
            'not_mine_dir': 'Mine2/dataset/not_mine',
            'unsorted_dir': 'Mine2/dataset/unsorted'
        }))
        return Mine2Config(cameras=cams, vision=vis, dataset=ds, logging_level=raw.get('logging_level', 'INFO'))
