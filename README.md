# Conveyor Bag Counter

Web application for asynchronous counting of bags on a fixed conveyor camera. The production detector is a **one-class RTMDet model executed through MMDetection**. The rest of the pipeline adds tracking, directional line crossing, anomaly monitoring, persistence and a small web UI.

## What is implemented

- MMDetection 3.x / RTMDet-tiny inference (`bag` class).
- Stable object IDs across frames using a deterministic IoU tracker with bounded constant-velocity bridging through very short detector gaps.
- Post-ROI one-class NMS suppresses nested RTMDet boxes before tracking, preventing duplicate tracks and false occlusion alerts.
- One-time directional line crossing; an already counted track cannot increment the counter twice.
- FastAPI upload/status/anomalies/result API.
- Celery + Redis background processing, so HTTP requests never wait for full-video inference.
- SQLite job persistence plus host-mounted `data/`, `models/` and Redis volume.
- Annotated result video with track IDs, counter, anomaly count and processing throughput.
- Anomaly monitoring for tracking gaps near the line, reverse motion, heavy occlusion, possible stalls and very slow inference.
- Docker Compose for API, worker, Redis and an optional training container.
- Bootstrap dataset generator for the supplied fixed camera.

## Architecture

```text
Browser
  |
  v
FastAPI ---- SQLite (/data/app.db)
  |
  | enqueue job
  v
Redis <---- Celery worker
               |
               v
        MMDetection RTMDet
               |
        IoU tracking + line crossing
               |
        anomaly monitor + overlay
               |
               v
        /data/results/<job>.mp4
```

The API and worker share the same host-mounted `./data` directory. Recreating containers therefore does not delete uploads/results. Redis also uses a named persistent volume.

## Why the counting logic is robust

A raw per-frame detection count would count the same bag many times. This project tracks every detection and gives it a persistent `track_id`. The counter only fires when a track centroid changes side of the configured line in the expected conveyor direction. The `Track.counted` flag then permanently prevents a second increment for that track.

For a production system, ByteTrack can replace `IoUTracker` behind the same interface. For this fixed camera, measured short-clip validation showed that post-ROI NMS plus bounded motion bridging maintain the needed line-crossing identities without adding an opaque dependency.

## Model preparation

The supplied bags are not a native COCO class, so submitting an untouched COCO detector would be weak. Fine-tune RTMDet-tiny for one class (`bag`).

### 1. Create bootstrap annotations from `input.mp4`

Put the test video in the repository root as `input.mp4` and run:

```bash
python scripts/bootstrap_dataset.py input.mp4 --out dataset --samples 600
```

This produces COCO JSON and sampled frames. The generator is intentionally camera-specific and uses belt geometry + appearance only to create **pseudo-labels**. Review/correct the boxes in CVAT or Label Studio before the final training run. Even a relatively small corrected set is enough because the camera, belt and object class are fixed.

### 2. Train RTMDet through MMDetection

```bash
cp .env.example .env
docker compose --profile train run --build --rm trainer
```

The training service allocates 1 GB of shared memory for PyTorch data-loader
workers and persists downloaded Torch checkpoints in a named Docker volume. On
CPU-only hardware this 60-epoch RTMDet run is expected to take hours; training
can be resumed from a saved checkpoint with `TRAIN_RESUME=/work_dirs/rtmdet_bag/epoch_N.pth`.

The training config is `mmdet_configs/rtmdet_tiny_bag.py`. It inherits the official RTMDet-tiny configuration, changes `bbox_head.num_classes` to one, uses COCO-format custom data and transfers the official COCO pretrained weights. Its warm-up and cosine-decay schedule are scaled for this 60-epoch, 40-batch-per-epoch dataset rather than retaining the upstream 300-epoch timings.

After training, the trainer copies the checkpoint with the best held-out
`bbox_mAP` (falling back to the newest checkpoint if no validation metric is
available) to:

```text
models/rtmdet_bag.pth
```

That is exactly the path consumed by the worker.

## Run

```bash
docker compose up --build
```

Open `http://localhost:8001`. Set `API_PORT=8000` in `.env` if that port is free.

Workflow:

1. Select `input.mp4`.
2. Click **Upload & create job**.
3. Click **Start processing**.
4. The UI polls job state while Celery performs inference independently of the HTTP request.
5. When the job reaches `completed`, click **Download result**.

To reopen a persisted job after a page reload, use `http://localhost:8001/?job=<job-id>`.

## API

### Upload

```http
POST /api/videos
Content-Type: multipart/form-data
```

Returns a job in `uploaded` state.

### Start asynchronous processing

```http
POST /api/jobs/{job_id}/start
```

Returns immediately with HTTP 202 and a queued job.

### Poll state

```http
GET /api/jobs/{job_id}
```

### Anomalies

```http
GET /api/jobs/{job_id}/anomalies
```

Each anomaly has timestamp, frame number, type, severity, optional track ID and a human-readable explanation.

### Result

```http
GET /api/jobs/{job_id}/result
```

## Camera configuration

The checked-in `.env.example` contains normalized ROI and counting-line defaults matching the supplied 640x360 test video. Coordinates are normalized, so the same geometry scales with resolution.

For another camera, change `ROI_POINTS` and the line coordinates instead of hard-coding pixel values into the CV code.

## Independent sanity check for the supplied video

The script below does **not** replace MMDetection. It measures brightness events at a fixed belt cross-section and is useful as an independent reference when validating the trained detector:

```bash
python scripts/estimate_reference_count.py input.mp4
```

On the supplied video, the expected reference is **130 bag passages**. A materially different MMDetection result is a reason to inspect missed detections, duplicate tracks or line placement.

## Final production validation

The committed production checkpoint is `models/rtmdet_bag.pth`. It loaded through MMDetection as a one-class `RTMDet` model. Its 60-epoch validation metrics were bbox mAP **0.785**, bbox mAP@0.50 **0.981**, bbox mAP@0.75 **0.922**, and AR@100 **0.840**.

The final full `input.mp4` job used `DETECTOR_BACKEND=mmdet`, not the bootstrap detector. It produced **127** directional passages against the independent reference of approximately **130** (difference: **-3**, -2.3%). The 14,999-frame annotated result is persisted at `data/results/04220166-ec7e-4769-8732-8d3a18ce3377.mp4` and can be downloaded from the job result endpoint.

Before the full run, real-MMDetection short clips validated the calibrated pipeline against the independent signal: 20–32 s = 4/4, 180–192 s = 1/1, and 540–554 s = 5/5. The final anomaly report contains 34 auditable events: 18 `possible_stall`, 6 `reverse_motion`, 5 `heavy_occlusion`, and 5 `tracking_gap_near_line`. Anomalies never alter the count.

## Anomaly design

The assignment leaves anomaly semantics open. Here an anomaly means a condition that can reduce confidence in counting:

- `tracking_gap_near_line`: a track temporarily disappears close to the count line, creating duplicate-count risk;
- `reverse_motion`: centroid movement contradicts conveyor direction;
- `heavy_occlusion`: two tracked boxes overlap strongly;
- `possible_stall`: a tracked object barely moves for an unusually long interval;
- `slow_inference`: worker throughput becomes extremely low.

Anomalies are persisted with the job and exposed via API. They do not silently modify the bag count.

## Tests

```bash
pytest -q
```

The suite covers the API/worker lifecycle, post-ROI NMS, direction-aware anomalies, short-gap tracker bridging and the key invariant: one directional crossing increments exactly once.

## Technical decisions

**RTMDet-tiny.** It is a compact real-time detector in MMDetection and is appropriate for a single-class fixed-camera task. A larger model can improve recall but increases inference cost without necessarily improving the engineering design.

**Separate worker.** Video inference is CPU/GPU-heavy and can take minutes. Celery keeps request latency independent from inference duration and makes retries/worker scaling straightforward.

**SQLite for metadata.** The test has a single worker and modest write volume. SQLite keeps the demo self-contained; PostgreSQL would be the natural replacement for multiple concurrent workers.

**Host-mounted video storage.** Uploads and rendered results are deliberately outside the container filesystem to satisfy persistence requirements after container recreation.

## Submission checklist

- [x] Train and validate `models/rtmdet_bag.pth` through MMDetection.
- [x] Run the test suite.
- [x] Build and start FastAPI, Celery worker and Redis with Docker Compose.
- [x] Process the provided `input.mp4` with real MMDetection.
- [x] Compare the final count (127) against the independent 130-event reference.
- [x] Download and visually inspect the final processed video.
- [ ] Record the screen showing Docker build/start, upload, progress/status and result download.
- [ ] Push this repository publicly or send it as an archive together with the processed video and screen recording.

## Defense notes

A compact explanation of the architectural choices and likely interview questions is included in [`docs/TECHNICAL_DEFENSE.md`](docs/TECHNICAL_DEFENSE.md). Curl examples are in [`docs/API_EXAMPLES.md`](docs/API_EXAMPLES.md).
