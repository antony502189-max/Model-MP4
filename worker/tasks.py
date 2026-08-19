from pathlib import Path

from worker.celery_app import celery_app
from app.config import settings
from app.cv.pipeline import process_video
from app.services.jobs import get_job, mark_finished, mark_started, update_job


@celery_app.task(name='process_video', bind=True)
def process_video_task(self, job_id: str):
    job = get_job(job_id)
    if not job:
        raise RuntimeError(f'Job not found: {job_id}')

    mark_started(job_id, settings.detector_backend)
    output_path = settings.results_dir / f'{job_id}.mp4'

    def report(progress: float, count: int, anomalies: list[dict], proc_fps: float) -> None:
        import json
        update_job(
            job_id,
            progress=progress,
            bag_count=count,
            anomaly_count=len(anomalies),
            anomalies_json=json.dumps(anomalies, ensure_ascii=False),
            processing_fps=proc_fps,
        )
        self.update_state(state='PROGRESS', meta={'progress': progress, 'count': count})

    try:
        result = process_video(job.input_path, str(output_path), report)
        mark_finished(job_id, str(output_path), result['count'], result['anomalies'], result['processing_fps'])
        return result
    except Exception as exc:
        update_job(job_id, status='failed', error=str(exc))
        raise
