# OPENROUTER

## Purpose
Call OpenRouter API to get AI responses with customizable models and parameters.

## Description
OPENROUTER是一个OpenRouter API调用工具，支持指定查询内容、模型、API密钥等参数，获取AI回复。支持多种免费模型，兼容RUN环境。

## Usage
```
OPENROUTER <query> [options]
OPENROUTER --list
OPENROUTER --default <model>
OPENROUTER --test-connection
```

### Arguments
- `query`: 查询内容 (必需，除非使用特殊选项)

### Options
- `--model <model>`: 指定模型 (默认: deepseek/deepseek-r1-distill-llama-70b)
- `--key <api_key>`: 指定API密钥 (覆盖环境变量)
- `--max-tokens <num>`: 最大token数 (默认: 4000)
- `--temperature <num>`: 温度参数 (默认: 0.7)
- `--output-dir <dir>`: 输出目录，保存模型回复到指定目录
- `--list`: 列出可用模型及其信息
- `--default <model>`: 设置默认模型
- `--test-connection`: 测试API连接状态，不发送查询
- `--help, -h`: 显示帮助信息

## Examples

### Basic Usage
```bash
# 基本用法
OPENROUTER "What is machine learning?"

# 指定模型
OPENROUTER "解释量子计算" --model "anthropic/claude-3-haiku"

# 指定API密钥和参数
OPENROUTER "Write a Python function" --key "sk-or-v1-..." --max-tokens 2000

# 调整温度参数
OPENROUTER "创建一个学习计划" --temperature 0.9
```

### Connection Testing
```bash
# 测试基本连接
OPENROUTER --test-connection

# 测试特定模型的可用性
OPENROUTER --test-connection --model "anthropic/claude-3-haiku"

# 测试自定义API密钥
OPENROUTER --test-connection --key "sk-or-v1-..."

# RUN模式下的连接测试（返回JSON）
RUN --show OPENROUTER --test-connection
```

### Model Management
```bash
# 列出所有可用模型
OPENROUTER --list

# 设置默认模型
OPENROUTER --default "google/gemini-2.5-flash-lite-preview-06-17"
```

### RUN Environment
```bash
# 在RUN环境中使用
RUN --show OPENROUTER "Explain neural networks" --model "meta-llama/llama-3.2-3b-instruct:free"
```

## Features
- **Cost Tracking**: Automatically displays token usage and cost information
- **Dynamic Token Limits**: Max tokens automatically adjusted to 1/4 of model's context length
- **Connection Testing**: Test API connectivity and model availability without making queries
- **Comprehensive Error Handling**: Detailed error messages for network, authentication, and API issues
- **Model Management**: List models, set default model, view pricing information
- **RUN Compatible**: Works seamlessly with RUN tool for JSON output

## Available Models
Use `OPENROUTER --list` to see all available models with pricing and context length information.
Current default model: `google/gemini-2.5-flash-lite-preview-06-17`

## Environment Variables
- `OPENROUTER_API_KEY`: 默认API密钥

## Version History
- v1.0: Initial release with basic functionality
- v1.1: Added cost tracking and dynamic token limits
- v1.2: Added --default option for model management

## Output Formats

### Normal Mode
直接输出AI回复内容到stdout，错误信息到stderr。

### RUN Mode
输出JSON格式结果：
```json
{
  "success": true,
  "message": "Success",
  "query": "What is machine learning?",
  "model": "deepseek/deepseek-r1-distill-llama-70b",
  "response": "Machine learning is...",
  "timestamp": "2025-01-17T15:30:00.000000"
}
```

## Error Handling
- API密钥缺失或无效
- 网络连接问题
- 请求超时 (60秒)
- 模型不可用
- 参数验证错误

## Integration
- **RUN兼容**: 支持 `RUN --show` 获取JSON格式输出
- **环境变量**: 自动读取 `OPENROUTER_API_KEY`
- **参数覆盖**: `--key` 参数可覆盖环境变量中的API密钥

## Features
- **多模型支持**: 支持OpenRouter平台的多种AI模型
- **参数可配置**: 可调整max_tokens、temperature等参数
- **错误处理**: 完善的错误处理和提示信息
- **双输出模式**: 支持普通模式和RUN JSON模式
- **免费模型**: 提供多个免费模型选择
- **超时控制**: 60秒请求超时保护 