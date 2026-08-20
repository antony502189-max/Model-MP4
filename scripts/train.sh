#!/usr/bin/env bash
set -euo pipefail
CONFIG=${1:-/app/mmdet_configs/rtmdet_tiny_bag.py}
EXTRA_ARGS=()
if [[ -n "${TRAIN_MAX_EPOCHS:-}" ]]; then
  EXTRA_ARGS+=(--cfg-options "train_cfg.max_epochs=${TRAIN_MAX_EPOCHS}")
fi
if [[ -n "${TRAIN_RESUME:-}" ]]; then
  EXTRA_ARGS+=(--resume "${TRAIN_RESUME}")
fi
python /usr/local/lib/python3.10/site-packages/mmdet/.mim/tools/train.py "$CONFIG" "${EXTRA_ARGS[@]}"
BEST=$(find /work_dirs/rtmdet_bag -name 'best_coco_bbox_mAP*.pth' -type f -print -quit)
LATEST=$(find /work_dirs/rtmdet_bag -name 'epoch_*.pth' -type f -printf '%T@ %p\n' | sort -n | tail -n1 | cut -d' ' -f2-)
SOURCE=${BEST:-$LATEST}
if [[ -z "$SOURCE" ]]; then echo 'No checkpoint produced'; exit 1; fi
cp "$SOURCE" /models/rtmdet_bag.pth
echo "Saved /models/rtmdet_bag.pth from $SOURCE"
