from app.cv.counter import LineCounter
from app.cv.types import Track


def test_counts_once_when_crossing_down():
    t=Track(id=1,bbox=(0,0,10,10),score=.9,hits=2,centers=[(5,40),(5,60)])
    c=LineCounter((0,50),(100,50),'down')
    assert c.update([t]) == [1]
    assert c.count == 1
    t.centers.append((5,70))
    assert c.update([t]) == []
    assert c.count == 1


def test_wrong_direction_is_not_counted():
    t=Track(id=1,bbox=(0,0,10,10),score=.9,hits=2,centers=[(5,60),(5,40)])
    c=LineCounter((0,50),(100,50),'down')
    assert c.update([t]) == []
    assert c.count == 0
