import logging
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import numpy as np
import torch
import torch.nn as nn

# Ultralytics 관련 모듈 대거 임포트 (보안 에러 방지용)
try:
    from ultralytics import YOLO
    from ultralytics.nn.tasks import DetectionModel
    from ultralytics.nn.modules.conv import Conv, Concat
    from ultralytics.nn.modules.block import C2f, Bottleneck, SPPF, DFL
    from ultralytics.nn.modules.head import Detect
except ImportError:
    YOLO = None
    DetectionModel = None
    Conv = None
    Concat = None
    C2f = None
    Bottleneck = None
    SPPF = None
    DFL = None
    Detect = None

logger = logging.getLogger(__name__)

class YOLOFashionDetector:
    """
    YOLO 기반 패션 아이템 감지기 (PyTorch 2.6+ 호환 패치 V3)
    """
    
    def __init__(self):
        self.model = None
        self.pose_model = None
        self.initialized = False
        
        self.PERSON_CLASS_ID = 0
        self.UPPER_RATIO = 0.55
        self.LOWER_RATIO = 0.45
        
    def initialize(self):
        if self.initialized: return True
            
        try:
            if not YOLO: raise ImportError("ultralytics not installed")

            # 🚨 [FIX V3] PyTorch 2.6+ 보안 에러 완벽 대응
            if hasattr(torch.serialization, 'add_safe_globals'):
                safe_globals = []
                
                # 1. PyTorch 기본 모듈
                safe_globals.extend([
                    nn.Sequential, nn.Conv2d, nn.BatchNorm2d, nn.SiLU,
                    nn.Upsample, nn.MaxPool2d, nn.ModuleList, nn.Softmax,
                    nn.Sigmoid, nn.Identity, nn.Parameter
                ])
                
                # 2. Ultralytics 커스텀 모듈 (SPPF, Concat, DFL 추가)
                if DetectionModel: safe_globals.append(DetectionModel)
                if Conv: safe_globals.append(Conv)
                if C2f: safe_globals.append(C2f)
                if Bottleneck: safe_globals.append(Bottleneck)
                if SPPF: safe_globals.append(SPPF)
                if Concat: safe_globals.append(Concat)
                if DFL: safe_globals.append(DFL)
                if Detect: safe_globals.append(Detect)
                
                torch.serialization.add_safe_globals(safe_globals)
                logger.info(f"🛡️ Applied PyTorch safe globals for {len(safe_globals)} modules")
            
            self.model = YOLO('yolov8n.pt')
            
            try:
                self.pose_model = YOLO('yolov8n-pose.pt')
                logger.info("✅ YOLO Pose model loaded")
            except:
                self.pose_model = None
            
            self.initialized = True
            logger.info("✅ YOLO Fashion Detector initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ YOLO initialization failed: {e}")
            return False
    
    def detect_person(self, image: Image.Image) -> List[Dict[str, Any]]:
        if not self.initialized:
            if not self.initialize(): return []
        
        try:
            img_array = np.array(image)
            results = self.model(img_array, classes=[self.PERSON_CLASS_ID], verbose=False)
            
            persons = []
            for result in results:
                if result.boxes is None: continue
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    persons.append({
                        "bbox": (int(x1), int(y1), int(x2), int(y2)),
                        "confidence": float(box.conf[0]),
                        "area": (x2 - x1) * (y2 - y1)
                    })
            persons.sort(key=lambda x: x["area"], reverse=True)
            return persons
        except Exception as e:
            logger.error(f"❌ Person detection failed: {e}")
            return []
    
    def get_keypoints(self, image: Image.Image) -> Optional[Dict[str, Tuple[int, int]]]:
        if self.pose_model is None: return None
        try:
            img_array = np.array(image)
            results = self.pose_model(img_array, verbose=False)
            KEYPOINT_NAMES = {5: "left_shoulder", 6: "right_shoulder", 11: "left_hip", 12: "right_hip"}
            
            for result in results:
                if result.keypoints is None: continue
                kps = result.keypoints.xy[0].tolist()
                kp_dict = {}
                for idx, name in KEYPOINT_NAMES.items():
                    if idx < len(kps):
                        x, y = kps[idx]
                        if x > 0 and y > 0: kp_dict[name] = (int(x), int(y))
                if kp_dict: return kp_dict
            return None
        except: return None
    
    # [주의] 메서드 이름이 crop_fashion_regions 입니다. (i 하나)
    def crop_fashion_regions(self, image: Image.Image, target: str = "full") -> Optional[Image.Image]:
        persons = self.detect_person(image)
        if not persons: return image
        
        main_person = persons[0]
        x1, y1, x2, y2 = main_person["bbox"]
        img_w, img_h = image.size
        
        pad_x = int((x2 - x1) * 0.1)
        pad_y = int((y2 - y1) * 0.05)
        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(img_w, x2 + pad_x)
        y2 = min(img_h, y2 + pad_y)
        
        if target == "upper":
            kps = self.get_keypoints(image)
            if kps and "left_hip" in kps:
                y2 = min(kps["left_hip"][1] + 20, y2)
            else:
                y2 = int(y1 + (y2 - y1) * self.UPPER_RATIO)
        elif target == "lower":
            kps = self.get_keypoints(image)
            if kps and "left_hip" in kps:
                y1 = max(kps["left_hip"][1] - 20, y1)
            else:
                y1 = int(y1 + (y2 - y1) * (1 - self.LOWER_RATIO))
        
        return image.crop((x1, y1, x2, y2))
    
    def extract_fashion_features(self, image: Image.Image) -> Dict[str, Optional[Image.Image]]:
        result = {"full": image, "upper": None, "lower": None}
        persons = self.detect_person(image)
        if not persons: return result
        
        result["full"] = self.crop_fashion_regions(image, "full")
        result["upper"] = self.crop_fashion_regions(image, "upper")
        result["lower"] = self.crop_fashion_regions(image, "lower")
        return result

# 전역 인스턴스
yolo_detector = YOLOFashionDetector()