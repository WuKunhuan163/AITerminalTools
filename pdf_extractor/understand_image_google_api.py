#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions
from PIL import Image

# 加载 .env 文件中的环境变量
load_dotenv()

# --- 核心修改：将密钥加载和检查逻辑移入函数内部 ---
# 顶层不再检查或配置任何东西，允许脚本被安全地导入

def get_image_analysis(image_path: str, mode: str = "academic") -> str:
    """
    调用Google Gemini Vision API分析图片，并实现从免费到付费密钥的自动回退。
    """
    # **步骤1：在函数被调用时，才检查和加载密钥**
    api_keys = {
        "FREE": os.getenv("GOOGLE_API_KEY_FREE"),
        "PAID": os.getenv("GOOGLE_API_KEY_PAID")
    }
    if not any(api_keys.values()):
        return "*[API调用错误：环境变量 GOOGLE_API_KEY_FREE 或 GOOGLE_API_KEY_PAID 未设置。]*"

    if not os.path.exists(image_path):
        return "*[错误：图片路径不存在]*"

    try:
        img = Image.open(image_path)
    except Exception as e:
        return f"*[错误：无法打开图片文件 {image_path}: {e}]*"

    # 准备Prompt (逻辑不变)
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
    
    # 循环尝试逻辑 (保持不变)
    for key_type, api_key in api_keys.items():
        if not api_key:
            continue
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = model.generate_content([prompt_instruction, img], stream=False)
            response.resolve()
            print(f"   - 成功！使用 {key_type} 密钥获得回复。", file=sys.stderr)
            return response.text
        except (exceptions.ResourceExhausted, exceptions.PermissionDenied, Exception) as e:
            print(f"   - 警告: 使用 {key_type} 密钥时失败: {str(e)[:100]}... 正在尝试下一个...", file=sys.stderr)
            continue
            
    return "*[API调用失败：所有配置的API密钥都无法成功获取回复。]*"

# 测试入口 (保持不变)
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python understand_image_google_api.py <image_path> [mode]", file=sys.stderr)
        sys.exit(1)
    
    image_path_arg = sys.argv[1]
    mode_arg = sys.argv[2] if len(sys.argv) > 2 else "academic"
    
    analysis_result = get_image_analysis(image_path_arg, mode_arg)
    print(analysis_result)