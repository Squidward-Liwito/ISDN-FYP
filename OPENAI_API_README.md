# OpenAI Vision API 使用说明

## 功能描述
使用OpenAI GPT-4 Vision API分析selectedFrame目录中的图像，识别物体类型和数量。

## 安装依赖
```bash
pip install requests
```

## 获取API密钥
1. 访问 https://platform.openai.com/api-keys
2. 登录您的OpenAI账户
3. 创建新的API密钥
4. 复制密钥（只会显示一次）

## 使用方法

### 方法1: 运行时输入
```bash
cd /home/orangepi/Desktop/ISDN-FYP
python3 testOpenAIapi.py
```
程序会提示您输入API密钥

### 方法2: 使用环境变量
```bash
export OPENAI_API_KEY="your-api-key-here"
python3 testOpenAIapi.py
```

## 工作流程
1. 读取 `selectedFrame/` 目录中的所有图像
2. 对每张图像调用OpenAI Vision API
3. 使用提示词: "Identify the object type and quantity in this image..."
4. 显示分析结果
5. 将结果保存到 `api_results/` 目录

## 输出示例
```
======================================================================
OpenAI Vision API 图像分析工具
======================================================================
找到 3 张图像

[1/3]
正在分析: selected_01_frame_xxx.jpg
----------------------------------------------------------------------
正在发送请求到OpenAI API...

✓ 分析完成!

响应内容:
----------------------------------------------------------------------
In this image, I can see the following objects:
1. Orange - 3 pieces
2. Apple - 2 pieces
...
----------------------------------------------------------------------
```

## 费用说明
- 使用 GPT-4 Vision API 会产生费用
- 费用基于输入的token数量和图像大小
- 详情请查看: https://openai.com/pricing

## 注意事项
1. 需要有效的OpenAI API密钥
2. 确保账户有足够的余额
3. API请求可能需要几秒钟时间
4. 图像会被编码为base64发送
5. 结果会保存为JSON文件供后续分析

## 配置选项
可以在脚本中修改以下参数：
- `MODEL_NAME`: 使用的模型（默认: "gpt-4o"）
- `PROMPT`: 分析提示词
- `max_tokens`: 响应最大token数（默认: 500）

