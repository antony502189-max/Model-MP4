from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import cv2
import numpy as np

from app.config import settings
from app.cv.types import Detection


def bbox_iou(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> float:
    x1 = max(first[0], second[0])
    y1 = max(first[1], second[1])
    x2 = min(first[2], second[2])
    y2 = min(first[3], second[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    first_area = max(0.0, first[2] - first[0]) * max(0.0, first[3] - first[1])
    second_area = max(0.0, second[2] - second[0]) * max(0.0, second[3] - second[1])
    union = first_area + second_area - intersection
    return intersection / union if union else 0.0


def suppress_overlaps(detections: list[Detection], max_iou: float) -> list[Detection]:
    """Keep the highest-score detection for each strongly overlapping bag."""
    kept: list[Detection] = []
    for detection in sorted(detections, key=lambda item: item.score, reverse=True):
        if all(bbox_iou(detection.bbox, existing.bbox) < max_iou for existing in kept):
            kept.append(detection)
    return kept


class Detector(ABC):
    name: str

    @abstractmethod
    def detect(self, frame: np.ndarray) -> list[Detection]:
        raise NotImplementedError


class MMDetectionDetector(Detector):
    name = 'mmdet'

    def __init__(self) -> None:
        config = Path(settings.mmdet_config)
        checkpoint = Path(settings.mmdet_checkpoint)
        if not config.exists():
            raise FileNotFoundError(f'MMDetection config not found: {config}')
        if not checkpoint.exists():
            raise FileNotFoundError(
                f'MMDetection checkpoint not found: {checkpoint}. '
                'Train/copy a one-class bag checkpoint as documented in README.'
            )

        from mmdet.apis import inference_detector, init_detector

        self._inference_detector = inference_detector
        self.model = init_detector(str(config), str(checkpoint), device=settings.device)

    def detect(self, frame: np.ndarray) -> list[Detection]:
        result = self._inference_detector(self.model, frame)
        instances = result.pred_instances.cpu()
        boxes = instances.bboxes.numpy()
        scores = instances.scores.numpy()
        labels = instances.labels.numpy()
        detections: list[Detection] = []
        h, w = frame.shape[:2]
        roi = np.array([(int(x * w), int(y * h)) for x, y in settings.parsed_roi], dtype=np.int32)
        for bbox, score, label in zip(boxes, scores, labels):
            if int(label) != 0 or float(score) < settings.confidence_threshold:
                continue
            x1, y1, x2, y2 = map(float, bbox)
            center = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
            if cv2.pointPolygonTest(roi, center, False) < 0:
                continue
            detections.append(Detection((x1, y1, x2, y2), float(score), int(label)))
        # RTMDet's model-level NMS is deliberately permissive for COCO.  With
        # this one-class conveyor camera it can leave nested boxes for one bag,
        # creating duplicate tracks and false heavy-occlusion alerts.
        return suppress_overlaps(detections, settings.detection_nms_iou_threshold)


class ContrastBootstrapDetector(Detector):
    """Camera-specific fallback used only for dataset bootstrapping and local pipeline checks.

    It rectifies the known conveyor plane, segments bright low-saturation bags there, then maps
    candidate boxes back to the source frame. The production submission backend remains MMDetection.
    """

    name = 'contrast'

    def __init__(self) -> None:
        src = np.float32([[313, 53], [373, 53], [210, 359], [27, 359]])
        dst = np.float32([[0, 0], [249, 0], [249, 599], [0, 599]])
        self.matrix = cv2.getPerspectiveTransform(src, dst)
        self.inverse = np.linalg.inv(self.matrix)

    def detect(self, frame: np.ndarray) -> list[Detection]:
        # Geometry is calibrated for the provided 640x360 video. Scale to another resolution first.
        h, w = frame.shape[:2]
        sx, sy = w / 640.0, h / 360.0
        if (w, h) != (640, 360):
            calibrated = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_LINEAR)
        else:
            calibrated = frame

        warped = cv2.warpPerspective(calibrated, self.matrix, (250, 600))
        hsv = cv2.cvtColor(warped, cv2.COLOR_BGR2HSV)
        mask = ((hsv[:, :, 2] > 145) & (hsv[:, :, 1] < 155)).astype(np.uint8) * 255
        mask[:, :12] = 0
        mask[:, 238:] = 0
        mask[:18] = 0
        mask[580:] = 0
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8), iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8), iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections: list[Detection] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            x, y, bw, bh = cv2.boundingRect(contour)
            fill = area / max(bw * bh, 1)
            if area < 700 or bw < 70 or bh < 18 or bh > 220 or fill < 0.18:
                continue

            corners = np.float32([[[x, y], [x + bw, y], [x + bw, y + bh], [x, y + bh]]])
            original = cv2.perspectiveTransform(corners, self.inverse)[0]
            x1 = max(0.0, float(original[:, 0].min()) * sx)
            y1 = max(0.0, float(original[:, 1].min()) * sy)
            x2 = min(float(w - 1), float(original[:, 0].max()) * sx)
            y2 = min(float(h - 1), float(original[:, 1].max()) * sy)
            if x2 - x1 > 15 and y2 - y1 > 10:
                detections.append(Detection((x1, y1, x2, y2), 0.70, 0))
        return detections


def build_detector() -> Detector:
    backend = settings.detector_backend.lower().strip()
    if backend == 'mmdet':
        return MMDetectionDetector()
    if backend == 'contrast':
        return ContrastBootstrapDetector()
    raise ValueError(f'Unknown detector backend: {backend}')
