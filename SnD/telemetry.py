from __future__ import annotations
import csv
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Any

@dataclass
class TelemetryLogger:
    path: Path
    fieldnames: Iterable[str]
    _file: Any = field(init=False, default=None)
    _writer: Any = field(init=False, default=None)
    _started: bool = field(init=False, default=False)

    def start(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open('w', newline='', encoding='utf-8')
        self._writer = csv.DictWriter(self._file, fieldnames=list(self.fieldnames))
        self._writer.writeheader()
        self._started = True

    def log(self, **row):
        if not self._started:
            self.start()
        row.setdefault('ts', time.time())
        self._writer.writerow(row)

    def close(self):
        if self._file:
            self._file.close()
            self._file = None
            self._writer = None
