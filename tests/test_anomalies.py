from app.cv.anomalies import AnomalyMonitor
from app.cv.types import Track


def _upward_track() -> Track:
    centers = [(40.0, 120.0 - offset * 3) for offset in range(8)]
    return Track(id=7, bbox=(30, 90, 50, 110), score=.9, hits=8, centers=centers)


def test_upward_conveyor_motion_is_not_reverse_motion():
    monitor = AnomalyMonitor(fps=25, line_y=80, direction='up')
    monitor.inspect([_upward_track()], frame_index=8)
    assert not [item for item in monitor.items if item.type == 'reverse_motion']


def test_upward_motion_is_reverse_when_configured_downward():
    monitor = AnomalyMonitor(fps=25, line_y=80, direction='down')
    monitor.inspect([_upward_track()], frame_index=8)
    assert [item for item in monitor.items if item.type == 'reverse_motion']
