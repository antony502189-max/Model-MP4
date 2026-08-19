from datetime import datetime
from pydantic import BaseModel


class JobResponse(BaseModel):
    id: str
    original_name: str
    status: str
    progress: float
    bag_count: int
    anomaly_count: int
    detector_backend: str | None = None
    processing_fps: float | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {'from_attributes': True}


class AnomalyResponse(BaseModel):
    timestamp: float
    frame: int
    type: str
    severity: str
    track_id: int | None = None
    description: str
