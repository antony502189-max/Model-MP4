# Codex handoff

## Current state

This repository is the implementation for the conveyor bag-counting test assignment.

Implemented:

- FastAPI upload/start/status/anomalies/result API;
- Celery + Redis asynchronous video processing;
- MMDetection RTMDet-tiny one-class (`bag`) detector wrapper;
- ROI filtering, IoU tracking, directional line crossing and duplicate-count protection;
- anomaly monitoring and annotated video rendering;
- SQLite persistence and host-mounted video/model storage;
- Docker/Docker Compose setup, web UI, tests and training/bootstrap scripts;
- independent reference-event analysis for the supplied test video.

The independent sanity-check currently yields **130 bag passages** on the supplied `input.mp4`. This is a validation reference, not the final MMDetection result.

## External source material

Original assignment folder:

https://drive.google.com/drive/folders/1gNVPpVfYS7LIE4PSoTaxnVuzI9Fnyjx5

It contains `Задание.MD` and `input.mp4` (~38 MB). The large video is intentionally not committed to Git.

Generated outside Git:

- bootstrap COCO dataset: 600 sampled frames, 480 train / 120 val;
- bootstrap pseudo-labels: ~700 boxes;
- reference preview video;
- independent reference count: 130 passages.

## Highest-priority next work

1. Obtain `input.mp4` from the Drive folder and place it in repository root.
2. Run/inspect the bootstrap dataset generator and correct pseudo-labels if needed.
3. Verify the MMDetection config against the exact installed MMDetection/MMEngine versions.
4. Fine-tune RTMDet-tiny and produce `models/rtmdet_bag.pth`.
5. Process the complete `input.mp4` through the actual MMDetection pipeline.
6. Compare final count with the independent 130-event reference; inspect any discrepancy frame-by-frame.
7. Harden tracker/counting behavior around occlusion and lost tracks near the line. If needed, replace the simple IoU tracker with ByteTrack while preserving the current counting interface.
8. Run all tests and add integration tests for API/job lifecycle.
9. Validate `docker compose up --build` from a clean machine/state.
10. Update README with the final measured MMDetection count, model metrics, training details and exact runtime instructions.

## Important integrity constraint

Do not present the heuristic/bootstrap detector or the 130-event sanity check as MMDetection inference. The final submission must use MMDetection for bag detection, as required by the assignment.

## Useful commands

```bash
pytest -q
python scripts/estimate_reference_count.py input.mp4
python scripts/bootstrap_dataset.py input.mp4 --out dataset --samples 600
cp .env.example .env
docker compose --profile train run --rm trainer
docker compose up --build
```

Expected trained checkpoint path:

```text
models/rtmdet_bag.pth
```

## Acceptance target

A reviewer should be able to clone the repository, follow README, run `docker compose up --build`, upload `input.mp4`, start processing without blocking the HTTP request, observe job progress/anomalies, and download a correctly annotated result video with no duplicate bag counts.
