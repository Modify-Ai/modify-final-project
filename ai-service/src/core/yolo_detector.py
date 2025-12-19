import logging
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw
import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

class YOLOFashionDetector:
    """
    YOLO 기반 패션 아이템 감지기
    - YOLOv8을 사용하여 사람/의류 영역 감지
    - 상의/하의 영역 분리 지원
    """
    
    def __init__(self):
        self.model = None
        self.pose_model = None
        self.seg_model = None       # [추가] 세그멘테이션용 (가상 피팅)
        self.initialized = False
        
        # COCO 클래스 ID (person = 0)
        self.PERSON_CLASS_ID = 0
        
        # 상의/하의 비율 (전체 사람 bbox 기준)
        self.UPPER_RATIO = 0.55  # 상위 55%가 상의
        self.LOWER_RATIO = 0.45  # 하위 45%가 하의
        
    def initialize(self):
        """YOLO 모델 로드"""
        if self.initialized: return True
        try:
            from ultralytics import YOLO
            
            # [보안 패치] PyTorch Safe Globals 등록
            try:
                from ultralytics.nn.tasks import DetectionModel
                safe_classes = [
                    DetectionModel,
                    nn.Sequential, nn.Conv2d, nn.BatchNorm2d, nn.SiLU, 
                    nn.Upsample, nn.MaxPool2d, nn.ModuleList,
                ]
                torch.serialization.add_safe_globals(safe_classes)
            except: pass

            # [보안 패치] weights_only=False 강제 적용 (로딩 시에만)
            _original_load = torch.load
            def _unsafe_load(*args, **kwargs):
                if 'weights_only' not in kwargs: kwargs['weights_only'] = False
                return _original_load(*args, **kwargs)
            torch.load = _unsafe_load

            self.model = YOLO('yolov8n.pt')
            try:
                self.pose_model = YOLO('yolov8n-pose.pt')
                logger.info("✅ YOLO Pose model loaded")
            except: self.pose_model = None
            try:
                self.seg_model = YOLO('yolov8n-seg.pt')
                logger.info("✅ YOLO Segmentation model loaded")
            except: self.pose_model = None
            
            # 복구
            torch.load = _original_load
            
            self.initialized = True
            logger.info("✅ YOLO Fashion Detector initialized")
            return True
            
        except ImportError:
            logger.error("❌ ultralytics not installed.")
            return False
        except Exception as e:
            logger.error(f"❌ YOLO initialization failed: {e}")
            return False
    
    def detect_person(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        이미지에서 사람 감지
        """
        if not self.initialized:
            if not self.initialize(): return []
        
        try:
            # 🚨 [FIX] 4채널(RGBA) 이미지가 들어오면 3채널(RGB)로 변환
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # PIL -> numpy
            img_array = np.array(image)
            
            # YOLO 추론
            results = self.model(img_array, classes=[self.PERSON_CLASS_ID], verbose=False)
            
            persons = []
            for result in results:
                if result.boxes is None: continue
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    area = (x2 - x1) * (y2 - y1)
                    
                    persons.append({
                        "bbox": (int(x1), int(y1), int(x2), int(y2)),
                        "confidence": conf,
                        "area": area
                    })
            
            persons.sort(key=lambda x: x["area"], reverse=True)
            return persons
            
        except Exception as e:
            logger.error(f"❌ Person detection failed: {e}")
            return []
    
    def get_keypoints(self, image: Image.Image) -> Optional[Dict[str, Tuple[int, int]]]:
        if self.pose_model is None: return None
        try:
            # 🚨 [FIX] 포즈 추정 시에도 RGB 변환 확인
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            img_array = np.array(image)
            results = self.pose_model(img_array, verbose=False)
            
            KEYPOINT_NAMES = {5: "left_shoulder", 6: "right_shoulder", 11: "left_hip", 12: "right_hip"}
            for result in results:
                if result.keypoints is None: continue
                keypoints = result.keypoints.xy[0].tolist()
                kp_dict = {}
                for idx, name in KEYPOINT_NAMES.items():
                    if idx < len(keypoints):
                        x, y = keypoints[idx]
                        if x > 0 and y > 0: kp_dict[name] = (int(x), int(y))
                if kp_dict: return kp_dict
            return None
        except: return None
    
    def _crop_from_bbox(self, image: Image.Image, bbox: Tuple[int,int,int,int], target: str) -> Image.Image:
        x1, y1, x2, y2 = bbox
        w, h = image.size
        
        # Padding
        px = int((x2 - x1) * 0.1)
        py = int((y2 - y1) * 0.05)
        
        x1 = max(0, x1 - px)
        y1 = max(0, y1 - py)
        x2 = min(w, x2 + px)
        y2 = min(h, y2 + py)
        
        crop_box = (x1, y1, x2, y2)
        if target == "upper":
             crop_box = (x1, y1, x2, int(y1 + (y2-y1) * self.UPPER_RATIO))
        elif target == "lower":
             crop_box = (x1, int(y1 + (y2-y1) * (1 - self.LOWER_RATIO)), x2, y2)
             
        return image.crop(crop_box)

    def crop_fashion_regions(self, image: Image.Image, target: str = "full") -> Optional[Image.Image]:
        persons = self.detect_person(image)
        if not persons: return image
        return self._crop_from_bbox(image, persons[0]["bbox"], target)
    
    def extract_fashion_features(self, image: Image.Image) -> Dict[str, Optional[Image.Image]]:
        result = {"full": None, "upper": None, "lower": None}
        
        persons = self.detect_person(image)
        if not persons:
            result["full"] = image 
            return result
            
        main_bbox = persons[0]["bbox"]
        
        # 원본 이미지가 RGBA라면 여기서도 변환된 버전을 사용하는 게 안전하지만,
        # crop은 모드 상관없이 동작하므로 괜찮습니다.
        # 다만 detect_person 내부에서 변환된 이미지를 리턴하지 않으므로, 
        # 원본 image를 그대로 씁니다.
        
        result["full"] = self._crop_from_bbox(image, main_bbox, "full")
        result["upper"] = self._crop_from_bbox(image, main_bbox, "upper")
        result["lower"] = self._crop_from_bbox(image, main_bbox, "lower")
        
        return result
    
    # [추가] 가상 피팅용 마스크 생성 함수
    def generate_mask_for_fitting(self, image: Image.Image, target: str = "upper") -> Optional[Image.Image]:
        """
        YOLO Pose 기반의 정밀 마스킹
        - 얼굴 보호: Bounding Box 상단 13% 제외
        - 상/하의 분리: 골반(Hip) 좌표를 기준으로 동적 분리
        """
        if not self.initialized: self.initialize()
        if self.seg_model is None or self.pose_model is None: 
            return None

        try:
            if image.mode != "RGB": image = image.convert("RGB")
            w, h = image.size

            # 1. Segmentation 추론 (사람 모양 따기)
            seg_results = self.seg_model(image, classes=[0], verbose=False) # 0: Person

            final_mask = None
            person_box = None   # 사람 위치(박스) 저장용

            # 가장 큰 사람(주인공)의 마스크 찾기
            if seg_results and seg_results[0].masks:
                # 면적이 가장 큰 사람 선택
                masks = seg_results[0].masks.data.cpu().numpy()
                boxes = seg_results[0].boxes.xyxy.cpu().numpy()
                
                # (여러 명일 경우 가장 중앙에 있거나 큰 사람을 찾는 로직이 좋으나, 여기선 첫 번째 감지된 객체 사용)
                # 보통 YOLO는 confidence 순으로 정렬되어 있음
                mask_tensor = masks[0]
                person_box = boxes[0] # x1, y1, x2, y2

                # 마스크 리사이징 (YOLO 마스크 -> 원본 이미지 크기)
                final_mask = Image.fromarray((mask_tensor * 255).astype(np.uint8)).resize((w, h))
            
            if final_mask is None: return None

            draw = ImageDraw.Draw(final_mask)

            # 2. Pose 추론 (관절 위치 찾기)
            pose_results = self.pose_model(image, verbose=False)

            # 골반(Hip) 위치 찾기 (Keypoint Index : 11=Left Hip, 12=Right Hip)
            hip_y = int(h * 0.6)    # 기본값 : 못 찾으면 60% 지점 (Fallback)

            if pose_results and pose_results[0].keypoints is not None:
                # xy 좌표 가져오기
                keypoints = pose_results[0].keypoints.xy.cpu().numpy()[0]
                
                # 11번(왼쪽 골반), 12번(오른쪽 골반)이 존재하는지 확인
                # 좌표가 (0,0)이면 감지 안 된 것
                left_hip = keypoints[11]
                right_hip = keypoints[12]
                
                hips = []
                if left_hip[1] > 0: hips.append(left_hip[1])
                if right_hip[1] > 0: hips.append(right_hip[1])
                
                if hips:
                    # 두 골반의 평균 높이를 허리선으로 잡음 + 약간의 여유(10px)
                    hip_y = int(sum(hips) / len(hips)) + 10
                else:
                    # 골반이 안 보인다? = 상반신 클로즈업 사진일 확률 높음
                    # 이 경우 하단부를 자르지 않고 끝까지(100%) 옷으로 간주
                    hip_y = h
            
            # ---------------------------------------------------------
            # 🎨 마스킹 그리기 (검은색=보호 / 흰색=변경)
            # ---------------------------------------------------------
            
            # A. 머리 보호 로직
            # 코(Nose)와 어깨(Shoulder) 사이의 목 찾기
            head_limit = 0  # 기본값

            if pose_results and pose_results[0].keypoints is not None:
                keypoints = pose_results[0].keypoints.xy.cpu().numpy()[0]
                
                # Keypoint Index: 0=코, 5=왼쪽 어깨, 6=오른쪽 어깨
                nose = keypoints[0]
                left_shoulder = keypoints[5]
                right_shoulder = keypoints[6]
                
                # 1. 어깨 높이 평균 계산
                shoulder_y = 0
                if left_shoulder[1] > 0 and right_shoulder[1] > 0:
                    shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
                elif left_shoulder[1] > 0: shoulder_y = left_shoulder[1]
                elif right_shoulder[1] > 0: shoulder_y = right_shoulder[1]
                
                # 2. 코(Nose) 좌표가 있으면 -> "코와 어깨의 정중앙"을 자르는 선으로 설정
                if nose[1] > 0 and shoulder_y > 0:
                    # 코와 어깨 사이(목)의 중간 지점
                    head_limit = (nose[1] + shoulder_y) / 2
                    
                # 3. 코를 못 찾았으면(뒷모습 등) -> 어깨 너비를 기준으로 비례해서 위로 올림
                elif shoulder_y > 0:
                    # 어깨 너비 계산 (좌우 어깨가 다 있을 때)
                    if left_shoulder[0] > 0 and right_shoulder[0] > 0:
                        width = abs(left_shoulder[0] - right_shoulder[0])
                        # 어깨 너비의 50%만큼 위로 올리면 대략 목~머리 경계
                        head_limit = shoulder_y - (width * 0.5)
                    else:
                        # 어깨 너비도 모르면 기존 방식(박스 기준) Fallback
                        if person_box is not None:
                            head_limit = person_box[1] + ((person_box[3] - person_box[1]) * 0.13)
            
            # 안전장치: 혹시 계산된 라인이 0보다 작으면 0으로
            head_limit = max(0, int(head_limit))
            
            # 검은색 보호 영역 그리기
            draw.rectangle([(0, 0), (w, head_limit)], fill=0)

            # B. 상의/하의 영역 분리 (Pose 기반)
            if target == "upper":
                # 상의 피팅 -> 골반(hip_y) 아래쪽을 검은색으로 칠해서 하체 보호
                # 단, hip_y가 이미지 끝(h)이면 하체가 없는 것이므로 칠하지 않음
                if hip_y < h:
                    draw.rectangle([(0, hip_y), (w, h)], fill=0)

            elif target == "lower":
                # 하의 피팅 -> 골반(hip_y) 위쪽을 검은색으로 칠해서 상체 보호
                # (머리 보호 라인보다는 아래여야 함)
                start_y = max(int(head_limit), 0) if person_box is not None else 0
                draw.rectangle([(0, start_y), (w, hip_y)], fill=0)
            elif target == "full":
                # 드레스/전신 -> 머리만 보호하고 나머지는 유지
                pass
            
            return final_mask
        
        except Exception as e:
            logger.error(f"❌ Mask generation failed: {e}")
            return None

yolo_detector = YOLOFashionDetector()