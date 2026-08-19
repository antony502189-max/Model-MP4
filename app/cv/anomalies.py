from __future__ import annotations

from dataclasses import dataclass, asdict

from app.cv.tracker import iou
from app.cv.types import Track


@dataclass(slots=True)
class Anomaly:
    timestamp: float
    frame: int
    type: str
    severity: str
    description: str
    track_id: int | None = None

    def as_dict(self) -> dict:
        return asdict(self)


class AnomalyMonitor:
    def __init__(self, fps: float, line_y: float) -> None:
        self.fps = max(fps, 1.0)
        self.line_y = line_y
        self.items: list[Anomaly] = []
        self._seen: set[tuple] = set()

    def _emit(self, anomaly: Anomaly, cooldown_bucket: int = 5) -> None:
        bucket = int(anomaly.timestamp // cooldown_bucket)
        key = (anomaly.type, anomaly.track_id, bucket)
        if key in self._seen:
            return
        self._seen.add(key)
        self.items.append(anomaly)

    def inspect(self, tracks: list[Track], frame_index: int, processing_fps: float | None = None) -> None:
        ts = frame_index / self.fps

        for track in tracks:
            if track.missed > 0 and abs(track.center[1] - self.line_y) < 45:
                self._emit(Anomaly(ts, frame_index, 'tracking_gap_near_line', 'medium',
                                   'Track temporarily lost near the counting line.', track.id))

            if len(track.centers) >= 8:
                dy = track.centers[-1][1] - track.centers[-8][1]
                if dy < -12:
                    self._emit(Anomaly(ts, frame_index, 'reverse_motion', 'medium',
                                       'Object moved opposite to configured conveyor direction.', track.id))
                total_move = sum(
                    ((track.centers[i][0] - track.centers[i - 1][0]) ** 2 +
                     (track.centers[i][1] - track.centers[i - 1][1]) ** 2) ** 0.5
                    for i in range(1, len(track.centers))
                )
                if len(track.centers) >= 25 and total_move < 20:
                    self._emit(Anomaly(ts, frame_index, 'possible_stall', 'high',
                                       'Object remains almost stationary for an unusual time.', track.id), cooldown_bucket=10)

        for i, first in enumerate(tracks):
            for second in tracks[i + 1:]:
                if iou(first.bbox, second.bbox) > 0.40:
                    self._emit(Anomaly(ts, frame_index, 'heavy_occlusion', 'medium',
                                       f'Tracks {first.id} and {second.id} overlap heavily.', first.id))

        if processing_fps is not None and frame_index > int(self.fps * 10) and processing_fps < 1.0:
            self._emit(Anomaly(ts, frame_index, 'slow_inference', 'low',
                               f'Processing throughput is low ({processing_fps:.2f} FPS).', None), cooldown_bucket=30)
