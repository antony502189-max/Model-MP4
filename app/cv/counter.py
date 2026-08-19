from __future__ import annotations

from app.cv.types import Track


def side_of_line(point: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    px, py = point
    ax, ay = a
    bx, by = b
    return (bx - ax) * (py - ay) - (by - ay) * (px - ax)


class LineCounter:
    def __init__(self, line_a: tuple[float, float], line_b: tuple[float, float], direction: str = 'down') -> None:
        self.line_a = line_a
        self.line_b = line_b
        self.direction = direction
        self.count = 0

    def update(self, tracks: list[Track]) -> list[int]:
        newly_counted: list[int] = []
        for track in tracks:
            if track.counted or len(track.centers) < 2:
                continue
            prev = track.centers[-2]
            curr = track.centers[-1]
            prev_side = side_of_line(prev, self.line_a, self.line_b)
            curr_side = side_of_line(curr, self.line_a, self.line_b)
            crossed = prev_side <= 0 < curr_side or prev_side >= 0 > curr_side
            if not crossed:
                continue

            dy = curr[1] - prev[1]
            dx = curr[0] - prev[0]
            direction_ok = {
                'down': dy > 0,
                'up': dy < 0,
                'right': dx > 0,
                'left': dx < 0,
            }.get(self.direction, True)
            if direction_ok:
                track.counted = True
                self.count += 1
                newly_counted.append(track.id)
        return newly_counted
