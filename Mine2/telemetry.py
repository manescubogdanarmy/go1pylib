from __future__ import annotations
import csv
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Any
import datetime

@dataclass
class Telemetry:
    path: Path
    fieldnames: List[str]
    _fh: Any = field(init=False, default=None)
    _writer: Any = field(init=False, default=None)

    def __post_init__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open('w', newline='', encoding='utf-8')
        self._writer = csv.DictWriter(self._fh, fieldnames=self.fieldnames)
        self._writer.writeheader()

    def log(self, **row: Any):
        row.setdefault('ts', datetime.datetime.utcnow().isoformat())
        self._writer.writerow(row)
        self._fh.flush()

    def close(self):  # pragma: no cover
        try:
            self._fh.close()
        except Exception:
            pass
