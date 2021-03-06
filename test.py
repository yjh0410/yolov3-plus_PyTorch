import os
import argparse
import torch
import torch.nn as nn
import torch.backends.cudnn as cudnn
from data import *
import numpy as np
import cv2
import tools
import time


parser = argparse.ArgumentParser(description='YOLO Detection')
parser.add_argument('-v', '--version', default='yolo_v3_plus',
                    help='yolo_v3_plus, yolo_v3_plus_x, yolo_v3_plus_large, yolo_v3_plus_medium, yolo_v3_plus_small, \
                            yolo_v3_slim, yolo_v3_slim_csp.')
parser.add_argument('-d', '--dataset', default='voc',
                    help='voc, coco-val.')
parser.add_argument('-size', '--input_size', default=416, type=int,
                    help='input_size')
parser.add_argument('--trained_model', default='weight/voc/',
                    type=str, help='Trained state_dict file path to open')
parser.add_argument('--conf_thresh', default=0.1, type=float,
                    help='Confidence threshold')
parser.add_argument('--nms_thresh', default=0.50, type=float,
                    help='NMS threshold')
parser.add_argument('--visual_threshold', default=0.3, type=float,
                    help='Final confidence threshold')
parser.add_argument('--cuda', action='store_true', default=False, 
                    help='use cuda.')
parser.add_argument('--diou_nms', action='store_true', default=False, 
                    help='use diou nms.')

args = parser.parse_args()


def vis(img, bboxes, scores, cls_inds, thresh, class_colors, class_names, class_indexs=None, dataset='voc'):
    if dataset == 'voc':
        for i, box in enumerate(bboxes):
            cls_indx = cls_inds[i]
            xmin, ymin, xmax, ymax = box
            if scores[i] > thresh:
                cv2.rectangle(img, (int(xmin), int(ymin)), (int(xmax), int(ymax)), class_colors[int(cls_indx)], 1)
                cv2.rectangle(img, (int(xmin), int(abs(ymin)-20)), (int(xmax), int(ymin)), class_colors[int(cls_indx)], -1)
                mess = '%s' % (class_names[int(cls_indx)])
                cv2.putText(img, mess, (int(xmin), int(ymin-5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)

    elif dataset == 'coco-val' and class_indexs is not None:
        for i, box in enumerate(bboxes):
            cls_indx = cls_inds[i]
            xmin, ymin, xmax, ymax = box
            if scores[i] > thresh:
                cv2.rectangle(img, (int(xmin), int(ymin)), (int(xmax), int(ymax)), class_colors[int(cls_indx)], 1)
                cv2.rectangle(img, (int(xmin), int(abs(ymin)-20)), (int(xmax), int(ymin)), class_colors[int(cls_indx)], -1)
                cls_id = class_indexs[int(cls_indx)]
                cls_name = class_names[cls_id]
                # mess = '%s: %.3f' % (cls_name, scores[i])
                mess = '%s' % (cls_name)
                cv2.putText(img, mess, (int(xmin), int(ymin-5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)

    return img
        

def test(net, device, testset, transform, thresh, class_colors=None, class_names=None, class_indexs=None, dataset='voc'):
    num_images = len(testset)
    for index in range(num_images):
        print('Testing image {:d}/{:d}....'.format(index+1, num_images))
        img, _ = testset.pull_image(index)
        img_tensor, _, h, w, offset, scale = testset.pull_item(index)

        # to tensor
        x = img_tensor.unsqueeze(0).to(device)

        t0 = time.time()
        # forward
        bboxes, scores, cls_inds = net(x)
        print("detection time used ", time.time() - t0, "s")

        # scale each detection back up to the image
        max_line = max(h, w)
        # map the boxes to input image with zero padding
        bboxes *= max_line
        # map to the image without zero padding
        bboxes -= (offset * max_line)

        img_processed = vis(img, bboxes, scores, cls_inds, thresh, class_colors, class_names, class_indexs, dataset)
        cv2.imshow('detection', img_processed)
        cv2.waitKey(0)
        # print('Saving the' + str(index) + '-th image ...')
        # cv2.imwrite('test_images/' + args.dataset+ '3/' + str(index).zfill(6) +'.jpg', img)


if __name__ == '__main__':
    # get device
    if args.cuda:
        print('use cuda')
        cudnn.benchmark = True
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    input_size = [args.input_size, args.input_size]

    # dataset
    if args.dataset == 'voc':
        print('test on voc ...')
        class_names = VOC_CLASSES
        class_indexs = None
        num_classes = 20
        anchor_size = MULTI_ANCHOR_SIZE
        dataset = VOCDetection(root=VOC_ROOT, 
                               img_size=None, 
                               image_sets=[('2007', 'test')], 
                               transform=BaseTransform(input_size))

    elif args.dataset == 'coco-val':
        print('test on coco-val ...')
        class_names = coco_class_labels
        class_indexs = coco_class_index
        num_classes = 80
        anchor_size = MULTI_ANCHOR_SIZE_COCO
        dataset = COCODataset(
                    data_dir=coco_root,
                    json_file='instances_val2017.json',
                    name='val2017',
                    transform=BaseTransform(input_size),
                    img_size=input_size[0])

    class_colors = [(np.random.randint(255),np.random.randint(255),np.random.randint(255)) for _ in range(num_classes)]

    # build model
    # # yolo_v3_plus series: yolo_v3_plus, yolo_v3_plus_x, yolo_v3_plus_large, yolo_v3_plus_medium, yolo_v3_plus_small
    if args.version == 'yolo_v3_plus':
        from models.yolo_v3_plus import YOLOv3Plus
        backbone = 'd-53'
        
        yolo_net = YOLOv3Plus(device, input_size=input_size, num_classes=num_classes, conf_thresh=args.conf_thresh, nms_thresh=args.nms_thresh, anchor_size=anchor_size, backbone=backbone, diou_nms=args.diou_nms)
        print('Let us test yolo_v3_plus on the COCO dataset ......')
    
    elif args.version == 'yolo_v3_plus_x':
        from models.yolo_v3_plus import YOLOv3Plus
        backbone = 'csp-x'
        
        yolo_net = YOLOv3Plus(device, input_size=input_size, num_classes=num_classes, conf_thresh=args.conf_thresh, nms_thresh=args.nms_thresh, anchor_size=anchor_size, backbone=backbone, diou_nms=args.diou_nms)
        print('Let us test yolo_v3_plus_x on the COCO dataset ......')

    elif args.version == 'yolo_v3_plus_large':
        from models.yolo_v3_plus import YOLOv3Plus
        backbone = 'csp-l'
        
        yolo_net = YOLOv3Plus(device, input_size=input_size, num_classes=num_classes, conf_thresh=args.conf_thresh, nms_thresh=args.nms_thresh, anchor_size=anchor_size, backbone=backbone, diou_nms=args.diou_nms)
        print('Let us test yolo_v3_plus_large on the COCO dataset ......')

    elif args.version == 'yolo_v3_plus_medium':
        from models.yolo_v3_plus import YOLOv3Plus
        backbone = 'csp-m'
        
        yolo_net = YOLOv3Plus(device, input_size=input_size, num_classes=num_classes, conf_thresh=args.conf_thresh, nms_thresh=args.nms_thresh, anchor_size=anchor_size, backbone=backbone, diou_nms=args.diou_nms)
        print('Let us test yolo_v3_plus_medium on the COCO dataset ......')
    
    elif args.version == 'yolo_v3_plus_small':
        from models.yolo_v3_plus import YOLOv3Plus
        backbone = 'csp-s'
        
        yolo_net = YOLOv3Plus(device, input_size=input_size, num_classes=num_classes, conf_thresh=args.conf_thresh, nms_thresh=args.nms_thresh, anchor_size=anchor_size, backbone=backbone, diou_nms=args.diou_nms)
        print('Let us test yolo_v3_plus_small on the COCO dataset ......')
    
    # # yolo_v3_slim series: yolo_v3_slim, yolo_v3_slim_csp
    elif args.version == 'yolo_v3_slim':
        from models.yolo_v3_slim import YOLOv3Slim
        backbone = 'd-tiny'
        
        yolo_net = YOLOv3Slim(device, input_size=input_size, num_classes=num_classes, conf_thresh=args.conf_thresh, nms_thresh=args.nms_thresh, anchor_size=anchor_size, backbone=backbone, diou_nms=args.diou_nms)
        print('Let us test yolo_v3_slim on the COCO dataset ......')

    elif args.version == 'yolo_v3_slim_csp':
        from models.yolo_v3_slim import YOLOv3Slim
        backbone = 'csp-slim'
        
        yolo_net = YOLOv3Slim(device, input_size=input_size, num_classes=num_classes, conf_thresh=args.conf_thresh, nms_thresh=args.nms_thresh, anchor_size=anchor_size, backbone=backbone, diou_nms=args.diou_nms)
        print('Let us test yolo_v3_slim_csp on the COCO dataset ......')

    else:
        print('Unknown version !!!')
        exit()

    yolo_net.load_state_dict(torch.load(args.trained_model, map_location=device))
    yolo_net.to(device).eval()
    print('Finished loading model!')

    # evaluation
    test(net=yolo_net, 
        device=device, 
        testset=dataset,
        transform=BaseTransform(input_size),
        thresh=args.visual_threshold,
        class_colors=class_colors,
        class_names=class_names,
        class_indexs=class_indexs,
        dataset=args.dataset
        )
