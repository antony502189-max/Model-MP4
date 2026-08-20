from celery import Celery

from app.config import settings

# Explicitly import task modules so the standalone Celery worker registers the
# task name used by the FastAPI producer.
celery_app = Celery(
    'bag_counter',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=['worker.tasks'],
)
celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    # A CPU MMDetection run of the supplied 10-minute video can exceed Redis'
    # one-hour default visibility timeout.  Without this, Redis redelivers a
    # still-running task and the worker renders the entire video a second time.
    broker_transport_options={'visibility_timeout': 43200},
    result_backend_transport_options={'visibility_timeout': 43200},
    worker_prefetch_multiplier=1,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
)
