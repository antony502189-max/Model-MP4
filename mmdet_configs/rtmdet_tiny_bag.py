# One-class fine-tuning config for MMDetection 3.x.
# It inherits the official RTMDet-tiny recipe through MMEngine package config syntax.
_base_ = 'mmdet::rtmdet/rtmdet_tiny_8xb32-300e_coco.py'

classes = ('bag',)
data_root = '/dataset/'
metainfo = dict(classes=classes)

model = dict(bbox_head=dict(num_classes=1))

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

# COCO-pretrained RTMDet-tiny. The one-class head is re-initialized while backbone/neck weights transfer.
load_from = 'https://download.openmmlab.com/mmdetection/v3.0/rtmdet/rtmdet_tiny_8xb32-300e_coco/rtmdet_tiny_8xb32-300e_coco_20220902_112414-78e30dcc.pth'
work_dir = '/work_dirs/rtmdet_bag'
