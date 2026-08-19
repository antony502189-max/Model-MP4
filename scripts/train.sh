#!/usr/bin/env bash
set -euo pipefail
CONFIG=${1:-/app/mmdet_configs/rtmdet_tiny_bag.py}
mim train mmdet "$CONFIG"
LATEST=$(find /work_dirs/rtmdet_bag -name '*.pth' -type f -printf '%T@ %p\n' | sort -n | tail -n1 | cut -d' ' -f2-)
if [[ -z "$LATEST" ]]; then echo 'No checkpoint produced'; exit 1; fi
cp "$LATEST" /models/rtmdet_bag.pth
echo "Saved /models/rtmdet_bag.pth from $LATEST"
