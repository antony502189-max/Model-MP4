from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = 'jobs'

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255))
    input_path: Mapped[str] = mapped_column(Text)
    output_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default='uploaded', index=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    bag_count: Mapped[int] = mapped_column(Integer, default=0)
    anomaly_count: Mapped[int] = mapped_column(Integer, default=0)
    anomalies_json: Mapped[str] = mapped_column(Text, default='[]')
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    detector_backend: Mapped[str | None] = mapped_column(String(32), nullable=True)
    processing_fps: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
