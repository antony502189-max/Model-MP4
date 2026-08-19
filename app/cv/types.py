from dataclasses import dataclass, field


@dataclass(slots=True)
class Detection:
    bbox: tuple[float, float, float, float]
    score: float
    label: int = 0

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return (x1 + x2) / 2.0, (y1 + y2) / 2.0


@dataclass(slots=True)
class Track:
    id: int
    bbox: tuple[float, float, float, float]
    score: float
    hits: int = 1
    missed: int = 0
    counted: bool = False
    centers: list[tuple[float, float]] = field(default_factory=list)
    last_frame: int = 0

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return (x1 + x2) / 2.0, (y1 + y2) / 2.0
