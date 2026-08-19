import json
from datetime import datetime, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Job


def get_job(job_id: str) -> Job | None:
    with SessionLocal() as db:
        return db.scalar(select(Job).where(Job.id == job_id))


def update_job(job_id: str, **values) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if not job:
            return
        for key, value in values.items():
            setattr(job, key, value)
        db.commit()


def mark_started(job_id: str, backend: str) -> None:
    update_job(
        job_id,
        status='processing',
        progress=0.0,
        detector_backend=backend,
        error=None,
        started_at=datetime.now(timezone.utc),
    )


def mark_finished(job_id: str, output_path: str, count: int, anomalies: list[dict], processing_fps: float) -> None:
    update_job(
        job_id,
        status='completed',
        progress=100.0,
        output_path=output_path,
        bag_count=count,
        anomaly_count=len(anomalies),
        anomalies_json=json.dumps(anomalies, ensure_ascii=False),
        processing_fps=processing_fps,
        finished_at=datetime.now(timezone.utc),
    )
