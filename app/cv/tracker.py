from __future__ import annotations

from app.cv.types import Detection, Track


def iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / union if union > 0 else 0.0


def shifted_bbox(bbox: tuple[float, float, float, float], dx: float, dy: float) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = bbox
    return x1 + dx, y1 + dy, x2 + dx, y2 + dy


class IoUTracker:
    """Small deterministic tracker suitable for a fixed single-camera conveyor.

    It matches detections greedily by IoU and keeps tracks alive briefly through detector misses.
    The interface is intentionally simple so it can be replaced by ByteTrack without touching
    counting/anomaly logic.
    """

    def __init__(
        self,
        iou_threshold: float = 0.2,
        max_age: int = 18,
        min_hits: int = 2,
        prediction_max_age: int = 3,
    ) -> None:
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.min_hits = min_hits
        self.prediction_max_age = prediction_max_age
        self.tracks: dict[int, Track] = {}
        self._next_id = 1

    def update(self, detections: list[Detection], frame_index: int) -> list[Track]:
        unmatched_tracks = set(self.tracks)
        unmatched_detections = set(range(len(detections)))
        candidates: list[tuple[float, int, int]] = []

        for track_id, track in self.tracks.items():
            # A small constant-velocity prediction prevents a one-frame detector gap from
            # fragmenting a moving bag into a new identity.
            elapsed = max(frame_index - track.last_frame, 1)
            predicted = shifted_bbox(track.bbox, track.velocity[0] * elapsed, track.velocity[1] * elapsed)
            for det_idx, detection in enumerate(detections):
                score = iou(predicted, detection.bbox)
                if score >= self.iou_threshold:
                    candidates.append((score, track_id, det_idx))

        for _, track_id, det_idx in sorted(candidates, reverse=True):
            if track_id not in unmatched_tracks or det_idx not in unmatched_detections:
                continue
            detection = detections[det_idx]
            track = self.tracks[track_id]
            previous_center = track.center
            frame_gap = max(frame_index - track.last_frame, 1)
            track.bbox = detection.bbox
            track.score = detection.score
            track.hits += 1
            track.missed = 0
            track.last_frame = frame_index
            current_center = track.center
            measured_velocity = (
                (current_center[0] - previous_center[0]) / frame_gap,
                (current_center[1] - previous_center[1]) / frame_gap,
            )
            track.velocity = (
                0.65 * track.velocity[0] + 0.35 * measured_velocity[0],
                0.65 * track.velocity[1] + 0.35 * measured_velocity[1],
            )
            track.centers.append(current_center)
            track.centers = track.centers[-40:]
            unmatched_tracks.remove(track_id)
            unmatched_detections.remove(det_idx)

        for track_id in list(unmatched_tracks):
            track = self.tracks[track_id]
            track.missed += 1
            # Carry an established motion estimate through a very short model
            # dropout.  This is especially important at the count line: a bag
            # should not lose its identity one frame before crossing.  The
            # bounded age avoids fabricating long, unobserved trajectories.
            if track.missed <= self.prediction_max_age and track.hits >= self.min_hits:
                track.bbox = shifted_bbox(track.bbox, *track.velocity)
                track.centers.append(track.center)
                track.centers = track.centers[-40:]
                track.last_frame = frame_index
            if track.missed > self.max_age:
                del self.tracks[track_id]

        for det_idx in unmatched_detections:
            detection = detections[det_idx]
            track = Track(
                id=self._next_id,
                bbox=detection.bbox,
                score=detection.score,
                hits=1,
                missed=0,
                centers=[detection.center],
                last_frame=frame_index,
            )
            self.tracks[track.id] = track
            self._next_id += 1

        return [track for track in self.tracks.values() if track.hits >= self.min_hits and track.missed <= self.max_age]
