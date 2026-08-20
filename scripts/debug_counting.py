#!/usr/bin/env python3
"""Run the real MMDetection counter on a short, inspectable video interval.

This utility is intentionally separate from the asynchronous worker: it makes
tracker association and line-crossing decisions auditable before a full video
is queued.  It honours the same environment configuration as production.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import cv2

from app.config import settings
from app.cv.anomalies import AnomalyMonitor
from app.cv.counter import LineCounter, side_of_line
from app.cv.detector import build_detector
from app.cv.tracker import IoUTracker
from app.cv.visualize import draw_overlay


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", help="Video path visible inside the container")
    parser.add_argument("--start", type=float, default=0.0, help="Start time in seconds")
    parser.add_argument("--duration", type=float, default=12.0, help="Duration in seconds")
    parser.add_argument("--output", required=True, help="Annotated short-clip output path")
    parser.add_argument("--report", required=True, help="JSON diagnostic report output path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {args.video}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    start_frame = max(0, round(args.start * fps))
    end_frame = start_frame + max(1, round(args.duration * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    line_a = (round(settings.line_x1 * width), round(settings.line_y1 * height))
    line_b = (round(settings.line_x2 * width), round(settings.line_y2 * height))
    roi = [(round(x * width), round(y * height)) for x, y in settings.parsed_roi]
    detector = build_detector()
    tracker = IoUTracker(
        settings.tracker_iou_threshold,
        settings.tracker_max_age,
        settings.tracker_min_hits,
        settings.tracker_prediction_max_age,
    )
    counter = LineCounter(line_a, line_b, settings.count_direction, settings.line_crossing_min_motion)
    monitor = AnomalyMonitor(fps, (line_a[1] + line_b[1]) / 2, settings.count_direction)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(args.output, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Cannot write {args.output}")

    scores: list[float] = []
    detections_per_frame: list[int] = []
    near_line: list[dict] = []
    crossings: list[dict] = []
    all_track_ids: set[int] = set()
    frame_index = start_frame
    try:
        while frame_index < end_frame:
            ok, frame = cap.read()
            if not ok:
                break
            detections = detector.detect(frame)
            scores.extend(det.score for det in detections)
            detections_per_frame.append(len(detections))
            tracks = tracker.update(detections, frame_index)
            events = counter.update(tracks)
            all_track_ids.update(track.id for track in tracks)
            monitor.inspect(tracks, frame_index, processing_fps=None)

            for track in tracks:
                if len(track.centers) < 2 or abs(track.center[1] - line_a[1]) > 55:
                    continue
                previous = track.centers[-2]
                current = track.centers[-1]
                entry = {
                    "frame": frame_index,
                    "timestamp": round(frame_index / fps, 3),
                    "track_id": track.id,
                    "previous_center": [round(value, 2) for value in previous],
                    "center": [round(value, 2) for value in current],
                    "previous_side": round(side_of_line(previous, line_a, line_b), 2),
                    "side": round(side_of_line(current, line_a, line_b), 2),
                    "counted": track.counted,
                }
                near_line.append(entry)
                if track.id in events:
                    crossings.append(entry)

            writer.write(draw_overlay(frame, tracks, counter.count, line_a, line_b, roi,
                                      detector.name, len(monitor.items), 0.0))
            frame_index += 1
    finally:
        cap.release()
        writer.release()

    report = {
        "backend": detector.name,
        "settings": {
            "confidence_threshold": settings.confidence_threshold,
            "detection_nms_iou_threshold": settings.detection_nms_iou_threshold,
            "roi": roi,
            "line": [line_a, line_b],
            "direction": settings.count_direction,
            "tracker_iou_threshold": settings.tracker_iou_threshold,
            "tracker_max_age": settings.tracker_max_age,
            "tracker_min_hits": settings.tracker_min_hits,
            "tracker_prediction_max_age": settings.tracker_prediction_max_age,
        },
        "interval": {"start_seconds": args.start, "duration_seconds": args.duration,
                     "start_frame": start_frame, "end_frame": frame_index},
        "detection_scores": {
            "count": len(scores),
            "min": min(scores, default=None),
            "p10": sorted(scores)[max(0, int(len(scores) * .1) - 1)] if scores else None,
            "median": sorted(scores)[len(scores) // 2] if scores else None,
            "p90": sorted(scores)[min(len(scores) - 1, int(len(scores) * .9))] if scores else None,
            "max": max(scores, default=None),
        },
        "detections_per_frame": {
            "min": min(detections_per_frame, default=0),
            "mean": sum(detections_per_frame) / max(len(detections_per_frame), 1),
            "max": max(detections_per_frame, default=0),
        },
        "track_ids_created_or_active": len(all_track_ids),
        "crossing_count": counter.count,
        "crossings": crossings,
        "near_line_samples": near_line,
        "anomaly_types": dict(Counter(item.type for item in monitor.items)),
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
