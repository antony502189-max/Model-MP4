<div align="center">

# Conveyor Bag Counter

### Production-grade conveyor-video analytics with MMDetection / RTMDet

[![MMDetection](https://img.shields.io/badge/detector-MMDetection%20%2F%20RTMDet-5C4EE5?style=for-the-badge)](https://github.com/open-mmlab/mmdetection)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?style=for-the-badge)](https://fastapi.tiangolo.com/)
[![Celery](https://img.shields.io/badge/jobs-Celery-37814A?style=for-the-badge)](https://docs.celeryq.dev/)
[![Docker](https://img.shields.io/badge/runtime-Docker-2496ED?style=for-the-badge)](https://www.docker.com/)

**Detect bags. Preserve identities. Count each valid passage once.**

[Open the release](https://github.com/antony502189-max/Model-MP4/releases/tag/v1.0.1) · [Watch the application demo](https://github.com/antony502189-max/Model-MP4/releases/download/v1.0.1/model_mp4_demo.mp4) · [Download the final result](https://github.com/antony502189-max/Model-MP4/releases/download/v1.0.1/conveyor_bag_counter_result.mp4)

</div>

---

## The result

The final run processes the supplied conveyor video with the real **MMDetection RTMDet** backend. It never uses the bootstrap/reference detector in production.

| Validated measure | Final value |
| :-- | --: |
| **Directional bag passages** | **127** |
| Independent manual/reference estimate | ~130 |
| Difference | **−3 (−2.3%)** |
| bbox mAP | 0.785 |
| bbox mAP@0.50 / mAP@0.75 | 0.981 / 0.922 |
| AR@100 | 0.840 |

> The 14,999-frame annotated production result was visually reviewed. Representative real-MMDetection clips matched independent crossings: **4/4** (20–32 s), **1/1** (180–192 s), and **5/5** (540–554 s).

### Submission artefacts

Large binaries are kept in the public GitHub Release rather than normal Git history. This keeps cloning practical and avoids GitHub’s 100 MB blob limit.

| Artefact | Description | Download |
| :-- | :-- | :-- |
| `rtmdet_bag.pth` | Fine-tuned RTMDet checkpoint | [Download](https://github.com/antony502189-max/Model-MP4/releases/download/v1.0.1/rtmdet_bag.pth) |
| `input.mp4` | Supplied source video | [Download](https://github.com/antony502189-max/Model-MP4/releases/download/v1.0.1/input.mp4) |
| `conveyor_bag_counter_result.mp4` | Final annotated production result | [Download](https://github.com/antony502189-max/Model-MP4/releases/download/v1.0.1/conveyor_bag_counter_result.mp4) |
| `model_mp4_demo.mp4` | Docker build and UI demonstration recording | [Watch / download](https://github.com/antony502189-max/Model-MP4/releases/download/v1.0.1/model_mp4_demo.mp4) |

## Run locally

### Prerequisites

- Docker Desktop with Docker Compose v2
- The checkpoint and source video from the [release](https://github.com/antony502189-max/Model-MP4/releases/tag/v1.0.1)

### 1. Place the two release assets

```text
models/rtmdet_bag.pth
input.mp4
```

### 2. Start the full stack

```bash
docker compose up --build
```

### 3. Process a video

Open **http://localhost:8001**, upload `input.mp4`, and start processing. The request returns immediately: Celery performs inference in the background. When the job reaches `completed`, download the annotated MP4 from the UI.

---

## Architecture

```mermaid
flowchart LR
    UI[Browser UI] --> API[FastAPI]
    API --> DB[(SQLite)]
    API --> Q[(Redis)]
    Q --> W[Celery worker]
    W --> D[MMDetection RTMDet]
    D --> T[Tracking + directional counting]
    T --> R[Annotated MP4 + anomalies]
    R --> DB
```

| Component | Responsibility |
| :-- | :-- |
| **FastAPI** | Uploads, job creation, job status, anomaly and result endpoints |
| **Redis + Celery** | Non-blocking job queue and long-running video inference |
| **MMDetection / RTMDet** | One-class bag detection on every source frame |
| **Tracker + counter** | Object identity, directional finite-line crossing and duplicate protection |
| **SQLite + mounted storage** | Durable job state, uploads, results and anomaly audit trail |

`./data` is mounted into both API and worker containers: uploads, database records and processed videos survive container recreation. `./models` is mounted separately for the checkpoint. Redis uses a persistent named volume.

---

## CV pipeline

```text
RTMDet
  → confidence filter
  → conveyor ROI
  → one-class post-ROI NMS
  → IoU tracker
  → bounded prediction bridge
  → directional finite-line crossing
  → one-time track count
```

| Validated setting | Value | Why it matters |
| :-- | --: | :-- |
| Detection confidence | `0.35` | Keeps usable bag detections while rejecting weak boxes |
| Post-ROI NMS IoU | `0.35` | Removes nested one-class detections before association |
| Count direction | `up` | Matches real conveyor motion in image coordinates |
| Prediction bridge | `3` frames | Covers brief detector gaps around the count line |
| Minimum crossing motion | `0.25 px` | Filters stationary / jitter-only line changes |

Each track carries a persistent `counted` flag. A valid directional crossing may increment the result only once, which prevents double counting when the same bag remains visible near the line.

The scripts in `scripts/bootstrap_dataset.py`, `scripts/estimate_reference_count.py`, and `scripts/render_reference_preview.py` are validation/bootstrap utilities only. They do **not** take part in the production inference path and the reference estimate never forces the final MMDetection count.

---

## Asynchronous workflow

```text
POST /api/videos
      ↓
POST /api/jobs/{job_id}/start  →  202 Accepted
      ↓
Celery worker processes the video without blocking HTTP
      ↓
GET /api/jobs/{job_id}  →  progress, count and state
      ↓
GET /api/jobs/{job_id}/result  →  annotated MP4
```

The worker persists progress, bag count, processing FPS and anomalies. A 12-hour Redis visibility timeout and an idempotency guard prevent accidental duplicate processing: only `queued` and explicitly `failed` jobs may start.

### API surface

| Action | Endpoint |
| :-- | :-- |
| Upload a source video | `POST /api/videos` |
| Queue a processing job | `POST /api/jobs/{job_id}/start` |
| Poll job status | `GET /api/jobs/{job_id}` |
| Read anomaly audit events | `GET /api/jobs/{job_id}/anomalies` |
| Download annotated result | `GET /api/jobs/{job_id}/result` |

Working request examples are available in [docs/API_EXAMPLES.md](docs/API_EXAMPLES.md).

---

## Anomaly monitoring

Anomalies are stored as audit signals; they **never alter the counted total**. The validated full run recorded **34** events:

| Type | Events | Signal |
| :-- | --: | :-- |
| `possible_stall` | 18 | Motion below the configured conveyor expectation |
| `reverse_motion` | 6 | Track moves against the expected direction |
| `heavy_occlusion` | 5 | Object overlap / ambiguity can affect association |
| `tracking_gap_near_line` | 5 | Short tracker interruption near the count line |

---

## Verification

```bash
# Build image first with docker compose up --build
docker run --rm -e PYTHONPATH=/app -e DATA_DIR=/tmp/model-mp4-tests model-mp4:local python -m pytest -q
docker compose config --quiet
docker compose ps
```

The suite covers the API and worker lifecycle, post-ROI NMS, direction-aware anomaly logic, tracker bridging and one-time line crossing.

For implementation details, trade-offs and a technical defense, see [docs/TECHNICAL_DEFENSE.md](docs/TECHNICAL_DEFENSE.md).

<div align="center">

Built for the Model-MP4 computer-vision assignment · **FastAPI × Celery × Redis × MMDetection**

</div>
