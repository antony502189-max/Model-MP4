from __future__ import annotations

from app.cv.types import Track


def side_of_line(point: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    px, py = point
    ax, ay = a
    bx, by = b
    return (bx - ax) * (py - ay) - (by - ay) * (px - ax)


class LineCounter:
    def __init__(
        self,
        line_a: tuple[float, float],
        line_b: tuple[float, float],
        direction: str = 'down',
        min_motion: float = 1.0,
    ) -> None:
        self.line_a = line_a
        self.line_b = line_b
        self.direction = direction
        self.min_motion = min_motion
        self.count = 0

    def _crosses_segment(self, previous: tuple[float, float], current: tuple[float, float]) -> bool:
        previous_side = side_of_line(previous, self.line_a, self.line_b)
        current_side = side_of_line(current, self.line_a, self.line_b)
        if previous_side == current_side or (previous_side > 0) == (current_side > 0):
            return False

        # Ensure the trajectory crosses the configured *finite* line, not its
        # mathematical extension outside the conveyor ROI.
        denominator = previous_side - current_side
        if denominator == 0:
            return False
        t = previous_side / denominator
        crossing_x = previous[0] + t * (current[0] - previous[0])
        crossing_y = previous[1] + t * (current[1] - previous[1])
        ax, ay = self.line_a
        bx, by = self.line_b
        line_length_sq = (bx - ax) ** 2 + (by - ay) ** 2
        if line_length_sq == 0:
            return False
        projection = ((crossing_x - ax) * (bx - ax) + (crossing_y - ay) * (by - ay)) / line_length_sq
        return 0.0 <= projection <= 1.0

    def update(self, tracks: list[Track]) -> list[int]:
        newly_counted: list[int] = []
        for track in tracks:
            if track.counted or len(track.centers) < 2:
                continue
            prev = track.centers[-2]
            curr = track.centers[-1]
            if not self._crosses_segment(prev, curr):
                continue

            dy = curr[1] - prev[1]
            dx = curr[0] - prev[0]
            direction_ok = {
                'down': dy >= self.min_motion,
                'up': dy <= -self.min_motion,
                'right': dx >= self.min_motion,
                'left': dx <= -self.min_motion,
            }.get(self.direction, True)
            if direction_ok:
                track.counted = True
                self.count += 1
                newly_counted.append(track.id)
        return newly_counted
