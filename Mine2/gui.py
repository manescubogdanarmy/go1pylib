from __future__ import annotations
import math
from typing import Dict, List, Tuple

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None
    np = None

KEY_HELP = "Keys: q=quit  [ and ] = page  s=save-full"

class MultiFeedGUI:
    def __init__(self, window_name: str = "Mine2"):
        self.window_name = window_name

    def draw(self, frames: Dict[str, any], detections: Dict[str, List[Tuple[int,int,int]]], page: int = 0) -> int:
        """Render up to 4 feeds on current page. Return last key pressed (or -1)."""
        if cv2 is None or np is None:
            return -1
        names = sorted(frames.keys())
        per_page = 4
        start = page * per_page
        selected = names[start:start+per_page]
        # Normalize sizes and tile
        tiles = []
        for name in selected:
            frame = frames.get(name)
            if frame is None:
                h, w = 360, 640
                tile = np.zeros((h, w, 3), dtype=np.uint8)
                cv2.putText(tile, f"{name}: (no frame)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
            else:
                tile = frame.copy()
            # overlay detections
            for (x,y,r) in detections.get(name, []):
                cv2.circle(tile, (x,y), r, (0,255,0), 2)
                cv2.putText(tile, "MINE?", (x+5,y+5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
            cv2.putText(tile, KEY_HELP, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            cv2.putText(tile, name, (10, tile.shape[0]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
            tiles.append(tile)

        # build grid 2x2
        def pad(tile, target_size=(360, 640)):
            return cv2.resize(tile, target_size)
        while len(tiles) < 4:
            tiles.append(np.zeros((360,640,3), dtype=np.uint8))
        tiles = [pad(t) for t in tiles]
        top = np.hstack(tiles[0:2])
        bottom = np.hstack(tiles[2:4])
        grid = np.vstack([top, bottom])
        cv2.imshow(self.window_name, grid)
        key = cv2.waitKey(1) & 0xFF
        return key

    def close(self):  # pragma: no cover
        if cv2 is None:
            return
        cv2.destroyAllWindows()
