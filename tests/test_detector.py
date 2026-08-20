from app.cv.detector import suppress_overlaps
from app.cv.types import Detection


def test_post_roi_nms_keeps_only_highest_score_nested_detection():
    detections = [
        Detection((10, 10, 110, 60), .92),
        Detection((12, 11, 108, 61), .61),
        Detection((150, 20, 220, 60), .75),
    ]
    kept = suppress_overlaps(detections, max_iou=.35)
    assert [round(item.score, 2) for item in kept] == [.92, .75]
