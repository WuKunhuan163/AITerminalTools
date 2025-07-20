#!/usr/bin/env python3
"""
IMG2TEXT - Python Entrypoint
图片转文字描述工具的Python入口脚本
"""

import os
import sys
import argparse
from pathlib import Path
import google.generativeai as genai
from google.api_core import exceptions
from PIL import Image
import json
import datetime

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def is_run_environment(command_identifier=None):
    """Check if running in RUN environment by checking environment variables"""
    # Check for general RUN environment
    if os.environ.get('RUN_IDENTIFIER'):
        return True
    # Check for specific command identifier (legacy support)
    if command_identifier:
        return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
    return False

def create_json_output(success, message, result=None, image_path=None, api=None, reason=None):
    return {
        "success": success,
        "message": message,
        "result": result,
        "image_path": image_path,
        "api": api,
        "reason": reason,
        "timestamp": datetime.datetime.now().isoformat()
    }

def _generate_unique_output_path(image_path_obj: Path) -> Path:
    """
    生成唯一的输出文件路径，避免文件名冲突
    
    Args:
        image_path_obj: 图片文件的Path对象
        
    Returns:
        唯一的输出文件路径
    """
    base_name = f"{image_path_obj.stem}_description"
    extension = ".txt"
    parent_dir = image_path_obj.parent
    
    # 首先尝试不带编号的文件名
    output_path = parent_dir / f"{base_name}{extension}"
    if not output_path.exists():
        return output_path
    
    # 如果文件已存在，添加编号
    counter = 1
    while True:
        output_path = parent_dir / f"{base_name}_{counter}{extension}"
        if not output_path.exists():
            return output_path
        counter += 1
        # 防止无限循环，最多尝试1000次
        if counter > 1000:
            raise RuntimeError("无法生成唯一的输出文件名")

def test_connection(api: str = "google", key: str = None, command_identifier: str = None) -> str:
    """
    测试API连接状态，不处理任何图片
    
    Args:
        api: API接口 (目前仅支持google)
        key: 用户手动指定的API key，优先级最高
        command_identifier: RUN环境标识符
        
    Returns:
        连接测试结果（文本或JSON）
    """
    # 检查和加载密钥
    if key:
        api_keys = {"USER": key}
    else:
        api_keys = {
            "FREE": os.getenv("GOOGLE_API_KEY_FREE"),
            "PAID": os.getenv("GOOGLE_API_KEY_PAID")
        }
    
    if not any(api_keys.values()):
        reason = "API调用错误：环境变量 GOOGLE_API_KEY_FREE 或 GOOGLE_API_KEY_PAID 未设置，且未通过--key指定。"
        if is_run_environment():
            output = create_json_output(False, "No valid API key", None, None, api, reason)
            return json.dumps(output, ensure_ascii=False)
        return f"❌ 连接测试失败：{reason}"
    
    # 测试每个可用的API密钥
    results = []
    for key_name, api_key in api_keys.items():
        if not api_key:
            continue
            
        try:
            # 配置Google API
            genai.configure(api_key=api_key)
            
            # 尝试列出可用模型（这是一个轻量级的API调用，通常免费）
            try:
                models = list(genai.list_models())
                # 查找支持视觉的模型
                vision_models = [m for m in models if 'vision' in m.name.lower() or 'gemini-1.5' in m.name.lower() or 'gemini-pro-vision' in m.name.lower()]
                
                if vision_models:
                    model_name = vision_models[0].name
                    results.append({
                        "key_type": key_name,
                        "status": "success",
                        "message": f"✅ 连接成功，找到视觉模型: {model_name}",
                        "model": model_name
                    })
                else:
                    results.append({
                        "key_type": key_name,
                        "status": "warning", 
                        "message": f"⚠️  连接成功但未找到视觉模型，找到 {len(models)} 个模型",
                        "model_count": len(models)
                    })
                    
            except exceptions.PermissionDenied as e:
                results.append({
                    "key_type": key_name,
                    "status": "error",
                    "message": f"❌ 权限被拒绝: {str(e)}",
                    "error_type": "permission_denied"
                })
            except exceptions.Forbidden as e:
                # 通常是地区限制
                results.append({
                    "key_type": key_name,
                    "status": "error", 
                    "message": f"❌ 访问被禁止（可能是地区限制）: {str(e)}",
                    "error_type": "region_restriction"
                })
            except Exception as e:
                results.append({
                    "key_type": key_name,
                    "status": "error",
                    "message": f"❌ API调用失败: {str(e)}",
                    "error_type": "api_error"
                })
                
        except Exception as e:
            results.append({
                "key_type": key_name,
                "status": "error",
                "message": f"❌ 连接失败: {str(e)}",
                "error_type": "connection_error"
            })
    
    # 生成结果报告
    if is_run_environment():
        # RUN模式：返回JSON
        success = any(r["status"] == "success" for r in results)
        output = create_json_output(
            success, 
            "Connection test completed" if success else "All connection tests failed",
            results,
            None,
            api,
            None if success else "所有API密钥测试失败"
        )
        return json.dumps(output, ensure_ascii=False)
    else:
        # 普通模式：返回格式化文本
        report = ["🔍 API连接测试结果:", ""]
        
        for result in results:
            report.append(f"📊 {result['key_type']} 密钥: {result['message']}")
        
        report.append("")
        success_count = sum(1 for r in results if r["status"] == "success")
        if success_count > 0:
            report.append(f"✅ 总结: {success_count}/{len(results)} 个密钥可用")
        else:
            report.append(f"❌ 总结: 所有 {len(results)} 个密钥都无法使用")
            
        return "\n".join(report)

def get_image_analysis(image_path: str, mode: str = "general", api: str = "google", key: str = None, custom_prompt: str = None, command_identifier: str = None) -> str:
    """
    调用指定API分析图片，支持Google Gemini Vision。
    Args:
        image_path: 图片文件路径
        mode: 分析模式 ("academic", "general", "code_snippet")
        api: API接口 (目前仅支持google)
        key: 用户手动指定的API key，优先级最高
    Returns:
        分析结果文本或JSON（RUN --show模式）
    """
    # 检查和加载密钥
    if key:
        api_keys = {"USER": key}
    else:
        api_keys = {
            "FREE": os.getenv("GOOGLE_API_KEY_FREE"),
            "PAID": os.getenv("GOOGLE_API_KEY_PAID")
        }
    if not any(api_keys.values()):
        reason = "API调用错误：环境变量 GOOGLE_API_KEY_FREE 或 GOOGLE_API_KEY_PAID 未设置，且未通过--key指定。"
        if is_run_environment():
            output = create_json_output(False, "No valid API key", None, image_path, api, reason)
            with open(os.environ['RUN_DATA_FILE'], 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            return json.dumps(output, ensure_ascii=False)
        return f"*[API调用错误：{reason}]*"
    if not os.path.exists(image_path):
        reason = f"图片路径不存在: {image_path}"
        if is_run_environment():
            output = create_json_output(False, "Image path does not exist", None, image_path, api, reason)
            with open(os.environ['RUN_DATA_FILE'], 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            return json.dumps(output, ensure_ascii=False)
        return f"*[错误：{reason}]*"
    try:
        img = Image.open(image_path)
    except Exception as e:
        reason = f"无法打开图片文件 {image_path}: {e}"
        if is_run_environment():
            output = create_json_output(False, "Failed to open image", None, image_path, api, reason)
            with open(os.environ['RUN_DATA_FILE'], 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            return json.dumps(output, ensure_ascii=False)
        return f"*[错误：{reason}]*"
    # Use custom prompt if provided, otherwise use mode-based prompts
    if custom_prompt:
        prompt_instruction = custom_prompt
    else:
        prompt_instruction = ""
        if mode == "academic":
            prompt_instruction = (
                "You are an expert academic researcher. Analyze the following scientific image. "
                "Focus on extracting quantitative and qualitative information. Specifically:\n"
                "- **Identify the type of plot/figure.**\n"
                "- **Summarize the main finding or conclusion**.\n"
                "- **Extract key data points or significant numbers.**\n"
                "- **Describe the trend or relationship** shown.\n"
                "Present your analysis in a concise, structured list."
            )
        elif mode == "general":
            prompt_instruction = "Provide a detailed description of the image, including subjects, setting, and mood."
        elif mode == "code_snippet":
            prompt_instruction = "Accurately transcribe the code in the image into a raw code block. No explanations."
        else:
            prompt_instruction = "Please describe the following image:"
    # 收集失败原因
    failed_reasons = []
    for key_type, api_key in api_keys.items():
        if not api_key:
            continue
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = model.generate_content([prompt_instruction, img], stream=False)
            response.resolve()
            print(f"✅ 成功！使用 {key_type} 密钥获得回复。", file=sys.stderr)
            if is_run_environment(command_identifier):
                output = create_json_output(True, "Success", response.text, image_path, api)
                with open(os.environ['RUN_DATA_FILE'], 'w', encoding='utf-8') as f:
                    json.dump(output, f, ensure_ascii=False, indent=2)
                return json.dumps(output, ensure_ascii=False)
            return response.text
        except (exceptions.ResourceExhausted, exceptions.PermissionDenied, Exception) as e:
            error_detail = f"使用 {key_type} 密钥时失败: {str(e)}"
            failed_reasons.append(error_detail)
            print(f"⚠️ 警告: {error_detail[:100]}... 正在尝试下一个...", file=sys.stderr)
            continue
    
    # 构建详细的失败原因
    detailed_reason = "所有配置的API密钥都无法成功获取回复。详细信息:\n" + "\n".join([f"- {reason}" for reason in failed_reasons])
    
    if is_run_environment(command_identifier):
        output = create_json_output(False, "All API keys failed", None, image_path, api, detailed_reason)
        with open(os.environ['RUN_DATA_FILE'], 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        return json.dumps(output, ensure_ascii=False)
    return f"*[API调用失败：{detailed_reason}]*"

def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description="图片转文字描述工具（IMG2TEXT）")
    parser.add_argument("positional_args", nargs="*", help="Positional arguments (command_identifier and/or image_path)")
    parser.add_argument("--mode", default="general", 
                       choices=["academic", "general", "code_snippet"],
                       help="分析模式")
    parser.add_argument("--api", default="google", choices=["google"], help="API接口，当前仅支持google")
    parser.add_argument("--key", default=None, help="手动指定API key，优先级高于环境变量")
    parser.add_argument("--prompt", default=None, help="自定义分析指令，会覆盖默认的模式提示")
    parser.add_argument("--output-dir", help="输出结果到指定目录（自动生成文件名）")
    parser.add_argument("--test-connection", action="store_true", help="测试API连接状态，不处理任何图片")
    args = parser.parse_args()
    
    # Handle positional arguments (command_identifier and/or image_path)
    command_identifier = None
    image_path = None
    interactive_mode = False  # 默认非交互模式
    
    # 如果指定了--test-connection，则只测试连接，不需要图片路径
    if args.test_connection:
        result = test_connection(args.api, args.key, command_identifier)
        print(result)
        return
    
    if len(args.positional_args) == 0:
        # 交互模式：使用FILEDIALOG选择图片
        interactive_mode = True
        
        # 交互模式下先测试API连接
        print("🔍 正在测试API连接...")
        connection_result = test_connection(args.api, args.key, command_identifier)
        print(connection_result)
        
        # 检查连接是否成功
        if "❌ 总结: 所有" in connection_result:
            print("\n⚠️  警告：API连接测试失败，但您仍可继续选择图片进行处理")
            print("💡 建议：检查网络连接、API密钥配置或地区限制设置")
        
        try:
            import subprocess
            # 使用RUN模式调用FILEDIALOG获取JSON返回值
            run_tool = Path(__file__).parent / "RUN"
            filedialog_tool = Path(__file__).parent / "FILEDIALOG"
            if run_tool.exists() and filedialog_tool.exists():
                print("🖼️  请选择要分析的图片文件...")
                result = subprocess.run([str(run_tool), "--show", "FILEDIALOG", "--types", "image", "--title", "选择图片文件"], 
                                      capture_output=True, text=True, check=False)
                if result.returncode == 0 and result.stdout.strip():
                    # 解析RUN返回的JSON
                    try:
                        run_result = json.loads(result.stdout.strip())
                        if run_result.get('success') and (run_result.get('result') or run_result.get('selected_file')):
                            # FILEDIALOG可能返回'result'或'selected_file'字段
                            image_path = (run_result.get('result') or run_result.get('selected_file')).strip()
                            print(f"📁 已选择图片: {Path(image_path).name}")
                            
                            # 交互模式下自动设置输出文件（带编号避免冲突）
                            if not args.output_dir and interactive_mode:
                                image_path_obj = Path(image_path)
                                # 生成不重复的输出文件名
                                output_path = _generate_unique_output_path(image_path_obj)
                                
                                # 设置特殊标记，表示直接输出到文件而不是目录
                                args.output_dir = str(output_path)
                                args._direct_file_output = True  # 添加标记
                                print(f"💾 将保存描述到: {output_path.name}")
                        else:
                            # 检查是否是用户取消操作
                            if run_result.get('success') == False:
                                print(f"❌ 操作取消或失败: {run_result.get('message', '未知错误')}")
                            else:
                                print("❌ 未选择图片，退出")
                            print(f"🔍 完整返回结果: {run_result}")
                            return
                    except json.JSONDecodeError as e:
                        print(f"❌ 解析FILEDIALOG返回结果失败: {e}")
                        print(f"🔍 调试信息 - 返回码: {result.returncode}")
                        print(f"🔍 调试信息 - STDOUT: {repr(result.stdout)}")
                        print(f"🔍 调试信息 - STDERR: {repr(result.stderr)}")
                        return
                else:
                    print("❌ 文件选择失败，退出")
                    print(f"🔍 调试信息 - 返回码: {result.returncode}")
                    print(f"🔍 调试信息 - STDOUT: {repr(result.stdout)}")
                    print(f"🔍 调试信息 - STDERR: {repr(result.stderr)}")
                    return
            else:
                parser.error("Image path is required (RUN or FILEDIALOG tool not available)")
        except Exception as e:
            parser.error(f"Image path is required (FILEDIALOG error: {e})")
    elif len(args.positional_args) == 1:
        # One positional arg - could be image_path or command_identifier + image_path in other flags
        arg = args.positional_args[0]
        if arg.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif')) or '/' in arg or '\\' in arg:
            # Looks like image path
            image_path = arg
        else:
            # Could be command_identifier, but we need image_path too
            # This case is ambiguous, assume it's image_path for now
            image_path = arg
    elif len(args.positional_args) == 2:
        # Two positional args - first is command_identifier, second is image_path
        command_identifier = args.positional_args[0]
        image_path = args.positional_args[1]
    else:
        # Too many positional args
        parser.error("Too many positional arguments")
    
    args.image_path = image_path
    
    result = get_image_analysis(args.image_path, args.mode, args.api, args.key, args.prompt, command_identifier)
    
    # 如果在RUN环境下，直接输出JSON格式
    if is_run_environment(command_identifier):
        try:
            # 尝试解析result为JSON（如果已经是JSON字符串）
                json_result = json.loads(result)
                print(json.dumps(json_result, ensure_ascii=False, indent=2))
            except json.JSONDecodeError:
                # 如果不是JSON，创建一个包含结果的JSON结构
                output = create_json_output(True, "Success", result, args.image_path, args.api)
                print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
        # 正常模式下的输出
        if args.output_dir:
            # 检查是否是直接文件输出模式（交互模式）
            if hasattr(args, '_direct_file_output') and args._direct_file_output:
                # 直接输出到指定文件，覆盖已存在的文件
                output_path = args.output_dir
                # 确保父目录存在
                os.makedirs(Path(output_path).parent, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result)
                print(f"✅ 分析结果已保存到: {Path(output_path).name}")
            else:
                # 原来的目录模式：创建输出目录
                os.makedirs(args.output_dir, exist_ok=True)
                
                # 生成输出文件名：基于图片名和时间戳
                image_name = Path(args.image_path).stem
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"img2text_{image_name}_{timestamp}.txt"
                output_path = os.path.join(args.output_dir, output_filename)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result)
                print(f"✅ 分析结果已保存到: {output_path}")
        else:
            print(result)

if __name__ == "__main__":
    main() 