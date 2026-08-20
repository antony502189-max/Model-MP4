# One-class fine-tuning config for MMDetection 3.x.
# It inherits the official RTMDet-tiny recipe through MMEngine package config syntax.
_base_ = 'mmdet::rtmdet/rtmdet_tiny_8xb32-300e_coco.py'

classes = ('bag',)
data_root = '/dataset/'
metainfo = dict(classes=classes)

model = dict(
    backbone=dict(init_cfg=None),
    bbox_head=dict(num_classes=1),
)
# The upstream recipe sets a backbone-only preload. This project instead uses the
# full COCO RTMDet checkpoint below, so disable the inherited preload to avoid a
# second, redundant network download at every training run.
checkpoint = None

train_dataloader = dict(
    batch_size=8,
    num_workers=4,
    dataset=dict(
        type='CocoDataset',
        data_root=data_root,
        metainfo=metainfo,
        ann_file='annotations/train.json',
        data_prefix=dict(img='images/train/'),
    ),
)
val_dataloader = dict(
    batch_size=8,
    num_workers=2,
    dataset=dict(
        type='CocoDataset',
        data_root=data_root,
        metainfo=metainfo,
        ann_file='annotations/val.json',
        data_prefix=dict(img='images/val/'),
        test_mode=True,
    ),
)
test_dataloader = val_dataloader

val_evaluator = dict(type='CocoMetric', ann_file=data_root + 'annotations/val.json', metric='bbox')
test_evaluator = val_evaluator

train_cfg = dict(type='EpochBasedTrainLoop', max_epochs=60, val_interval=5)
# The inherited RTMDet recipe is 300 epochs with a 1,000-iteration warm-up.
# This compact, fixed-camera dataset has only 40 batches per epoch, so preserve
# the same training phases on the documented 60-epoch schedule instead of
# spending most of it warming up and never reaching cosine decay.
param_scheduler = [
    dict(type='LinearLR', start_factor=1e-5, by_epoch=False, begin=0, end=100),
    dict(
        type='CosineAnnealingLR',
        eta_min=2e-4,
        begin=3,
        end=60,
        T_max=57,
        by_epoch=True,
        convert_to_iter_based=True,
    ),
]
default_hooks = dict(
    checkpoint=dict(
        interval=1,
        max_keep_ckpts=3,
        save_best='coco/bbox_mAP',
        rule='greater',
    ),
    logger=dict(interval=10),
)

# COCO-pretrained RTMDet-tiny. The one-class head is re-initialized while backbone/neck weights transfer.
load_from = 'https://download.openmmlab.com/mmdetection/v3.0/rtmdet/rtmdet_tiny_8xb32-300e_coco/rtmdet_tiny_8xb32-300e_coco_20220902_112414-78e30dcc.pth'
work_dir = '/work_dirs/rtmdet_bag'
