from pathlib import Path
from uuid import uuid4

import cv2
from fastapi import UploadFile

from app.config import settings


ALLOWED_SUFFIXES = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}


def safe_video_path(filename: str) -> tuple[str, Path]:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError(f'Unsupported video extension: {suffix or "<none>"}')
    file_id = str(uuid4())
    return file_id, settings.uploads_dir / f'{file_id}{suffix}'


async def save_upload(upload: UploadFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('wb') as dst:
        while chunk := await upload.read(1024 * 1024):
            dst.write(chunk)


def validate_video(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError('Uploaded video is empty.')
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened() or capture.get(cv2.CAP_PROP_FRAME_WIDTH) <= 0 or capture.get(cv2.CAP_PROP_FRAME_HEIGHT) <= 0:
            raise ValueError('Uploaded file is not a readable video.')
    finally:
        capture.release()
