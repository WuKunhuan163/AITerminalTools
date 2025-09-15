# IMG2TEXT

## Purpose
Convert images to structured text descriptions using Google Gemini Vision API.

## Description
图片转文字描述工具，支持Google Gemini Vision API，适用于学术图片、通用图片、代码截图等多种场景。支持交互模式和连接测试功能。

## Usage

### 基本用法
```
IMG2TEXT <image_path> [--mode academic|general|code_snippet] [--api google] [--output <file>]
```

### 交互模式
```
IMG2TEXT
```
无参数启动时进入交互模式，自动弹出文件选择对话框，并在图片同目录生成 `图片名_description.txt` 文件。

### 连接测试
```
IMG2TEXT --test-connection [--api google] [--key <api_key>]
```
测试API连接状态，不处理任何图片，用于诊断网络、地区限制等问题。

## Options
- `image_path`：图片文件路径
- `--mode`：分析模式（`academic` 学术图片，`general` 通用描述，`code_snippet` 代码识别）
- `--api`：API接口，当前仅支持`google`（默认）
- `--key`：手动指定API key，优先级高于环境变量
- `--prompt`：自定义分析指令，会覆盖默认的模式提示
- `--output`：将结果输出到指定文件
- `--output-dir`：输出结果到指定目录（自动生成文件名）
- `--test-connection`：测试API连接状态，不处理任何图片

## Examples

### 基本使用
```
IMG2TEXT example.png --mode academic
IMG2TEXT example.png --mode general --output result.txt
IMG2TEXT example.png --mode code_snippet
```

### 交互模式
```
IMG2TEXT
# 自动弹出文件选择对话框
# 自动生成 example_description.txt 文件
```

### 连接测试
```
IMG2TEXT --test-connection
# 输出：
# 🔍 API连接测试结果:
# FREE 密钥: 连接成功，找到视觉模型: models/gemini-1.0-pro-vision-latest
# PAID 密钥: 连接成功，找到视觉模型: models/gemini-1.0-pro-vision-latest
# 总结: 2/2 个密钥可用
```

### 自定义提示
```
IMG2TEXT diagram.png --prompt "请详细描述这个流程图中的每个步骤"
```

## RUN --show Support
在 RUN --show 环境下，工具会输出标准 JSON 结果，包含 success、message、result、image_path、api、reason 等字段，便于自动化集成。

```
RUN --show IMG2TEXT --test-connection
# 输出 JSON 格式的连接测试结果
```

## Error Handling
- 若 API 密钥无效或图片路径错误，支持详细错误原因输出。
- 支持自动回退免费/付费密钥。
- 交互模式下会自动测试API连接，失败时给出诊断建议。
- 连接测试功能可诊断网络问题、地区限制、API密钥问题等。

## Dependencies
- Python 3.8+
- `google-generativeai`, `Pillow`, `python-dotenv`
- 环境变量：`GOOGLE_API_KEY_FREE` 或 `GOOGLE_API_KEY_PAID`

## Typical Scenarios
- 学术论文图片自动解读
- 代码截图转文字
- 通用图片内容理解
- API连接状态诊断
- 批量图片处理（交互模式） 