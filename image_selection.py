#!/usr/bin/env python3
"""
图像选择模块
从buffer目录中选择清晰度最高的前3张图像并保存到selectedFrame目录
"""

import cv2
import os
import sys
import shutil
from pathlib import Path
from typing import List, Tuple

# 添加分析模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入模糊检测器
from analysis.blur_detector import BlurDetector


# ============================================
# 配置参数
# ============================================
BASE_DIR = Path(__file__).parent
BUFFER_DIR = BASE_DIR / 'capture' / 'buffer'
SELECTED_DIR = BASE_DIR / 'selectedFrame'
TOP_N = 3  # 选择前3张最清晰的图像


# ============================================
# 图像选择函数
# ============================================
def select_best_frames(buffer_dir: Path, output_dir: Path, top_n: int = 3) -> List[Tuple[str, float]]:
    """
    从buffer目录中选择清晰度最高的前N张图像
    
    Args:
        buffer_dir: 输入图像目录
        output_dir: 输出目录
        top_n: 选择前N张图像
    
    Returns:
        选中的图像列表 [(文件名, 清晰度分数), ...]
    """
    print("="*70)
    print("图像选择程序 - 基于清晰度评分")
    print("="*70)
    print(f"输入目录: {buffer_dir}")
    print(f"输出目录: {output_dir}")
    print(f"选择数量: 前 {top_n} 张最清晰的图像")
    print("="*70)
    
    # 检查buffer目录是否存在
    if not buffer_dir.exists():
        print(f"\n错误: Buffer目录不存在: {buffer_dir}")
        return []
    
    # 获取所有图像文件
    image_files = sorted([f for f in buffer_dir.glob('*.jpg')])
    
    if not image_files:
        print(f"\n错误: Buffer目录中没有找到图像文件")
        return []
    
    print(f"\n找到 {len(image_files)} 张图像")
    print("-"*70)
    
    # 计算每张图像的清晰度分数
    print("正在计算清晰度分数...")
    image_scores = []
    
    for i, image_path in enumerate(image_files):
        # 读取图像
        frame = cv2.imread(str(image_path))
        
        if frame is None:
            print(f"  ⚠ 警告: 无法读取图像 {image_path.name}")
            continue
        
        # 计算清晰度分数
        blur_score = BlurDetector.calculate_blur_score(frame)
        image_scores.append((image_path, blur_score))
        
        print(f"  [{i+1:2d}/{len(image_files)}] {image_path.name}: 分数 = {blur_score:.2f}")
    
    if not image_scores:
        print("\n错误: 没有成功计算出任何图像的清晰度分数")
        return []
    
    print("-"*70)
    
    # 按分数排序（分数越高越清晰）
    image_scores.sort(key=lambda x: x[1], reverse=True)
    
    # 选择前N张
    selected = image_scores[:top_n]
    
    print(f"\n✓ 已选择前 {len(selected)} 张最清晰的图像:")
    for i, (path, score) in enumerate(selected, 1):
        print(f"  {i}. {path.name} - 分数: {score:.2f}")
    
    # 清理并创建输出目录
    if output_dir.exists():
        print(f"\n正在清理旧的输出目录...")
        shutil.rmtree(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓ 输出目录已准备: {output_dir}")
    
    # 保存选中的图像
    print("\n正在保存选中的图像...")
    saved_files = []
    
    for i, (image_path, score) in enumerate(selected, 1):
        # 读取图像
        frame = cv2.imread(str(image_path))
        
        if frame is not None:
            # 创建新的文件名
            output_filename = f"selected_{i:02d}_{image_path.name}"
            output_path = output_dir / output_filename
            
            # 保存图像（高质量）
            success = cv2.imwrite(str(output_path), frame, 
                                 [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            if success:
                print(f"  ✓ 已保存: {output_filename} (分数: {score:.2f})")
                saved_files.append((output_filename, score))
            else:
                print(f"  ✗ 保存失败: {output_filename}")
    
    print("\n" + "="*70)
    print("图像选择完成!")
    print(f"总图像数: {len(image_files)}")
    print(f"已选择: {len(saved_files)} 张")
    print(f"保存位置: {output_dir}")
    print("="*70)
    
    return saved_files


def display_score_statistics(buffer_dir: Path):
    """显示所有图像的清晰度统计信息"""
    print("\n" + "="*70)
    print("清晰度统计")
    print("="*70)
    
    image_files = sorted([f for f in buffer_dir.glob('*.jpg')])
    
    if not image_files:
        print("没有图像文件")
        return
    
    scores = []
    for image_path in image_files:
        frame = cv2.imread(str(image_path))
        if frame is not None:
            score = BlurDetector.calculate_blur_score(frame)
            scores.append(score)
    
    if scores:
        print(f"图像数量: {len(scores)}")
        print(f"平均分数: {sum(scores)/len(scores):.2f}")
        print(f"最高分数: {max(scores):.2f}")
        print(f"最低分数: {min(scores):.2f}")
        print(f"分数范围: {max(scores) - min(scores):.2f}")
        print("="*70)


# ============================================
# 主程序
# ============================================
def main():
    """主程序入口"""
    try:
        # 选择最佳帧
        selected_files = select_best_frames(BUFFER_DIR, SELECTED_DIR, TOP_N)
        
        # 显示统计信息
        if BUFFER_DIR.exists():
            display_score_statistics(BUFFER_DIR)
        
        if selected_files:
            print("\n程序执行成功!")
            return 0
        else:
            print("\n程序执行失败: 没有选择任何图像")
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

