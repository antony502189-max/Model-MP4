from __future__ import annotations

import cv2
import numpy as np

from app.cv.types import Track


def draw_overlay(
    frame: np.ndarray,
    tracks: list[Track],
    count: int,
    line_a: tuple[int, int],
    line_b: tuple[int, int],
    roi: list[tuple[int, int]],
    backend: str,
    anomalies: int,
    processing_fps: float,
) -> np.ndarray:
    out = frame.copy()
    cv2.polylines(out, [np.array(roi, np.int32)], True, (180, 180, 180), 1, cv2.LINE_AA)
    cv2.line(out, line_a, line_b, (0, 220, 255), 3, cv2.LINE_AA)

    for track in tracks:
        x1, y1, x2, y2 = map(int, track.bbox)
        color = (40, 210, 40) if not track.counted else (255, 190, 20)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
        cv2.putText(out, f'bag #{track.id} {track.score:.2f}', (x1, max(20, y1 - 7)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 1, cv2.LINE_AA)

    panel = out.copy()
    cv2.rectangle(panel, (12, 12), (250, 108), (15, 15, 15), -1)
    cv2.addWeighted(panel, 0.72, out, 0.28, 0, out)
    cv2.putText(out, f'BAGS: {count}', (26, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.83, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(out, f'anomalies: {anomalies}', (26, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220, 220, 220), 1, cv2.LINE_AA)
    cv2.putText(out, f'{backend} | {processing_fps:.1f} proc FPS', (26, 91), cv2.FONT_HERSHEY_SIMPLEX, 0.43,
                (220, 220, 220), 1, cv2.LINE_AA)
    return out
