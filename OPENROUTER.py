#!/usr/bin/env python3
"""
OPENROUTER.py - OpenRouter API 调用工具
支持指定查询、模型、API密钥等参数，获取AI回复
修改版本：支持新的模型数据结构，包含费率和context length信息
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def is_run_environment(command_identifier=None):
    """Check if running in RUN environment by checking environment variables"""
    if command_identifier:
        return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
    # 检查通用的RUN环境变量
    return bool(os.environ.get('RUN_DATA_FILE') or os.environ.get('RUN_IDENTIFIER'))

# 模型配置文件路径
MODELS_CONFIG_FILE = Path(__file__).parent / "OPENROUTER_PROJ" / "openrouter_models.json"


def get_default_models() -> Dict[str, Dict[str, Any]]:
    """获取默认模型列表（从配置文件或硬编码）"""
    # 尝试从配置文件加载
    if MODELS_CONFIG_FILE.exists():
        try:
            with open(MODELS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                models = data.get('models', {})
                if models:
                    return models
        except Exception:
            pass
    
    # 如果配置文件不存在或为空，返回硬编码的默认模型
    return {
        "deepseek/deepseek-v3-base:free": {
            "input_cost_per_1m": 0,
            "output_cost_per_1m": 0,
            "context_length": 163840,
            "useable": True
        },
        "deepseek/deepseek-r1:free": {
            "input_cost_per_1m": 0,
            "output_cost_per_1m": 0,
            "context_length": 163840,
            "useable": True
        },
        "meta-llama/llama-3.2-3b-instruct:free": {
            "input_cost_per_1m": 0,
            "output_cost_per_1m": 0,
            "context_length": 131072,
            "useable": True
        }
    }


def test_connection(api_key=None, model=None):
    """测试OpenRouter API连接状态"""
    # 获取API密钥
    if api_key:
        test_api_key = api_key
    else:
        test_api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not test_api_key:
        return {
            "success": False,
            "message": "Error: Connection test failed: API key not set",
            "results": [{
                "test": "API key check",
                "status": "error",
                "message": "Error: Connection test failed: API key not set"
            }],
            "summary": {
                "total_tests": 1,
                "successful": 0,
                "warnings": 0,
                "errors": 1
            },
            "details": "Please set the environment variable OPENROUTER_API_KEY or use the --key parameter"
        }
    
    results = []
    
    # 准备API请求头
    headers = {
        "Authorization": f"Bearer {test_api_key}",
        "HTTP-Referer": "https://github.com/your-app",
        "X-Title": "OPENROUTER Test Connection"
    }
    
    # 测试API连接和模型列表获取
    try:
        # 测试基本连接：获取模型列表
        response = requests.get("https://openrouter.ai/api/v1/models", headers=headers, timeout=10)
        
        if response.status_code == 200:
            models_data = response.json()
            model_count = len(models_data.get('data', []))
            results.append({
                "test": "Model list retrieval",
                "status": "success",
                "message": f"Successfully retrieved {model_count} available models"
            })
            
            # 如果指定了特定模型，检查其可用性
            if model:
                available_models = [m['id'] for m in models_data.get('data', [])]
                if model in available_models:
                    results.append({
                        "test": f"Model {model} availability",
                        "status": "success", 
                        "message": f"Model {model} available"
                    })
                else:
                    results.append({
                        "test": f"Model {model} availability",
                        "status": "warning",
                        "message": f"Warning: Model {model} is not in the available list"
                    })
                    
        elif response.status_code == 401:
            results.append({
                "test": "API authentication",
                "status": "error",
                "message": "API key invalid or expired"
            })
        elif response.status_code == 429:
            results.append({
                "test": "API limit",
                "status": "warning",
                "message": "Request too frequent, please try again later"
            })
        else:
            results.append({
                "test": "API connection",
                "status": "error",
                "message": f"Error: API request failed: HTTP {response.status_code}"
            })
            
    except requests.exceptions.Timeout:
        results.append({
            "test": "Network connection",
            "status": "error", 
            "message": "Error: Connection timeout, please check the network connection"
        })
    except requests.exceptions.ConnectionError:
        results.append({
            "test": "Network connection",
            "status": "error",
            "message": "Error: Unable to connect to OpenRouter server"
        })
    except Exception as e:
        results.append({
            "test": "Unknown error",
            "status": "error",
            "message": f"Error: Connection test failed: {str(e)}"
        })
    
    # 如果连接成功，可以测试一个简单的API调用
    if results and results[0]["status"] == "success":
        try:
            test_model = model if model else "deepseek/deepseek-chat:free"
            test_payload = {
                "model": test_model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 5
            }
            
            api_response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=test_payload,
                timeout=15
            )
            
            if api_response.status_code == 200:
                results.append({
                    "test": "API call test",
                    "status": "success",
                    "message": f"Successfully called model {test_model}"
                })
            elif api_response.status_code == 402:
                results.append({
                    "test": "API call test",
                    "status": "warning",
                    "message": "Warning: Account balance insufficient or needs to be paid"
                })
            else:
                error_data = api_response.json() if api_response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('error', {}).get('message', f"HTTP {api_response.status_code}")
                results.append({
                    "test": "API call test",
                    "status": "error",
                    "message": f"Error: API call failed: {error_msg}"
                })
                
        except Exception as e:
            results.append({
                "test": "API call test",
                "status": "error",
                "message": f"Error: API call test failed: {str(e)}"
            })
    
    # 生成总结
    success_count = sum(1 for r in results if r["status"] == "success")
    total_count = len(results)
    overall_success = success_count > 0 and not any(r["status"] == "error" for r in results)
    
    return {
        "success": overall_success,
        "message": f"Connection test completed: {success_count}/{total_count} successful",
        "results": results,
        "summary": {
            "total_tests": total_count,
            "successful": success_count,
            "warnings": sum(1 for r in results if r["status"] == "warning"),
            "errors": sum(1 for r in results if r["status"] == "error")
        }
    }


def load_models() -> Dict[str, Dict[str, Any]]:
    """加载模型列表（新格式）"""
    if MODELS_CONFIG_FILE.exists():
        try:
            with open(MODELS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                models = data.get('models', {})
                
                # 检查是否是旧格式（列表）
                if isinstance(models, list):
                    # 转换旧格式到新格式
                    new_models = {}
                    for model_id in models:
                        new_models[model_id] = {
                            "input_cost_per_1m": 0,
                            "output_cost_per_1m": 0,
                            "context_length": 0,
                            "useable": False
                        }
                    return new_models
                
                return models
        except Exception as e:
            print(f"Warning: Loading model configuration failed: {e}", file=sys.stderr)
    
    return get_default_models()


def save_models(models: Dict[str, Dict[str, Any]]) -> bool:
    """保存模型列表（新格式）"""
    try:
        MODELS_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MODELS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'models': models}, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Saving model list failed: {e}", file=sys.stderr)
        return False


def set_default_model(model_ids_str: str) -> bool:
    """设置默认模型（支持多个模型ID，将指定模型按顺序移到列表最前面）"""
    models = load_models()
    
    # 解析模型ID列表（支持逗号或空格分隔）
    import re
    model_ids = re.split(r'[,\s]+', model_ids_str.strip())
    model_ids = [mid.strip() for mid in model_ids if mid.strip()]
    
    if not model_ids:
        print(f"Error: No valid model ID provided", file=sys.stderr)
        return False
    
    # 检查每个模型是否存在
    existing_models = []
    missing_models = []
    
    for model_id in model_ids:
        if model_id in models:
            existing_models.append(model_id)
        else:
            missing_models.append(model_id)
    
    # 警告不存在的模型
    if missing_models:
        print(f"Warning: The following models do not exist in the list: {', '.join(missing_models)}")
    
    if not existing_models:
        print(f"Error: No valid models found", file=sys.stderr)
        return False
    
    # 创建新的有序字典
    new_models = {}
    
    # 1. 先按指定顺序添加存在的模型
    for model_id in existing_models:
        new_models[model_id] = models[model_id]
    
    # 2. 然后添加其他未指定的模型，保持它们的原有相对顺序
    for model_id, info in models.items():
        if model_id not in existing_models:
            new_models[model_id] = info
    
    if save_models(new_models):
        if len(existing_models) == 1:
            print(f"{existing_models[0]} set as default model")
        else:
            print(f"Set priority models in order: {' -> '.join(existing_models)}")
            print(f"New default model: {existing_models[0]}")
        return True
    else:
        print(f"Error: Setting default model failed", file=sys.stderr)
        return False


def test_model_availability(model_id: str, api_key: str = None) -> Dict[str, Any]:
    """测试模型是否可用"""
    # 获取API密钥
    test_api_key = api_key or os.getenv("OPENROUTER_API_KEY")
    
    if not test_api_key:
        return {
            "success": False,
            "message": "Error: API key is required to test models",
            "error": "missing_api_key"
        }
    
    headers = {
        "Authorization": f"Bearer {test_api_key}",
        "HTTP-Referer": "https://github.com/openrouter-test",
        "X-Title": "OPENROUTER Model Test"
    }
    
    # 测试模型调用
    test_payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Hello, please respond with 'OK'"}],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=test_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                return {
                    "success": True,
                    "message": f"Model {model_id} test successful",
                    "response": result['choices'][0]['message']['content'].strip()
                }
            else:
                return {
                    "success": False,
                    "message": f"Error: Model {model_id} returned an abnormal format",
                    "error": "invalid_response_format"
                }
        elif response.status_code == 404:
            return {
                "success": False,
                "message": f"Error: Model {model_id} does not exist",
                "error": "model_not_found"
            }
        elif response.status_code == 402:
            return {
                "success": False,
                "message": f"Error: Account balance insufficient or model requires payment",
                "error": "payment_required"
            }
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            error_msg = error_data.get('error', {}).get('message', f"HTTP {response.status_code}")
            return {
                "success": False,
                "message": f"Error: Model {model_id} test failed: {error_msg}",
                "error": "api_error"
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": f"Error: Model {model_id} test timeout",
            "error": "timeout"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: Model {model_id} test error: {str(e)}",
            "error": "unknown_error"
        }


def add_model(model_id: str, api_key: str = None) -> bool:
    """添加新模型到列表（先测试可用性）"""
    models = load_models()
    
    if model_id in models:
        print(f"Warning: Model {model_id} already exists in the list")
        return False
    
    print(f"Testing the availability of model {model_id}...")
    
    # 测试模型
    test_result = test_model_availability(model_id, api_key)
    
    if not test_result["success"]:
        print(test_result["message"])
        return False
    
    print(test_result["message"])
    
    # 尝试获取模型的详细信息
    try:
        # 获取模型列表以获取详细信息
        test_api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        headers = {
            "Authorization": f"Bearer {test_api_key}",
            "HTTP-Referer": "https://github.com/openrouter-test",
            "X-Title": "OPENROUTER Model Info"
        }
        
        response = requests.get("https://openrouter.ai/api/v1/models", headers=headers, timeout=15)
        
        model_info = {
            "input_cost_per_1m": 0.0,
            "output_cost_per_1m": 0.0,
            "context_length": 4000,
            "useable": True
        }
        
        if response.status_code == 200:
            models_data = response.json()
            for model_data in models_data.get('data', []):
                if model_data.get('id') == model_id:
                    pricing = model_data.get('pricing', {})
                    model_info.update({
                        "input_cost_per_1m": float(pricing.get('prompt', '0')) * 1000000,
                        "output_cost_per_1m": float(pricing.get('completion', '0')) * 1000000,
                        "context_length": model_data.get('context_length', 4000),
                        "useable": True
                    })
                    break
    
    except Exception as e:
        print(f"Warning: Unable to get model details, using default values: {e}")
    
    # 添加到模型列表
    models[model_id] = model_info
    
    if save_models(models):
        print(f"Successfully added model {model_id} to the list")
        print(f"Rate: input ${model_info['input_cost_per_1m']:.2f}/1M, output ${model_info['output_cost_per_1m']:.2f}/1M")
        print(f"Context length: {model_info['context_length']:,} tokens")
        return True
    else:
        print(f"Error: Adding model failed")
        return False


def remove_model(model_id: str) -> bool:
    """从列表中移除模型"""
    models = load_models()
    
    if model_id not in models:
        print(f"Error: Model {model_id} does not exist in the list")
        return False
    
    # 删除模型
    del models[model_id]
    
    if save_models(models):
        print(f"Removed model {model_id} from the list")
        return True
    else:
        print(f"Error: Removing model failed")
        return False


def get_useable_models() -> List[str]:
    """获取可用模型列表"""
    models = load_models()
    return [model_id for model_id, info in models.items() if info.get('useable', False)]


def get_model_info(model_id: str) -> Optional[Dict[str, Any]]:
    """获取模型信息"""
    models = load_models()
    return models.get(model_id)


def get_suggested_max_tokens(model_id: str, user_max_tokens: Optional[int] = None) -> int:
    """根据模型的context length建议合适的max tokens（1/4安全值）"""
    """Suggest appropriate max tokens based on the model's context length (1/4 safety value)"""
    model_info = get_model_info(model_id)
    if not model_info:
        return user_max_tokens or 1000
    
    context_length = model_info.get('context_length', 4000)
    
    # 计算建议的max tokens（上下文长度的1/4，为输入和输出各留1/4空间）
    suggested_tokens = max(100, context_length // 4)
    
    # 如果用户指定了max_tokens，使用较小的值
    if user_max_tokens:
        return min(user_max_tokens, suggested_tokens)
    
    return suggested_tokens

def write_to_json_output(data, command_identifier=None):
    """将结果写入到指定的 JSON 输出文件中"""
    if not is_run_environment(command_identifier):
        return False
    
    # Get the specific output file for this command identifier
    if command_identifier:
        output_file = os.environ.get(f'RUN_DATA_FILE_{command_identifier}')
    else:
        output_file = os.environ.get('RUN_DATA_FILE')
    
    if not output_file:
        return False
    
    try:
        from pathlib import Path
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing to JSON output file: {e}")
        return False


def create_json_output(success: bool, message: str, **kwargs) -> Dict[str, Any]:
    """创建标准JSON输出格式"""
    return {
        "success": success,
        "message": message,
        "timestamp": __import__('datetime').datetime.now().isoformat(),
        **kwargs
    }


def list_models():
    """列出所有可用模型"""
    models = load_models()
    useable_models = get_useable_models()
    
    if is_run_environment():
        # 在RUN环境下返回JSON格式的模型列表（只返回可用模型）
        model_data = create_json_output(
            True, 
            "Command executed successfully", 
            models=useable_models,
            total_count=len(useable_models),
            default_model=useable_models[0] if useable_models else None,
            model_details={model_id: models[model_id] for model_id in useable_models}
        )
        
        if 'RUN_DATA_FILE' in os.environ:
            with open(os.environ['RUN_DATA_FILE'], 'w', encoding='utf-8') as f:
                json.dump(model_data, f, ensure_ascii=False, indent=2)
        
        print(json.dumps(model_data, ensure_ascii=False, indent=2))
    else:
        # 在普通环境下显示格式化的模型列表（只显示可用模型）
        print(f"Available models list:")
        print(f"=" * 40)
        for i, model_id in enumerate(useable_models, 1):
            info = models[model_id]
            input_cost = info.get('input_cost_per_1m', 0)
            output_cost = info.get('output_cost_per_1m', 0)
            context_length = info.get('context_length', 0)
            
            print(f"{i:2d}. {model_id}")
            print(f"    Rate: input ${input_cost:.2f}/1M, output ${output_cost:.2f}/1M")
            print(f"    Context length: {context_length:,} tokens")
            print()
        
        print(f"Total: {len(useable_models)} available models")
        print(f"Default model: {useable_models[0] if useable_models else 'None'}")


def calculate_cost(input_tokens: int, output_tokens: int, model_id: str) -> float:
    """计算API调用费用"""
    model_info = get_model_info(model_id)
    if not model_info:
        return 0.0
    
    input_cost = (input_tokens / 1000000) * model_info.get('input_cost_per_1m', 0)
    output_cost = (output_tokens / 1000000) * model_info.get('output_cost_per_1m', 0)
    
    return input_cost + output_cost


def call_openrouter_api(query: str, model: str = None, api_key: str = None, max_tokens: int = None, temperature: float = 0.7, output_dir: str = None, command_identifier: str = None) -> Union[str, Dict[str, Any]]:
    """
    调用OpenRouter API获取回复
    
    Args:
        query: 查询内容
        model: 模型名称
        api_key: API密钥
        max_tokens: 最大token数（None时自动根据模型context length调整）
        temperature: 温度参数
        
    Returns:
        包含回复内容和元数据的字典
    """
    # 获取API密钥
    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        return {
            "success": False,
            "error": "No API key provided. Use --update-key to set API key, set OPENROUTER_API_KEY environment variable, or use --key parameter"
        }
    
    # 获取模型
    if not model:
        useable_models = get_useable_models()
        if not useable_models:
            return {
                "success": False,
                "error": "No useable models available. Please run update_openrouter_models.py to update model information."
            }
        model = useable_models[0]
    
    # 检查模型是否可用
    model_info = get_model_info(model)
    if not model_info or not model_info.get('useable', False):
        return {
            "success": False,
            "error": f"Model '{model}' is not available or not useable"
        }
    
    # 动态调整max_tokens
    suggested_max_tokens = get_suggested_max_tokens(model, max_tokens)
    if max_tokens is None:
        max_tokens = suggested_max_tokens
    elif max_tokens > suggested_max_tokens:
        print(f"Warning: Specified max_tokens ({max_tokens}) exceeds the recommended value ({suggested_max_tokens}), adjusted", file=sys.stderr)
        max_tokens = suggested_max_tokens
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": query}],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        print(f"Calling OpenRouter API...", file=sys.stderr)
        print(f"Model: {model}, max tokens: {max_tokens}, temperature: {temperature}", file=sys.stderr)
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            
            # 获取token使用信息
            usage = result.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)
            
            # 计算费用
            cost = calculate_cost(input_tokens, output_tokens, model)
            
            print(f"API call successful", file=sys.stderr)
            print(f"Token usage: input {input_tokens}, output {output_tokens}, total {total_tokens}", file=sys.stderr)
            print(f"Cost: ${cost:.6f}", file=sys.stderr)
            
            return {
                "success": True,
                "content": content,
                "model": model,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens
                },
                "cost": cost,
                "model_info": model_info
            }
        else:
            return {
                "success": False,
                "error": "No response content received"
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"API request failed: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def main():
    """主函数"""
    help_text = f"""OPENROUTER - OpenRouter API calling tool

Usage: OPENROUTER <query> [options]
       OPENROUTER --list
       OPENROUTER --default <model1> [model2] [model3] ...
       OPENROUTER --add <model> [--temp-key <api_key>]
       OPENROUTER --remove <model>
       OPENROUTER --test-connection

Options:
  <query>                查询内容
  --model <model>        指定模型 (默认使用第一个可用模型)
  --key <api_key>        指定API密钥 (临时使用)
  --max-tokens <num>     最大token数 (默认: 根据模型自动调整为上下文长度的1/4)
  --temperature <float>  温度参数 (默认: 0.7)
  --output-dir <dir>     输出目录，保存模型回复到指定目录
  --list                 列出所有可用模型
  --default <models>     设置默认模型优先级（支持多个模型，用逗号或空格分隔）
  --add <model>          添加新模型到列表（先测试连接）
  --remove <model>       从列表中移除模型
  --temp-key <api_key>   临时API密钥（用于测试新模型）
  --test-connection      测试API连接状态，不发送查询
  --help                 显示帮助信息

Examples:
  OPENROUTER "What is machine learning?"
  OPENROUTER "解释量子计算" --model "deepseek/deepseek-r1:free"
  OPENROUTER "Write a Python function" --key "sk-or-v1-..." --max-tokens 2000
  OPENROUTER "创建一个学习计划" --temperature 0.9

  OPENROUTER --list
  OPENROUTER --default "qwen/qwen3-235b-a22b-07-25:free"
  OPENROUTER --default "qwen/qwen3-235b-a22b-07-25:free,google/gemini-2.5-flash-lite-preview-06-17"
  OPENROUTER --default "model1 model2 model3"
  OPENROUTER --add "qwen/qwen3-235b-a22b-07-25:free"
  OPENROUTER --add "moonshotai/kimi-k2:free" --temp-key "sk-or-v1-..."
  OPENROUTER --remove "old-model"
  OPENROUTER --test-connection

Environment Variables:
  OPENROUTER_API_KEY    默认API密钥

Note: 只有标记为可用(useable=true)的模型才会显示在列表中。
      运行 fetch_openrouter_models.py 来更新模型信息和费率。
"""

    parser = argparse.ArgumentParser(description="OpenRouter API 调用工具", add_help=False)
    parser.add_argument('query', nargs='?', help='查询内容')
    parser.add_argument('--model', help='指定模型')
    parser.add_argument('--key', help='指定API密钥')
    parser.add_argument('--max-tokens', type=int, default=None, help='最大token数（默认根据模型自动调整）')
    parser.add_argument('--temperature', type=float, default=0.7, help='温度参数')
    parser.add_argument('--list', action='store_true', help='列出所有可用模型')
    parser.add_argument('--default', help='设置默认模型')
    parser.add_argument('--add', help='添加新模型到列表（先测试连接）')
    parser.add_argument('--remove', help='从列表中移除模型')
    parser.add_argument('--temp-key', help='临时API密钥（用于测试新模型）')
    parser.add_argument('--output-dir', help='输出目录，保存模型回复到指定目录')
    parser.add_argument('--test-connection', action='store_true', help='测试API连接状态，不发送查询')
    parser.add_argument('--help', action='store_true', help='显示帮助信息')
    
    args = parser.parse_args()
    
    # 显示帮助信息
    if args.help or (not args.query and not args.list and not args.default and not args.add and not args.remove and not args.test_connection):
        print(help_text)
        return
    
    # 列出模型
    if args.list:
        list_models()
        return
    
    # 设置默认模型
    if args.default:
        success = set_default_model(args.default)
        sys.exit(0 if success else 1)
    
    # 添加模型
    if args.add:
        success = add_model(args.add, args.temp_key)
        sys.exit(0 if success else 1)
    
    # 移除模型
    if args.remove:
        success = remove_model(args.remove)
        sys.exit(0 if success else 1)
    
    # 测试连接
    if args.test_connection:
        result = test_connection(args.key, args.model)
        
        # 检查是否在RUN环境中
        if is_run_environment():
            # RUN模式：输出JSON
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 普通模式：输出格式化文本
            print(f"OpenRouter API connection test results:")
            print()
            
            for test_result in result["results"]:
                print(f"{test_result['test']}: {test_result['message']}")
            
            print()
            summary = result["summary"]
            if result["success"]:
                print(f"Summary: connection test successful - {summary['successful']}/{summary['total_tests']} passed")
                if summary['warnings'] > 0:
                    print(f"Warning: {summary['warnings']} items need attention")
            else:
                print(f"Error: Summary: connection test failed - {summary['errors']} errors, {summary['warnings']} warnings")
                
        return
    
    # 调用API
    if args.query:
        # 检查是否是文件路径（以@开头）
        if args.query.startswith('@'):
            file_path = args.query[1:]  # 移除@前缀
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    query_content = f.read()
            except Exception as e:
                print(f"Error: Unable to read file {file_path}: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            query_content = args.query
    else:
        # 如果没有提供query参数，尝试从stdin读取
        if not sys.stdin.isatty():
            try:
                query_content = sys.stdin.read().strip()
                if not query_content:
                    print(f"Error: Content read from stdin is empty", file=sys.stderr)
                    sys.exit(1)
            except Exception as e:
                print(f"Error: Failed to read content from stdin: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Error: No query content provided", file=sys.stderr)
            sys.exit(1)
    
    result = call_openrouter_api(
        query_content,
        args.model,
        args.key,
        args.max_tokens,
        args.temperature
    )
    
    # 处理--output-dir功能
    if result['success'] and args.output_dir:
        try:
            from pathlib import Path
            import datetime
            
            output_path = Path(args.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名：openrouter_YYYYMMDD_HHMMSS.txt
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_path / f"openrouter_{timestamp}.txt"
            
            # 写入回复内容和元数据
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Query: {query_content}\n")
                f.write(f"Model: {result.get('model', 'unknown')}\n")
                f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
                f.write(f"Cost: ${result.get('cost', 0):.6f}\n")
                f.write(f"Tokens: {result.get('usage', {}).get('total_tokens', 0)}\n")
                f.write("-" * 50 + "\n\n")
                f.write(result['content'])
            
            result['output_file'] = str(output_file)
            print(f"Reply saved to: {output_file}", file=sys.stderr)
            
        except Exception as e:
            print(f"Warning: Saving to output directory failed: {e}", file=sys.stderr)
    
    if is_run_environment():
        # 在RUN环境下输出JSON格式
        if 'RUN_DATA_FILE' in os.environ:
            with open(os.environ['RUN_DATA_FILE'], 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 在普通环境下输出格式化结果
        if result['success']:
            print(result['content'])
        else:
            print(f"Error: Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main() 