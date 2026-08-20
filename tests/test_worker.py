from worker.celery_app import celery_app


def test_standalone_worker_registers_processing_task():
    """`celery -A worker.celery_app.celery_app worker` must discover the task."""
    celery_app.loader.import_default_modules()
    assert 'process_video' in celery_app.tasks


def test_worker_visibility_timeout_exceeds_a_full_cpu_video_run():
    assert celery_app.conf.broker_transport_options['visibility_timeout'] >= 12 * 60 * 60
