#!/usr/bin/env python3
"""
视频帧捕获脚本
以5fps捕获3秒视频（共15帧），并保存到buffer目录
使用camera_settings.json中的相机配置
"""

import cv2
import time
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# 添加父目录到路径以便导入
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 从camera_tune.py导入相机设置和图像处理函数
from camera_tune import (
    load_settings,
    set_v4l2_control,
    apply_camera_hardware_settings,
    apply_image_processing
)


# ============================================
# 配置参数
# ============================================
CAPTURE_DURATION = 3  # 捕获持续时间（秒）
CAPTURE_FPS = 10  # 捕获帧率
TOTAL_FRAMES = CAPTURE_DURATION * CAPTURE_FPS  # 总帧数 = 30

# 目录配置
BASE_DIR = Path(__file__).parent.parent
BUFFER_DIR = BASE_DIR / 'buffer'


# ============================================
# 帧捕获函数
# ============================================
def capture_frames():
    """
    捕获视频帧并保存到buffer目录
    """
    print("="*70)
    print("视频帧捕获程序")
    print("="*70)
    print(f"捕获参数:")
    print(f"  - 持续时间: {CAPTURE_DURATION}秒")
    print(f"  - 帧率: {CAPTURE_FPS} fps")
    print(f"  - 总帧数: {TOTAL_FRAMES}帧")
    print(f"  - 保存目录: {BUFFER_DIR}")
    print("="*70)
    
    # 清理并重新创建buffer目录
    if BUFFER_DIR.exists():
        print(f"\n正在清理旧的buffer目录...")
        shutil.rmtree(BUFFER_DIR)
        print(f"✓ 已清理旧文件")
    
    BUFFER_DIR.mkdir(exist_ok=True)
    print(f"✓ Buffer目录已准备: {BUFFER_DIR}")
    
    # 加载相机设置（使用camera_tune.py的load_settings函数）
    config = load_settings()
    device = config.get('device', '/dev/video0')
    width = config.get('width', 640)
    height = config.get('height', 480)
    camera_fps = config.get('fps', 30)
    
    # 显示关键设置信息
    print(f"\n应用的图像处理设置:")
    print(f"  - 亮度偏移: {config.get('brightness_offset', 0)}")
    print(f"  - 对比度: {config.get('contrast', 1.0):.2f}")
    print(f"  - 饱和度: {config.get('saturation', 1.0):.2f}")
    print(f"  - 锐化: {config.get('sharpness', 0.0):.2f}")
    print(f"  - RGB增益: R={config.get('red_gain', 1.0):.2f}, G={config.get('green_gain', 1.0):.2f}, B={config.get('blue_gain', 1.0):.2f}")
    print(f"  - 降噪: {config.get('denoise', False)}")
    
    # 初始化相机
    print(f"\n正在打开相机: {device}")
    cap = cv2.VideoCapture(device)
    
    if not cap.isOpened():
        print("错误: 无法打开相机")
        return False
    
    # 设置相机参数
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, camera_fps)
    
    # 等待相机初始化
    time.sleep(0.5)
    
    # 应用硬件设置（使用camera_tune.py的函数）
    apply_camera_hardware_settings(config)
    
    # 预热相机（读取几帧并丢弃，让相机稳定）
    print("\n正在预热相机...")
    for i in range(10):
        ret, frame = cap.read()
        if ret:
            # 对预热帧也应用图像处理，让相机适应
            _ = apply_image_processing(frame, config)
        time.sleep(0.05)
    
    print("✓ 相机已准备就绪\n")
    
    # 开始捕获
    print("开始捕获帧...")
    print("提示: 捕获过程中会显示实时预览窗口")
    print("-"*70)
    
    captured_frames = []
    frame_interval = 1.0 / CAPTURE_FPS  # 每帧之间的时间间隔
    
    start_time = time.time()
    frame_count = 0
    
    # 创建预览窗口
    window_name = "捕获预览 (Capture Preview)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    # 设置窗口大小 (宽度, 高度)
    cv2.resizeWindow(window_name, 1280, 960)
    
    while frame_count < TOTAL_FRAMES:
        # 读取帧
        ret, frame = cap.read()
        if not ret:
            print(f"错误: 无法读取帧 #{frame_count + 1}")
            break
        
        # 应用图像处理
        processed_frame = apply_image_processing(frame, config)
        
        # 在图像上添加信息文本
        display_frame = processed_frame.copy()
        timestamp = time.time() - start_time
        
        # 添加捕获信息覆盖层
        text_lines = [
            f"捕获中: {frame_count + 1}/{TOTAL_FRAMES}",
            f"时间: {timestamp:.2f}s / {CAPTURE_DURATION}s",
            f"帧率: {CAPTURE_FPS} fps"
        ]
        
        y_offset = 30
        for i, text in enumerate(text_lines):
            cv2.putText(display_frame, text, (10, y_offset + i * 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
        
        # 显示预览
        cv2.imshow(window_name, display_frame)
        cv2.waitKey(1)  # 刷新显示
        
        # 保存帧信息
        captured_frames.append({
            'frame': processed_frame,
            'timestamp': timestamp,
            'frame_number': frame_count
        })
        
        print(f"✓ 捕获帧 {frame_count + 1}/{TOTAL_FRAMES} (时间: {timestamp:.3f}s)")
        
        frame_count += 1
        
        # 等待下一帧
        if frame_count < TOTAL_FRAMES:
            time.sleep(frame_interval)
    
    # 释放相机和关闭窗口
    cap.release()
    cv2.destroyAllWindows()
    
    print("-"*70)
    print(f"✓ 捕获完成! 共捕获 {len(captured_frames)} 帧")
    
    # 保存帧到buffer目录
    print(f"\n正在保存帧到 {BUFFER_DIR}...")
    session_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for i, frame_data in enumerate(captured_frames):
        filename = f"frame_{session_time}_{i:03d}.jpg"
        filepath = BUFFER_DIR / filename
        
        # 使用高质量参数保存图像 (JPEG质量95)
        success = cv2.imwrite(str(filepath), frame_data['frame'], 
                             [cv2.IMWRITE_JPEG_QUALITY, 95])
        if success:
            print(f"  ✓ 已保存: {filename}")
        else:
            print(f"  ✗ 保存失败: {filename}")
    
    print("\n" + "="*70)
    print("捕获任务完成!")
    print(f"保存位置: {BUFFER_DIR}")
    print(f"文件数量: {len(captured_frames)}")
    print("="*70)
    
    return True


# ============================================
# 主程序
# ============================================
def main():
    try:
        success = capture_frames()
        if success:
            print("\n程序执行成功")
            return 0
        else:
            print("\n程序执行失败")
            return 1
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        return 2
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

