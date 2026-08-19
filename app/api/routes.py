import json
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Job
from app.schemas import AnomalyResponse, JobResponse
from app.services.storage import safe_video_path, save_upload
from worker.tasks import process_video_task

router = APIRouter(prefix='/api')


@router.post('/videos', response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(file: UploadFile = File(...)):
    try:
        job_id, destination = safe_video_path(file.filename or 'video.mp4')
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await save_upload(file, destination)
    job = Job(id=job_id, original_name=file.filename or destination.name, input_path=str(destination), status='uploaded')
    with SessionLocal() as db:
        db.add(job)
        db.commit()
        db.refresh(job)
    return job


@router.post('/jobs/{job_id}/start', response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def start_job(job_id: str):
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail='Job not found')
        if job.status not in {'uploaded', 'failed'}:
            raise HTTPException(status_code=409, detail=f'Job cannot be started from status {job.status}')
        job.status = 'queued'
        job.progress = 0.0
        job.error = None
        db.commit()
        db.refresh(job)
    process_video_task.delay(job_id)
    return job


@router.get('/jobs/{job_id}', response_model=JobResponse)
def job_status(job_id: str):
    with SessionLocal() as db:
        job = db.scalar(select(Job).where(Job.id == job_id))
        if not job:
            raise HTTPException(status_code=404, detail='Job not found')
        return job


@router.get('/jobs/{job_id}/anomalies', response_model=list[AnomalyResponse])
def job_anomalies(job_id: str):
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail='Job not found')
        return json.loads(job.anomalies_json or '[]')


@router.get('/jobs/{job_id}/result')
def job_result(job_id: str):
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail='Job not found')
        if job.status != 'completed' or not job.output_path:
            raise HTTPException(status_code=409, detail='Result is not ready')
        result = Path(job.output_path)
        if not result.exists():
            raise HTTPException(status_code=410, detail='Result file is missing')
        return FileResponse(result, media_type='video/mp4', filename=f'processed_{Path(job.original_name).stem}.mp4')


@router.get('/health')
def health():
    return {'status': 'ok'}
