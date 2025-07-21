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
            "message": "❌ 连接测试失败：未设置API密钥",
            "results": [{
                "test": "API密钥检查",
                "status": "error",
                "message": "❌ 连接测试失败：未设置API密钥"
            }],
            "summary": {
                "total_tests": 1,
                "successful": 0,
                "warnings": 0,
                "errors": 1
            },
            "details": "请设置环境变量OPENROUTER_API_KEY或使用--key参数"
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
                "test": "模型列表获取",
                "status": "success",
                "message": f"✅ 成功获取 {model_count} 个可用模型"
            })
            
            # 如果指定了特定模型，检查其可用性
            if model:
                available_models = [m['id'] for m in models_data.get('data', [])]
                if model in available_models:
                    results.append({
                        "test": f"模型 {model} 可用性",
                        "status": "success", 
                        "message": f"✅ 模型 {model} 可用"
                    })
                else:
                    results.append({
                        "test": f"模型 {model} 可用性",
                        "status": "warning",
                        "message": f"⚠️  模型 {model} 不在可用列表中"
                    })
                    
        elif response.status_code == 401:
            results.append({
                "test": "API认证",
                "status": "error",
                "message": "❌ API密钥无效或已过期"
            })
        elif response.status_code == 429:
            results.append({
                "test": "API限制",
                "status": "warning",
                "message": "⚠️  请求过于频繁，请稍后再试"
            })
        else:
            results.append({
                "test": "API连接",
                "status": "error",
                "message": f"❌ API请求失败: HTTP {response.status_code}"
            })
            
    except requests.exceptions.Timeout:
        results.append({
            "test": "网络连接",
            "status": "error", 
            "message": "❌ 连接超时，请检查网络连接"
        })
    except requests.exceptions.ConnectionError:
        results.append({
            "test": "网络连接",
            "status": "error",
            "message": "❌ 无法连接到OpenRouter服务器"
        })
    except Exception as e:
        results.append({
            "test": "未知错误",
            "status": "error",
            "message": f"❌ 连接测试失败: {str(e)}"
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
                    "test": "API调用测试",
                    "status": "success",
                    "message": f"✅ 成功调用模型 {test_model}"
                })
            elif api_response.status_code == 402:
                results.append({
                    "test": "API调用测试",
                    "status": "warning",
                    "message": "⚠️  账户余额不足或需要付费"
                })
            else:
                error_data = api_response.json() if api_response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('error', {}).get('message', f"HTTP {api_response.status_code}")
                results.append({
                    "test": "API调用测试",
                    "status": "error",
                    "message": f"❌ API调用失败: {error_msg}"
                })
                
        except Exception as e:
            results.append({
                "test": "API调用测试",
                "status": "error",
                "message": f"❌ API调用测试失败: {str(e)}"
            })
    
    # 生成总结
    success_count = sum(1 for r in results if r["status"] == "success")
    total_count = len(results)
    overall_success = success_count > 0 and not any(r["status"] == "error" for r in results)
    
    return {
        "success": overall_success,
        "message": f"连接测试完成: {success_count}/{total_count} 项成功",
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
            print(f"⚠️  加载模型配置失败: {e}", file=sys.stderr)
    
    return get_default_models()


def save_models(models: Dict[str, Dict[str, Any]]) -> bool:
    """保存模型列表（新格式）"""
    try:
        MODELS_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MODELS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'models': models}, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存模型列表失败: {e}", file=sys.stderr)
        return False


def set_default_model(model_id: str) -> bool:
    """设置默认模型（将指定模型移到列表最上方）"""
    models = load_models()
    
    if model_id not in models:
        print(f"❌ 模型 '{model_id}' 不存在", file=sys.stderr)
        return False
    
    # 创建新的有序字典，将指定模型放在最前面
    new_models = {model_id: models[model_id]}
    
    # 添加其他模型
    for mid, info in models.items():
        if mid != model_id:
            new_models[mid] = info
    
    if save_models(new_models):
        print(f"✅ 已将 '{model_id}' 设置为默认模型")
        return True
    else:
        print(f"❌ 设置默认模型失败", file=sys.stderr)
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
        print("📋 可用模型列表:")
        print("=" * 40)
        for i, model_id in enumerate(useable_models, 1):
            info = models[model_id]
            input_cost = info.get('input_cost_per_1m', 0)
            output_cost = info.get('output_cost_per_1m', 0)
            context_length = info.get('context_length', 0)
            
            print(f"{i:2d}. {model_id}")
            print(f"    📊 费率: 输入 ${input_cost:.2f}/1M, 输出 ${output_cost:.2f}/1M")
            print(f"    📏 上下文长度: {context_length:,} tokens")
            print()
        
        print(f"总计: {len(useable_models)} 个可用模型")
        print(f"默认模型: {useable_models[0] if useable_models else '无'}")


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
        print(f"⚠️  指定的max_tokens ({max_tokens}) 超过建议值 ({suggested_max_tokens})，已调整", file=sys.stderr)
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
        print(f"🤖 调用OpenRouter API...", file=sys.stderr)
        print(f"📝 模型: {model}", file=sys.stderr)
        print(f"🔢 最大tokens: {max_tokens}", file=sys.stderr)
        print(f"🌡️  温度: {temperature}", file=sys.stderr)
        
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
            
            print(f"✅ API调用成功", file=sys.stderr)
            print(f"📊 Token使用: 输入 {input_tokens}, 输出 {output_tokens}, 总计 {total_tokens}", file=sys.stderr)
            print(f"💰 费用: ${cost:.6f}", file=sys.stderr)
            
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
    help_text = f"""OPENROUTER - OpenRouter API 调用工具

Usage: OPENROUTER <query> [options]
       OPENROUTER --list
       OPENROUTER --default <model>
       OPENROUTER --test-connection

Options:
  <query>                查询内容
  --model <model>        指定模型 (默认使用第一个可用模型)
  --key <api_key>        指定API密钥 (临时使用)
  --max-tokens <num>     最大token数 (默认: 根据模型自动调整为上下文长度的1/4)
  --temperature <float>  温度参数 (默认: 0.7)
  --output-dir <dir>     输出目录，保存模型回复到指定目录
  --list                 列出所有可用模型
  --default <model>      设置默认模型（将指定模型移到列表最上方）
  --test-connection      测试API连接状态，不发送查询
  --help                 显示帮助信息

Examples:
  OPENROUTER "What is machine learning?"
  OPENROUTER "解释量子计算" --model "deepseek/deepseek-r1:free"
  OPENROUTER "Write a Python function" --key "sk-or-v1-..." --max-tokens 2000
  OPENROUTER "创建一个学习计划" --temperature 0.9

  OPENROUTER --list
  OPENROUTER --default "deepseek/deepseek-chat"
  OPENROUTER --test-connection
  OPENROUTER --test-connection --model "deepseek/deepseek-chat" --key "sk-or-v1-..."

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
    parser.add_argument('--output-dir', help='输出目录，保存模型回复到指定目录')
    parser.add_argument('--test-connection', action='store_true', help='测试API连接状态，不发送查询')
    parser.add_argument('--help', action='store_true', help='显示帮助信息')
    
    args = parser.parse_args()
    
    # 显示帮助信息
    if args.help or (not args.query and not args.list and not args.default and not args.test_connection):
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
    
    # 测试连接
    if args.test_connection:
        result = test_connection(args.key, args.model)
        
        # 检查是否在RUN环境中
        if is_run_environment():
            # RUN模式：输出JSON
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 普通模式：输出格式化文本
            print("🔍 OpenRouter API连接测试结果:")
            print()
            
            for test_result in result["results"]:
                print(f"📊 {test_result['test']}: {test_result['message']}")
            
            print()
            summary = result["summary"]
            if result["success"]:
                print(f"✅ 总结: 连接测试成功 - {summary['successful']}/{summary['total_tests']} 项通过")
                if summary['warnings'] > 0:
                    print(f"⚠️  警告: {summary['warnings']} 项需要注意")
            else:
                print(f"❌ 总结: 连接测试失败 - {summary['errors']} 个错误, {summary['warnings']} 个警告")
                
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
                print(f"❌ 无法读取文件 {file_path}: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            query_content = args.query
    else:
        # 如果没有提供query参数，尝试从stdin读取
        if not sys.stdin.isatty():
            try:
                query_content = sys.stdin.read().strip()
                if not query_content:
                    print("❌ 从stdin读取的内容为空", file=sys.stderr)
                    sys.exit(1)
            except Exception as e:
                print(f"❌ 从stdin读取内容失败: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print("❌ 没有提供查询内容", file=sys.stderr)
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
            print(f"💾 回复已保存到: {output_file}", file=sys.stderr)
            
        except Exception as e:
            print(f"⚠️  保存到输出目录失败: {e}", file=sys.stderr)
    
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
            print(f"❌ 错误: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main() 