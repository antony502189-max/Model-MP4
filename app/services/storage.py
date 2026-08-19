from pathlib import Path
from uuid import uuid4

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
