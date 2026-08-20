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

The independent sanity-check yields **130 bag passages** on the supplied `input.mp4`. This is a validation reference, not the final MMDetection result. The final production MMDetection result is **127** passages (difference -3).

## External source material

Original assignment folder:

https://drive.google.com/drive/folders/1gNVPpVfYS7LIE4PSoTaxnVuzI9Fnyjx5

It contains `Задание.MD` and `input.mp4` (~38 MB). The large video is intentionally not committed to Git.

Generated outside Git:

- bootstrap COCO dataset: 600 sampled frames, 480 train / 120 val;
- bootstrap pseudo-labels: ~700 boxes;
- reference preview video;
- independent reference count: 130 passages.

## Completed production validation

- `models/rtmdet_bag.pth` loads through MMDetection as one-class RTMDet.
- 60-epoch held-out metrics: mAP .785, mAP@.50 .981, mAP@.75 .922, AR@100 .840.
- `docker compose up --build` was run with healthy FastAPI, Redis and Celery.
- Final real-MMDetection job: `04220166-ec7e-4769-8732-8d3a18ce3377`.
- Final count: 127; independent reference: 130; difference: -3.
- Final anomaly breakdown: possible_stall 18, reverse_motion 6, heavy_occlusion 5, tracking_gap_near_line 5.
- Result: `data/results/04220166-ec7e-4769-8732-8d3a18ce3377.mp4`.
- Short-clip validation: 20–32 s 4/4, 180–192 s 1/1, 540–554 s 5/5.

The production fix was not a retrain. Bags travel upward in image coordinates, so the count direction is `up`; the line is correctly calibrated at y=186 px. Post-ROI NMS removes nested RTMDet boxes, a three-frame velocity bridge covers short detector gaps, and the directional motion floor is 0.25 px. Celery uses a 12-hour Redis visibility timeout plus job idempotency to avoid a second multi-hour render after redelivery.

## Important integrity constraint

Do not present the heuristic/bootstrap detector or the 130-event sanity check as MMDetection inference. The final submission must use MMDetection for bag detection, as required by the assignment.

## Useful commands

```bash
pytest -q
python scripts/estimate_reference_count.py input.mp4
python scripts/bootstrap_dataset.py input.mp4 --out dataset --samples 600
cp .env.example .env
docker compose --profile train run --build --rm trainer
docker compose up --build
```

Expected trained checkpoint path:

```text
models/rtmdet_bag.pth
```

## Acceptance target

A reviewer should be able to clone the repository, follow README, run `docker compose up --build`, upload `input.mp4`, start processing without blocking the HTTP request, observe job progress/anomalies, and download a correctly annotated result video with no duplicate bag counts.
