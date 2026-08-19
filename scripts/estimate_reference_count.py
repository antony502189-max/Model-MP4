"""Camera-specific independent line-signal sanity check for input.mp4.

This is not the application detector. It gives a reference count from brightness changes at a fixed
belt cross-section. On the supplied video it should be close to 130 events.
"""
import argparse
import cv2
import numpy as np


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('video'); args=ap.parse_args()
    cap=cv2.VideoCapture(args.video); fps=cap.get(cv2.CAP_PROP_FPS) or 25
    # Belt perspective corners for the supplied 640x360 camera.
    src=np.float32([[313,53],[373,53],[210,359],[27,359]])
    dst=np.float32([[0,0],[249,0],[249,599],[0,599]])
    matrix=cv2.getPerspectiveTransform(src,dst)
    scores=[]; frame_idx=0
    while True:
        ok,frame=cap.read()
        if not ok: break
        if frame_idx % 5 == 0:
            warped=cv2.warpPerspective(frame,matrix,(250,600))
            band=warped[400:440,25:225]
            hsv=cv2.cvtColor(band,cv2.COLOR_BGR2HSV)
            score=float(np.mean((hsv[:,:,2] > 145) & (hsv[:,:,1] < 150)))
            scores.append(score)
        frame_idx += 1
    cap.release()
    active = np.asarray(scores) > .30
    count = 0
    start = None
    for i, value in enumerate(active):
        if value and start is None:
            start = i
        if (not value or i == len(active) - 1) and start is not None:
            end = i if not value else i + 1
            if end - start >= 2:
                count += 1
            start = None
    print(count)

if __name__=='__main__': main()
