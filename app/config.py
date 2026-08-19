from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Conveyor Bag Counter'
    data_dir: Path = Path('/data')
    database_url: str = 'sqlite:////data/app.db'
    redis_url: str = 'redis://redis:6379/0'

    detector_backend: str = 'mmdet'  # mmdet | contrast
    mmdet_config: str = '/app/mmdet_configs/rtmdet_tiny_bag.py'
    mmdet_checkpoint: str = '/models/rtmdet_bag.pth'
    device: str = 'cpu'
    confidence_threshold: float = 0.35

    # Counting line in normalized image coordinates.
    line_x1: float = 0.295
    line_y1: float = 0.517
    line_x2: float = 0.472
    line_y2: float = 0.517
    count_direction: str = 'down'

    tracker_iou_threshold: float = 0.20
    tracker_max_age: int = 18
    tracker_min_hits: int = 2

    # The supplied camera is fixed. ROI covers only the conveyor belt.
    roi_points: str = '0.489,0.147;0.583,0.147;0.328,0.997;0.042,0.997'

    @property
    def uploads_dir(self) -> Path:
        path = self.data_dir / 'uploads'
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def results_dir(self) -> Path:
        path = self.data_dir / 'results'
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def parsed_roi(self) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for pair in self.roi_points.split(';'):
            x, y = pair.split(',')
            points.append((float(x), float(y)))
        return points


settings = Settings()
