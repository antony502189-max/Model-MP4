"""Create a COCO-format bootstrap dataset from the supplied fixed-camera video.

The labels are pseudo-labels based on belt ROI + white-bag contrast. They are intended to reduce
manual labeling work, not replace review. Open the generated JSON in CVAT/Label Studio and correct
bad boxes before final training.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

SRC = np.float32([[313,53],[373,53],[210,359],[27,359]])
DST = np.float32([[0,0],[249,0],[249,599],[0,599]])
M = cv2.getPerspectiveTransform(SRC, DST)
INV = np.linalg.inv(M)


def boxes_for(frame: np.ndarray) -> list[list[int]]:
    original_h, original_w = frame.shape[:2]
    sx, sy = original_w / 640.0, original_h / 360.0
    calibrated = frame if (original_w, original_h) == (640,360) else cv2.resize(frame,(640,360))
    warped = cv2.warpPerspective(calibrated, M, (250,600))
    hsv = cv2.cvtColor(warped, cv2.COLOR_BGR2HSV)
    mask = ((hsv[:,:,2] > 145) & (hsv[:,:,1] < 155)).astype(np.uint8) * 255
    mask[:, :12] = 0; mask[:,238:] = 0; mask[:18] = 0; mask[580:] = 0
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7,7), np.uint8), iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((7,7), np.uint8), iterations=1)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for contour in contours:
        area = cv2.contourArea(contour); x,y,bw,bh = cv2.boundingRect(contour)
        fill = area / max(bw*bh, 1)
        if area < 700 or bw < 70 or bh < 18 or bh > 220 or fill < .18:
            continue
        corners=np.float32([[[x,y],[x+bw,y],[x+bw,y+bh],[x,y+bh]]])
        source=cv2.perspectiveTransform(corners, INV)[0]
        x1=max(0,int(source[:,0].min()*sx)); y1=max(0,int(source[:,1].min()*sy))
        x2=min(original_w-1,int(source[:,0].max()*sx)); y2=min(original_h-1,int(source[:,1].max()*sy))
        if x2-x1 > 15 and y2-y1 > 10:
            boxes.append([x1,y1,x2-x1,y2-y1])
    return boxes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('--out', default='dataset')
    ap.add_argument('--samples', type=int, default=600)
    ap.add_argument('--val-ratio', type=float, default=.2)
    args = ap.parse_args()

    out = Path(args.out)
    for split in ('train','val'):
        (out/'images'/split).mkdir(parents=True, exist_ok=True)
    (out/'annotations').mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(args.video)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); fps = cap.get(cv2.CAP_PROP_FPS) or 25
    selected = np.linspace(0, max(total-1,0), args.samples, dtype=int)
    datasets = {s:{'images':[],'annotations':[],'categories':[{'id':1,'name':'bag'}]} for s in ('train','val')}
    ann_id = 1
    for idx_no, frame_idx in enumerate(selected):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_idx)); ok, frame = cap.read()
        if not ok: continue
        split = 'val' if idx_no % max(int(1/max(args.val_ratio,1e-6)),2) == 0 else 'train'
        image_id = idx_no + 1
        name = f'frame_{frame_idx:06d}.jpg'
        cv2.imwrite(str(out/'images'/split/name), frame)
        h,w = frame.shape[:2]
        datasets[split]['images'].append({'id':image_id,'file_name':name,'width':w,'height':h,'timestamp':frame_idx/fps})
        for x,y,bw,bh in boxes_for(frame):
            datasets[split]['annotations'].append({'id':ann_id,'image_id':image_id,'category_id':1,'bbox':[x,y,bw,bh],'area':bw*bh,'iscrowd':0})
            ann_id += 1
    cap.release()
    for split, payload in datasets.items():
        (out/'annotations'/f'{split}.json').write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
        print(split, 'images=',len(payload['images']),'boxes=',len(payload['annotations']))


if __name__ == '__main__':
    main()
