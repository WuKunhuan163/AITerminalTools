#!/usr/bin/env python3
"""
IMG2TEXT - Python Entrypoint
图片转文字描述工具的Python入口脚本
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions
from PIL import Image
import json
import datetime

# 加载环境变量
load_dotenv()

def is_run_environment():
    """检测是否在RUN --show环境下运行"""
    return os.environ.get('RUN_IDENTIFIER') and os.environ.get('RUN_DATA_FILE')

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

def get_image_analysis(image_path: str, mode: str = "general", api: str = "google", key: str = None, custom_prompt: str = None) -> str:
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
    for key_type, api_key in api_keys.items():
        if not api_key:
            continue
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = model.generate_content([prompt_instruction, img], stream=False)
            response.resolve()
            print(f"✅ 成功！使用 {key_type} 密钥获得回复。", file=sys.stderr)
            if is_run_environment():
                output = create_json_output(True, "Success", response.text, image_path, api)
                with open(os.environ['RUN_DATA_FILE'], 'w', encoding='utf-8') as f:
                    json.dump(output, f, ensure_ascii=False, indent=2)
                return json.dumps(output, ensure_ascii=False)
            return response.text
        except (exceptions.ResourceExhausted, exceptions.PermissionDenied, Exception) as e:
            print(f"⚠️ 警告: 使用 {key_type} 密钥时失败: {str(e)[:100]}... 正在尝试下一个...", file=sys.stderr)
            continue
    reason = "所有配置的API密钥都无法成功获取回复。"
    if is_run_environment():
        output = create_json_output(False, "All API keys failed", None, image_path, api, reason)
        with open(os.environ['RUN_DATA_FILE'], 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        return json.dumps(output, ensure_ascii=False)
    return f"*[API调用失败：{reason}]*"

def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description="图片转文字描述工具（IMG2TEXT）")
    parser.add_argument("image_path", help="图片文件路径")
    parser.add_argument("--mode", default="general", 
                       choices=["academic", "general", "code_snippet"],
                       help="分析模式")
    parser.add_argument("--api", default="google", choices=["google"], help="API接口，当前仅支持google")
    parser.add_argument("--key", default=None, help="手动指定API key，优先级高于环境变量")
    parser.add_argument("--prompt", default=None, help="自定义分析指令，会覆盖默认的模式提示")
    parser.add_argument("--output", help="输出结果到文件")
    args = parser.parse_args()
    result = get_image_analysis(args.image_path, args.mode, args.api, args.key, args.prompt)
    
    # 如果在RUN环境下，直接输出JSON格式
    if is_run_environment():
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
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"✅ 分析结果已保存到: {args.output}")
        else:
            print(result)

if __name__ == "__main__":
    main() 