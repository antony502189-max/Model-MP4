from fastapi.testclient import TestClient

from app.api import routes
from app.main import app


def test_upload_status_and_queue_lifecycle(monkeypatch):
    """The HTTP request path remains asynchronous and exposes its state."""
    enqueued: list[str] = []

    # Video decoding and model inference belong to their own tested components;
    # keep this test focused on HTTP persistence and enqueue semantics.
    monkeypatch.setattr(routes, 'validate_video', lambda _path: None)
    monkeypatch.setattr(routes.process_video_task, 'delay', lambda job_id: enqueued.append(job_id))

    with TestClient(app) as client:
        upload = client.post(
            '/api/videos',
            files={'file': ('conveyor.mp4', b'not-decoded-in-this-test', 'video/mp4')},
        )
        assert upload.status_code == 201
        created = upload.json()
        assert created['status'] == 'uploaded'

        status = client.get(f"/api/jobs/{created['id']}")
        assert status.status_code == 200
        assert status.json()['status'] == 'uploaded'

        queued = client.post(f"/api/jobs/{created['id']}/start")
        assert queued.status_code == 202
        assert queued.json()['status'] == 'queued'
        assert enqueued == [created['id']]
