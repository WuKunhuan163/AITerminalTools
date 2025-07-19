# IMG2TEXT

## Purpose
Convert images to structured text descriptions using Google Gemini Vision API.

## Description
图片转文字描述工具，支持Google Gemini Vision API，适用于学术图片、通用图片、代码截图等多种场景。

## Usage
```
IMG2TEXT <image_path> [--mode academic|general|code_snippet] [--api google] [--output <file>]
```
- `image_path`：图片文件路径
- `--mode`：分析模式（`academic` 学术图片，`general` 通用描述，`code_snippet` 代码识别）
- `--api`：API接口，当前仅支持`google`（默认）
- `--output`：将结果输出到指定文件

## Examples
```
IMG2TEXT example.png --mode academic
IMG2TEXT example.png --mode general --output result.txt
IMG2TEXT example.png --mode code_snippet
```

## RUN --show Support
在 RUN --show 环境下，工具会输出标准 JSON 结果，包含 success、message、result、image_path、api、reason 等字段，便于自动化集成。

## Error Handling
- 若 API 密钥无效或图片路径错误，支持详细错误原因输出。
- 支持自动回退免费/付费密钥。

## Dependencies
- Python 3.8+
- `google-generativeai`, `Pillow`, `python-dotenv`
- 环境变量：`GOOGLE_API_KEY_FREE` 或 `GOOGLE_API_KEY_PAID`

## Typical Scenarios
- 学术论文图片自动解读
- 代码截图转文字
- 通用图片内容理解 