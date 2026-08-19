from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

import cv2

from app.config import settings
from app.cv.anomalies import AnomalyMonitor
from app.cv.counter import LineCounter
from app.cv.detector import build_detector
from app.cv.tracker import IoUTracker
from app.cv.visualize import draw_overlay


ProgressCallback = Callable[[float, int, list[dict], float], None]


def process_video(input_path: str, output_path: str, progress_cb: ProgressCallback | None = None) -> dict:
    detector = build_detector()
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f'Cannot open video: {input_path}')

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f'Cannot create output video: {output_path}')

    roi = [(int(x * width), int(y * height)) for x, y in settings.parsed_roi]
    line_a = (int(settings.line_x1 * width), int(settings.line_y1 * height))
    line_b = (int(settings.line_x2 * width), int(settings.line_y2 * height))

    tracker = IoUTracker(settings.tracker_iou_threshold, settings.tracker_max_age, settings.tracker_min_hits)
    counter = LineCounter(line_a, line_b, settings.count_direction)
    monitor = AnomalyMonitor(fps, (line_a[1] + line_b[1]) / 2)

    started = time.perf_counter()
    frame_index = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            detections = detector.detect(frame)
            tracks = tracker.update(detections, frame_index)
            counter.update(tracks)

            elapsed = max(time.perf_counter() - started, 1e-6)
            proc_fps = (frame_index + 1) / elapsed
            monitor.inspect(tracks, frame_index, proc_fps)

            annotated = draw_overlay(
                frame, tracks, counter.count, line_a, line_b, roi,
                detector.name, len(monitor.items), proc_fps,
            )
            writer.write(annotated)

            frame_index += 1
            if progress_cb and (frame_index % max(int(fps), 1) == 0 or frame_index == total_frames):
                progress = min(99.5, frame_index / max(total_frames, 1) * 100)
                progress_cb(progress, counter.count, [a.as_dict() for a in monitor.items], proc_fps)
    finally:
        cap.release()
        writer.release()

    elapsed = max(time.perf_counter() - started, 1e-6)
    proc_fps = frame_index / elapsed
    return {
        'count': counter.count,
        'anomalies': [a.as_dict() for a in monitor.items],
        'processing_fps': proc_fps,
        'frames': frame_index,
        'backend': detector.name,
    }
