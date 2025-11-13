#!/usr/bin/env python3
"""
OpenAI Vision API 测试脚本
读取selectedFrame目录中的图像，使用GPT-4 Vision识别物体类型和数量
"""

import os
import base64
import json
from pathlib import Path
from typing import List, Dict
import requests


# ============================================
# 配置参数
# ============================================
BASE_DIR = Path(__file__).parent
SELECTED_DIR = BASE_DIR / 'selectedFrame'
RESULTS_DIR = BASE_DIR / 'api_results'

# OpenAI API配置
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MODEL_NAME = "gpt-4o"  # 或 "gpt-4-turbo" 如果你有访问权限

# 识别提示词
PROMPT = "Identify the object type and quantity in this image. Please provide a detailed description of what objects you see and how many of each."


# ============================================
# 辅助函数
# ============================================
def encode_image_to_base64(image_path: Path) -> str:
    """将图像编码为base64字符串"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def get_api_credentials() -> tuple:
    """获取用户输入的API凭证"""
    print("="*70)
    print("OpenAI API 凭证配置")
    print("="*70)
    
    # 检查环境变量
    api_key = os.getenv('OPENAI_API_KEY')
    
    if api_key:
        print(f"✓ 检测到环境变量 OPENAI_API_KEY")
        use_env = input("是否使用环境变量中的API密钥? (y/n): ").strip().lower()
        if use_env == 'y':
            return api_key
    
    # 手动输入
    print("\n请输入您的OpenAI API密钥:")
    print("(可以从 https://platform.openai.com/api-keys 获取)")
    api_key = input("API Key: ").strip()
    
    if not api_key:
        raise ValueError("API密钥不能为空")
    
    return api_key


def analyze_image_with_openai(image_path: Path, api_key: str, prompt: str) -> Dict:
    """
    使用OpenAI Vision API分析图像
    
    Args:
        image_path: 图像文件路径
        api_key: OpenAI API密钥
        prompt: 分析提示词
    
    Returns:
        API响应结果
    """
    print(f"\n正在分析: {image_path.name}")
    print("-"*70)
    
    # 编码图像
    base64_image = encode_image_to_base64(image_path)
    
    # 构建请求
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 500
    }
    
    try:
        # 发送请求
        print("正在发送请求到OpenAI API...")
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        # 提取响应内容
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            print(f"\n✓ 分析完成!")
            print(f"\n响应内容:")
            print("-"*70)
            print(content)
            print("-"*70)
            
            return {
                'success': True,
                'image': image_path.name,
                'response': content,
                'model': result.get('model', MODEL_NAME),
                'usage': result.get('usage', {})
            }
        else:
            print("✗ API响应格式异常")
            return {
                'success': False,
                'image': image_path.name,
                'error': 'Invalid response format',
                'raw_response': result
            }
            
    except requests.exceptions.RequestException as e:
        print(f"\n✗ 请求失败: {e}")
        if hasattr(e.response, 'text'):
            print(f"错误详情: {e.response.text}")
        return {
            'success': False,
            'image': image_path.name,
            'error': str(e)
        }


def save_results(results: List[Dict], output_dir: Path):
    """保存分析结果到JSON文件"""
    output_dir.mkdir(exist_ok=True)
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"analysis_results_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ 结果已保存到: {output_file}")


def display_summary(results: List[Dict]):
    """显示分析结果摘要"""
    print("\n" + "="*70)
    print("分析结果摘要")
    print("="*70)
    
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print(f"总图像数: {len(results)}")
    print(f"成功分析: {successful}")
    print(f"失败数量: {failed}")
    
    # 显示token使用情况
    total_tokens = sum(r.get('usage', {}).get('total_tokens', 0) for r in results if r['success'])
    if total_tokens > 0:
        print(f"总Token使用: {total_tokens}")
    
    print("="*70)


# ============================================
# 主程序
# ============================================
def main():
    """主程序入口"""
    print("="*70)
    print("OpenAI Vision API 图像分析工具")
    print("="*70)
    print(f"分析目录: {SELECTED_DIR}")
    print(f"提示词: {PROMPT}")
    print("="*70)
    
    try:
        # 检查图像目录
        if not SELECTED_DIR.exists():
            print(f"\n错误: 目录不存在: {SELECTED_DIR}")
            print("请先运行 image_selection.py 生成选中的图像")
            return 1
        
        # 获取所有图像文件
        image_files = sorted(list(SELECTED_DIR.glob('*.jpg')))
        
        if not image_files:
            print(f"\n错误: {SELECTED_DIR} 目录中没有找到图像")
            return 1
        
        print(f"\n找到 {len(image_files)} 张图像")
        
        # 获取API凭证
        api_key = get_api_credentials()
        
        print("\n" + "="*70)
        print("开始分析图像")
        print("="*70)
        
        # 分析每张图像
        results = []
        for i, image_path in enumerate(image_files, 1):
            print(f"\n[{i}/{len(image_files)}]")
            result = analyze_image_with_openai(image_path, api_key, PROMPT)
            results.append(result)
        
        # 保存结果
        save_results(results, RESULTS_DIR)
        
        # 显示摘要
        display_summary(results)
        
        print("\n程序执行成功!")
        return 0
        
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

