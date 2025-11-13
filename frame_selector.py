#!/usr/bin/env python3
"""
基于模糊度和手部姿态的帧选择器
整合相机捕获、模糊检测和手部检测功能
"""

import cv2
import subprocess
import time
import numpy as np
import json
import os
from blur_detector import BlurDetector
from hand_detector import HandDetector

# ============================================
# 相机配置
# ============================================
CAMERA_CONFIG = {
    'device': '/dev/video0',
    'width': 640,
    'height': 480,
    'fps': 30,
    'auto_exposure': 1,
    'exposure': 800,
    'analogue_gain': 112,
    'white_balance_auto': 0,
    'brightness_offset': 15,
    'contrast': 1.4,
    'saturation': 1.1,
    'sharpness': 0.0,
    'red_gain': 1.0,
    'green_gain': 1.0,
    'blue_gain': 1.0,
    'denoise': False,
}

# 帧选择配置
FRAME_SELECTION_CONFIG = {
    'blur_threshold': 100.0,  # 模糊度阈值
    'hand_confidence_threshold': 0.7,  # 手部检测置信度阈值
    'target_hand_state': 'EMPTY',  # 目标手部状态: 'EMPTY' 或 'HOLDING'
    'buffer_size': 30,  # 保留最近N帧用于比较
}

SETTINGS_FILE = './camera_settings.json'

# ============================================
# 相机控制函数 (从camera_tune.py复用)
# ============================================

def load_settings():
    """从JSON文件加载相机设置"""
    if not os.path.exists(SETTINGS_FILE):
        print("未找到保存的设置,使用默认值")
        return CAMERA_CONFIG.copy()
    
    try:
        with open(SETTINGS_FILE, 'r') as f:
            saved_settings = json.load(f)
        
        config = CAMERA_CONFIG.copy()
        config.update(saved_settings)
        
        print(f"✓ 从 {SETTINGS_FILE} 加载设置")
        return config
    except Exception as e:
        print(f"警告: 加载设置失败: {e}")
        return CAMERA_CONFIG.copy()


def set_v4l2_control(device, control, value):
    """使用v4l2-ctl设置相机控制参数"""
    try:
        subprocess.run(['v4l2-ctl', '-d', device, f'--set-ctrl={control}={value}'], 
                      check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"警告: 设置 {control}={value} 失败: {e.stderr}")
        return False


def apply_camera_hardware_settings(config):
    """应用硬件相机设置"""
    device = config['device']
    
    print("正在应用硬件相机设置...")
    
    set_v4l2_control(device, 'auto_exposure', config['auto_exposure'])
    time.sleep(0.1)
    
    set_v4l2_control(device, 'exposure', config['exposure'])
    set_v4l2_control(device, 'analogue_gain', config['analogue_gain'])
    set_v4l2_control(device, 'white_balance_automatic', config['white_balance_auto'])
    
    print("✓ 硬件设置已应用")


def adjust_brightness_contrast(image, brightness=0, contrast=1.0):
    """调整亮度和对比度"""
    if brightness != 0:
        if brightness > 0:
            shadow = brightness
            highlight = 255
        else:
            shadow = 0
            highlight = 255 + brightness
        alpha_b = (highlight - shadow) / 255
        gamma_b = shadow
        image = cv2.addWeighted(image, alpha_b, image, 0, gamma_b)
    
    if contrast != 1.0:
        image = cv2.convertScaleAbs(image, alpha=contrast, beta=0)
    
    return image


def adjust_saturation(image, saturation=1.0):
    """调整色彩饱和度"""
    if saturation == 1.0:
        return image
    
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = hsv[:, :, 1] * saturation
    hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def adjust_rgb_channels(image, red_gain=1.0, green_gain=1.0, blue_gain=1.0):
    """调整RGB通道增益"""
    if red_gain == 1.0 and green_gain == 1.0 and blue_gain == 1.0:
        return image
    
    b, g, r = cv2.split(image.astype(np.float32))
    
    r = np.clip(r * red_gain, 0, 255)
    g = np.clip(g * green_gain, 0, 255)
    b = np.clip(b * blue_gain, 0, 255)
    
    result = cv2.merge([b, g, r]).astype(np.uint8)
    return result


def apply_image_processing(frame, config):
    """应用所有软件图像处理"""
    frame = adjust_brightness_contrast(frame, 
                                       config['brightness_offset'], 
                                       config['contrast'])
    
    frame = adjust_saturation(frame, config['saturation'])
    
    frame = adjust_rgb_channels(frame, 
                               config['red_gain'], 
                               config['green_gain'], 
                               config['blue_gain'])
    
    if config['denoise']:
        frame = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)
    
    return frame


# ============================================
# 帧选择器类
# ============================================

class FrameSelector:
    """基于模糊度和手部姿态选择最佳帧"""
    
    def __init__(self, config):
        self.config = config
        self.blur_detector = BlurDetector()
        self.hand_detector = HandDetector(
            min_detection_confidence=config['hand_confidence_threshold']
        )
        
        # 帧缓冲区
        self.frame_buffer = []
        self.max_buffer_size = config['buffer_size']
        
        # 最佳帧
        self.best_frame = None
        self.best_score = -1
        
    def calculate_frame_score(self, frame, blur_score, hand_detected, hand_state, hand_confidence):
        """
        计算帧的综合评分
        
        评分标准:
        - 模糊度越高(越清晰)越好
        - 检测到手部且置信度高越好
        - 手部状态符合目标状态越好
        """
        score = 0.0
        
        # 模糊度分数 (权重: 50%)
        blur_weight = 0.5
        score += blur_score * blur_weight
        
        # 手部检测分数 (权重: 50%)
        hand_weight = 0.5
        if hand_detected:
            # 置信度分数
            score += hand_confidence * 100 * hand_weight * 0.5
            
            # 手部状态匹配分数
            if hand_state == self.config['target_hand_state']:
                score += 100 * hand_weight * 0.5
        
        return score
    
    def process_frame(self, frame):
        """
        处理单个帧并更新最佳帧
        
        Returns:
            (annotated_frame, blur_score, hand_detected, hand_state, hand_confidence, frame_score)
        """
        # 计算模糊度
        blur_score = self.blur_detector.calculate_blur_score(frame)
        is_blurry = blur_score < self.config['blur_threshold']
        
        # 检测手部
        hand_detected, annotated_frame, hand_count, hand_state, hand_confidence = \
            self.hand_detector.detect(frame)
        
        # 计算综合评分
        frame_score = self.calculate_frame_score(
            frame, blur_score, hand_detected, hand_state, hand_confidence
        )
        
        # 更新最佳帧
        if frame_score > self.best_score:
            self.best_score = frame_score
            self.best_frame = frame.copy()
        
        # 添加信息到显示帧
        self._add_info_overlay(
            annotated_frame, blur_score, is_blurry, 
            hand_detected, hand_state, hand_confidence, frame_score
        )
        
        return annotated_frame, blur_score, hand_detected, hand_state, hand_confidence, frame_score
    
    def _add_info_overlay(self, frame, blur_score, is_blurry, hand_detected, 
                          hand_state, hand_confidence, frame_score):
        """在帧上添加信息叠加层"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        y_offset = 30
        
        # 模糊度信息
        blur_color = (0, 0, 255) if is_blurry else (0, 255, 0)
        blur_text = f"模糊度: {blur_score:.1f} {'[模糊]' if is_blurry else '[清晰]'}"
        cv2.putText(frame, blur_text, (10, y_offset), font, font_scale, blur_color, thickness)
        
        # 手部检测信息
        y_offset += 35
        if hand_detected:
            hand_text = f"手部: {hand_state} (置信度: {hand_confidence:.2f})"
            hand_color = (0, 255, 0) if hand_state == self.config['target_hand_state'] else (0, 165, 255)
        else:
            hand_text = "手部: 未检测到"
            hand_color = (0, 0, 255)
        cv2.putText(frame, hand_text, (10, y_offset), font, font_scale, hand_color, thickness)
        
        # 综合评分
        y_offset += 35
        score_text = f"帧评分: {frame_score:.1f}"
        cv2.putText(frame, score_text, (10, y_offset), font, font_scale, (255, 255, 0), thickness)
        
        # 最佳评分
        y_offset += 35
        best_text = f"最佳评分: {self.best_score:.1f}"
        cv2.putText(frame, best_text, (10, y_offset), font, font_scale, (255, 0, 255), thickness)
        
        # 帮助信息
        y_offset += 50
        help_text = "按 'S' 保存最佳帧 | 按 'Q' 退出"
        cv2.putText(frame, help_text, (10, y_offset), font, 0.5, (255, 255, 255), 1)
    
    def save_best_frame(self, output_path='best_frame.jpg'):
        """保存最佳帧"""
        if self.best_frame is not None:
            cv2.imwrite(output_path, self.best_frame)
            print(f"\n✓ 最佳帧已保存到: {output_path}")
            print(f"  最佳评分: {self.best_score:.1f}")
            return True
        else:
            print("\n✗ 没有可保存的最佳帧")
            return False
    
    def close(self):
        """释放资源"""
        self.hand_detector.close()


# ============================================
# 主程序
# ============================================

def main():
    print("="*70)
    print("帧选择器 - 基于模糊度和手部姿态")
    print("="*70)
    
    # 加载相机设置
    camera_config = load_settings()
    
    # 初始化相机
    print(f"\n正在打开相机: {camera_config['device']}")
    cap = cv2.VideoCapture(camera_config['device'])
    
    if not cap.isOpened():
        print("错误: 无法打开相机")
        return
    
    # 设置分辨率
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_config['width'])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_config['height'])
    cap.set(cv2.CAP_PROP_FPS, camera_config['fps'])
    
    time.sleep(0.5)
    
    # 应用硬件设置
    apply_camera_hardware_settings(camera_config)
    
    # 初始化帧选择器
    frame_selector = FrameSelector(FRAME_SELECTION_CONFIG)
    
    print("\n开始处理帧...")
    print(f"- 模糊度阈值: {FRAME_SELECTION_CONFIG['blur_threshold']}")
    print(f"- 目标手部状态: {FRAME_SELECTION_CONFIG['target_hand_state']}")
    print(f"- 手部置信度阈值: {FRAME_SELECTION_CONFIG['hand_confidence_threshold']}")
    print("\n按 'S' 保存最佳帧 | 按 'Q' 退出\n")
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("错误: 无法捕获帧")
            break
        
        # 应用图像处理
        processed_frame = apply_image_processing(frame, camera_config)
        
        # 处理帧(模糊度检测 + 手部检测)
        display_frame, blur_score, hand_detected, hand_state, hand_confidence, frame_score = \
            frame_selector.process_frame(processed_frame)
        
        frame_count += 1
        
        # 显示帧
        cv2.imshow('帧选择器', display_frame)
        
        # 处理键盘输入
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q') or key == ord('Q'):
            break
        elif key == ord('s') or key == ord('S'):
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = f'best_frame_{timestamp}.jpg'
            frame_selector.save_best_frame(output_path)
    
    # 清理
    print(f"\n总共处理了 {frame_count} 帧")
    cap.release()
    cv2.destroyAllWindows()
    frame_selector.close()
    print("程序结束")


if __name__ == "__main__":
    main()

