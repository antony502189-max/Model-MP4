from app.cv.tracker import IoUTracker
from app.cv.types import Detection


def test_tracker_keeps_identity():
    tr=IoUTracker(iou_threshold=.1,max_age=2,min_hits=1)
    first=tr.update([Detection((10,10,30,30),.9)],0)[0]
    second=tr.update([Detection((12,12,32,32),.8)],1)[0]
    assert first.id == second.id
    assert second.hits == 2
