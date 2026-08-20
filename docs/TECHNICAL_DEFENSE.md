# Technical defense notes

## Why MMDetection + RTMDet-tiny?

The task explicitly requires MMDetection. RTMDet-tiny is a strong fit for a fixed-camera, single-class detector because it has a small model footprint and a favorable accuracy/latency trade-off. The bags are not a native COCO class, so the correct engineering choice is one-class fine-tuning rather than pretending a COCO label such as `suitcase` is equivalent.

## Why not count detections per frame?

A bag remains visible for many frames. Per-frame counting would overcount the same physical object dozens of times. The pipeline therefore separates three concerns:

1. **Detection** answers: “where are bags in this frame?”
2. **Tracking** answers: “which detection corresponds to which physical bag over time?”
3. **Line crossing** answers: “has this physical track crossed the business boundary in the configured direction?”

The `counted` flag is an invariant on a track. Once set, that ID cannot increment the total again.

## Why a directional line?

A directional line is more robust than “count when center enters an ROI”. It creates a precise event boundary and naturally rejects reverse motion. The line is normalized to the image dimensions so resolution changes do not require changing source code.

## What happens if the detector misses a few frames?

The tracker keeps unmatched tracks alive for `max_age` frames and advances a confirmed track by its velocity for at most three missing frames. This bridges a single detector dropout at the line without inventing a long unobserved path. Post-ROI NMS at IoU 0.35 also removes nested one-class RTMDet boxes before association. A temporary loss near the line remains an anomaly because that is the highest-risk location for duplicate counting.

## Why not ByteTrack directly?

ByteTrack is a good production choice and can replace the current tracker. For a test assignment, the deterministic IoU tracker has two advantages: the identity logic is small enough to audit in full, and the fixed camera with moderate frame-to-frame motion makes IoU matching adequate after detector fine-tuning. Real-MMDetection validation on 20–32 s, 180–192 s and 540–554 s clips matched independent crossings 4/4, 1/1 and 5/5, respectively. The interfaces intentionally isolate the tracker so ByteTrack is a local replacement rather than an architectural rewrite.

If asked what would be changed for a busier conveyor: use ByteTrack/OC-SORT, add appearance embeddings if necessary, tune low/high confidence association thresholds, and measure IDF1/HOTA in addition to detection AP.

## Why Celery + Redis?

Inference over a 10-minute video is a long-running CPU/GPU job. Holding the HTTP connection open would couple request latency to inference time and waste web-server capacity. The API writes metadata, queues a Celery task, and returns HTTP 202. The worker owns the expensive computation and periodically persists progress.

This also creates a clean path to horizontal scaling: more workers can consume the same Redis queue. For multiple concurrent writers, SQLite should then be replaced with PostgreSQL.

## Why SQLite here?

The assignment is a single-node demo with one worker. SQLite removes an unnecessary infrastructure component while still providing persistent job metadata. WAL mode and a busy timeout are enabled. PostgreSQL is the obvious production upgrade once concurrent workers or stronger transactional guarantees are required.

## Why is video storage a bind mount?

Container filesystems are ephemeral. `./data:/data` makes uploaded and rendered videos survive container recreation, directly satisfying the persistence requirement. The trained checkpoint also lives in `./models:/models` so rebuilding the application image does not erase the trained model.

## What is an anomaly in this project?

An anomaly is not necessarily an incorrect count; it is an observable condition that reduces confidence in counting quality. The monitor records:

- tracking loss close to the count line;
- reverse motion;
- heavy track overlap/occlusion;
- unusually stationary objects;
- extremely slow inference.

The key design choice is that anomalies are **stored and displayed separately** instead of silently modifying the count. This keeps the primary metric deterministic and makes questionable segments auditable.

## How to validate correctness

Use three layers:

1. detector quality on held-out labeled frames (`bbox mAP`, precision/recall, especially recall near the line);
2. tracking/count tests with synthetic trajectories (unit tests in `tests/`);
3. end-to-end count on `input.mp4` compared with the independent fixed-line reference of 130 events, followed by manual review of disagreements.

For the final submission, manually inspect every discrepancy between the RTMDet result and the reference rather than blindly forcing the number to 130.

## Final measured result

The delivered `models/rtmdet_bag.pth` achieved held-out bbox mAP .785 (mAP@.50 .981, mAP@.75 .922, AR@100 .840). The final real-MMDetection job counted **127** passages on `input.mp4`, versus an independent reference of approximately **130** (difference -3, -2.3%). Visual review confirmed boxes, labels, count overlay, ROI and calibrated line on the 14,999-frame result.

The 34 persisted anomalies are observational rather than count adjustments: 18 `possible_stall`, 6 `reverse_motion`, 5 `heavy_occlusion` and 5 `tracking_gap_near_line`. This is a large reduction from the pre-fix run, whose wrong `down` direction and nested detections yielded 498 mostly false alerts.

## Known trade-offs

- The bootstrap pseudo-labeler is calibrated to the supplied camera and is only a labeling aid.
- The current IoU tracker does not use appearance features.
- SQLite is not intended for many concurrent workers.
- CPU MMDetection inference will be much slower than GPU inference.
- The independent 130-event signal is a sanity reference, not annotated ground truth.
