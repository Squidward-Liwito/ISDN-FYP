import cv2
import mediapipe as mp
import numpy as np
from typing import Optional, Tuple


class HandDetector:
    """使用MediaPipe检测手部并分析手部状态"""
    
    def __init__(self, min_detection_confidence: float = 0.7, min_tracking_confidence: float = 0.5):
        """
        初始化手部检测器
        
        Args:
            min_detection_confidence: 手部检测的最小置信度
            min_tracking_confidence: 手部跟踪的最小置信度
        """
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
        self.last_detection_confidence = 0.0
        self.hand_count = 0
        self.hand_state = "UNKNOWN"
        self.last_finger_spread = 0.0
    
    def _analyze_hand_state(self, hand_landmarks) -> str:
        """
        基于手指张开程度分析手部是否为空或持有物体
        
        Args:
            hand_landmarks: MediaPipe手部关键点
            
        Returns:
            "EMPTY" 如果手指张开, "HOLDING" 如果抓握
        """
        landmarks = hand_landmarks.landmark
        
        # 获取五个指尖的坐标
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        ring_tip = landmarks[16]
        pinky_tip = landmarks[20]
        palm_base = landmarks[0]
        
        # 计算所有指尖之间的距离
        distances = []
        fingertips = [thumb_tip, index_tip, middle_tip, ring_tip, pinky_tip]
        
        for i in range(len(fingertips)):
            for j in range(i + 1, len(fingertips)):
                dist = np.sqrt(
                    (fingertips[i].x - fingertips[j].x) ** 2 +
                    (fingertips[i].y - fingertips[j].y) ** 2
                )
                distances.append(dist)
        
        # 计算平均张开程度
        avg_spread = np.mean(distances)
        self.last_finger_spread = avg_spread
        
        # 根据张开程度判断手部状态
        return "EMPTY" if avg_spread > 0.15 else "HOLDING"
    
    def detect(self, frame: np.ndarray) -> Tuple[bool, np.ndarray, int, str, float]:
        """
        检测手部并分析手部状态
        
        Args:
            frame: 输入的BGR图像
            
        Returns:
            (hand_detected, annotated_frame, hand_count, hand_state, confidence)
            - hand_detected: 是否检测到手部
            - annotated_frame: 带标注的图像
            - hand_count: 检测到的手部数量
            - hand_state: 手部状态 ("EMPTY", "HOLDING", "UNKNOWN")
            - confidence: 检测置信度
        """
        if frame is None:
            return False, frame, 0, "UNKNOWN", 0.0
        
        # 转换为RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        annotated_frame = frame.copy()
        hand_detected = False
        hand_count = 0
        
        if results.multi_hand_landmarks:
            hand_detected = True
            hand_count = len(results.multi_hand_landmarks)
            
            # 绘制手部关键点
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    annotated_frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style()
                )
            
            # 分析第一只手的状态
            self.hand_state = self._analyze_hand_state(results.multi_hand_landmarks[0])
            
            # 获取置信度
            if results.multi_handedness:
                confidences = [hand.classification[0].score for hand in results.multi_handedness]
                self.last_detection_confidence = sum(confidences) / len(confidences)
        else:
            self.last_detection_confidence = 0.0
            self.hand_state = "UNKNOWN"
        
        self.hand_count = hand_count
        return hand_detected, annotated_frame, hand_count, self.hand_state, self.last_detection_confidence
    
    def get_confidence(self) -> float:
        """返回上一帧的检测置信度"""
        return self.last_detection_confidence
    
    def get_hand_state(self) -> str:
        """返回当前手部状态: "EMPTY", "HOLDING", 或 "UNKNOWN" """
        return self.hand_state
    
    def close(self):
        """释放资源"""
        self.hands.close()

