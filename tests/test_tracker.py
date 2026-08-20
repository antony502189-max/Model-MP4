from app.cv.tracker import IoUTracker
from app.cv.types import Detection


def test_tracker_keeps_identity():
    tr=IoUTracker(iou_threshold=.1,max_age=2,min_hits=1)
    first=tr.update([Detection((10,10,30,30),.9)],0)[0]
    second=tr.update([Detection((12,12,32,32),.8)],1)[0]
    assert first.id == second.id
    assert second.hits == 2


def test_tracker_keeps_identity_after_short_gap():
    tr=IoUTracker(iou_threshold=.1,max_age=2,min_hits=1)
    first=tr.update([Detection((10,10,30,30),.9)],0)[0]
    tr.update([Detection((14,14,34,34),.9)],1)
    tr.update([],2)
    third=tr.update([Detection((22,22,42,42),.9)],3)[0]
    assert third.id == first.id


def test_tracker_advances_a_short_missing_track_with_its_velocity():
    tr=IoUTracker(iou_threshold=.1,max_age=4,min_hits=1,prediction_max_age=2)
    tr.update([Detection((10,10,30,30),.9)],0)
    tr.update([Detection((14,14,34,34),.9)],1)
    predicted=tr.update([],2)[0]
    assert predicted.missed == 1
    assert predicted.center[0] > 24
    assert predicted.center[1] > 24
