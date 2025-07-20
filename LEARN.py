#!/usr/bin/env python3
"""
LEARN.py - 智能学习系统
独立的学习材料生成工具，支持交互模式和直接调用
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


def clear_terminal():
    """Clear the terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')


def interactive_select(prompt, options, default_index=0):
    """Interactive selection with numbered options."""
    print(f"{prompt}")
    for i, option in enumerate(options):
        print(f"  {i+1}. {option}")
    
    while True:
        try:
            choice = input(f"Choose (1-{len(options)}, default: {default_index+1}): ").strip()
            if not choice:
                print(f"Selected: {options[default_index]}")
                return default_index
            
            choice_num = int(choice) - 1
            if 0 <= choice_num < len(options):
                print(f"Selected: {options[choice_num]}")
                return choice_num
            else:
                print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print(f"Please enter a valid number between 1 and {len(options)}")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None


def check_and_confirm_overwrite(output_dir):
    """Check if tutorial.md or question.md exists and confirm overwrite."""
    tutorial_path = Path(output_dir) / "tutorial.md"
    question_path = Path(output_dir) / "question.md"
    
    existing_files = []
    if tutorial_path.exists():
        existing_files.append("tutorial.md")
    if question_path.exists():
        existing_files.append("question.md")
    
    if not existing_files:
        return True  # No files to overwrite
    
    print(f"\n⚠️  以下文件已存在于 {output_dir}:")
    for file in existing_files:
        print(f"  - {file}")
    
    while True:
        try:
            choice = input("\n是否覆盖这些文件？ (y/N): ").strip().lower()
            if choice in ['y', 'yes']:
                return True
            elif choice in ['n', 'no', '']:
                return False
            else:
                print("请输入 y 或 n")
        except KeyboardInterrupt:
            print("\n操作已取消")
            return False


def get_output_directory():
    """Get output directory using tkinter directory selection."""
    print("选择项目目录...")
    return get_output_directory_tkinter()


def get_output_directory_tkinter():
    """Get output directory using tkinter as fallback."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        print("📁 请在弹出的窗口中选择输出文件夹...")
        
        # 创建tkinter根窗口并隐藏
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        # 打开目录选择对话框
        selected_dir = filedialog.askdirectory(
            title="选择项目目录"
        )
        
        # 销毁tkinter窗口
        root.destroy()
        
        if selected_dir:
            print(f"✅ 选择目录: {selected_dir}")
            return selected_dir
        else:
            print("❌ 未选择目录")
            return None
            
    except ImportError:
        print("❌ tkinter不可用，请手动输入目录路径")
        return None
    except Exception as e:
        print(f"❌ 目录选择失败: {e}")
        return None


def get_paper_file():
    """Get paper file using tkinter file selection."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        print("📄 请在弹出的窗口中选择论文文件...")
        
        # 创建tkinter根窗口并隐藏
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        # 打开文件选择对话框
        selected_file = filedialog.askopenfilename(
            title="选择论文文件",
            filetypes=[
                ("PDF文件", "*.pdf"),
                ("Markdown文件", "*.md"),
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ]
        )
        
        # 销毁tkinter窗口
        root.destroy()
        
        if selected_file:
            print(f"✅ 选择文件: {selected_file}")
            return selected_file
        else:
            print("❌ 未选择文件")
            return None
            
    except ImportError:
        print("❌ tkinter不可用，请手动输入文件路径")
        return None
    except Exception as e:
        print(f"❌ 文件选择失败: {e}")
        return None


def run_interactive_mode():
    """Run in interactive mode to collect parameters."""
    clear_terminal()
    print("=== LEARN 智能学习系统 ===")
    print("欢迎使用智能学习内容生成工具！")
    print()
    
    # Step 1: Select learning type
    print("📚 第1步：选择学习类型")
    type_choice = interactive_select(
        "学习类型:",
        ["通用主题学习", "基于学术论文学习"]
    )
    if type_choice is None:
        return None
    
    params = {}
    
    if type_choice == 0:  # General topic
        params["type"] = "general"
        
        # Get topic
        print("\n📝 第2步：输入学习主题")
        while True:
            topic = input("请输入学习主题 (例如: Python基础, 机器学习, 数据结构): ").strip()
            if topic:
                params["topic"] = topic
                break
            print("请输入有效的主题")
        
    else:  # Paper-based
        params["type"] = "paper"
        
        print("\n📄 第2步：选择论文输入方式")
        input_choice = interactive_select(
            "论文输入方式:",
            ["本地Markdown文件", "本地PDF文件", "论文URL", "论文描述/搜索"]
        )
        if input_choice is None:
            return None
            
        params["input_type"] = input_choice
        
        if input_choice == 0:  # Markdown file
            paper_file = get_paper_file()
            if not paper_file:
                return None
            params["paper_path"] = paper_file
            
            # Read markdown content
            try:
                with open(paper_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                params["paper_content"] = content
                print(f"✅ 读取Markdown文件: {len(content)} 字符")
            except Exception as e:
                print(f"❌ 读取文件失败: {e}")
                return None
                
        elif input_choice == 1:  # PDF file
            paper_file = get_paper_file()
            if not paper_file:
                return None
            params["paper_path"] = paper_file
            
            # Ask about image processing
            print("\n🖼️  图像处理选项")
            image_choice = interactive_select(
                "是否处理PDF中的图像、公式和表格？",
                ["否 (仅提取文本，速度快)", "是 (完整处理，需要API调用)"]
            )
            params["read_images"] = image_choice == 1
            
        elif input_choice == 2:  # URL
            while True:
                url = input("请输入论文URL: ").strip()
                if url:
                    params["paper_url"] = url
                    break
                print("请输入有效的URL")
                
            # Ask about image processing
            print("\n🖼️  图像处理选项")
            image_choice = interactive_select(
                "是否处理PDF中的图像、公式和表格？",
                ["否 (仅提取文本，速度快)", "是 (完整处理，需要API调用)"]
            )
            params["read_images"] = image_choice == 1
            
        elif input_choice == 3:  # Description/Search
            while True:
                description = input("请输入论文描述或关键词: ").strip()
                if description:
                    params["paper_description"] = description
                    break
                print("请输入有效的描述")
                
            # Ask about image processing
            print("\n🖼️  图像处理选项")
            image_choice = interactive_select(
                "是否处理PDF中的图像、公式和表格？",
                ["否 (仅提取文本，速度快)", "是 (完整处理，需要API调用)"]
            )
            params["read_images"] = image_choice == 1
    
    # Step 3: Select learning level
    print("\n🎯 第3步：选择学习水平")
    mode_choice = interactive_select(
        "学习水平:",
        ["初学者", "中级", "高级", "专家"]
    )
    if mode_choice is None:
        return None
    
    modes = ["初学者", "中级", "高级", "专家"]
    params["mode"] = modes[mode_choice]
    
    # Step 4: Select explanation style
    print("\n📖 第4步：选择解释风格")
    style_choice = interactive_select(
        "解释风格:",
        ["简洁明了", "详细深入", "实例丰富", "理论导向"]
    )
    if style_choice is None:
        return None
    
    styles = ["简洁明了", "详细深入", "实例丰富", "理论导向"]
    params["style"] = styles[style_choice]
    
    # Step 5: Get output directory
    print("\n📁 第5步：选择输出目录")
    output_dir = get_output_directory()
    if not output_dir:
        return None
    
    params["output_dir"] = output_dir
    
    # Check for existing files
    if not check_and_confirm_overwrite(output_dir):
        print("操作已取消")
        return None
    
    return params


def parse_direct_command(args):
    """Parse direct command line arguments."""
    parser = argparse.ArgumentParser(description='LEARN - 智能学习系统')
    
    # Basic options
    parser.add_argument('topic', nargs='?', help='学习主题')
    parser.add_argument('-o', '--output', required=True, help='输出目录')
    parser.add_argument('-m', '--mode', choices=['初学者', '中级', '高级', '专家'], 
                       default='中级', help='学习水平')
    parser.add_argument('-s', '--style', choices=['简洁明了', '详细深入', '实例丰富', '理论导向'],
                       default='详细深入', help='解释风格')
    
    # Paper options
    parser.add_argument('-p', '--paper', help='论文文件路径')
    parser.add_argument('-u', '--url', help='论文URL')
    parser.add_argument('-d', '--description', help='论文描述/搜索关键词')
    parser.add_argument('--read-images', action='store_true', help='处理PDF中的图像、公式和表格')
    
    # Model options
    parser.add_argument('--model', help='指定OpenRouter模型')
    parser.add_argument('--max-tokens', type=int, help='最大token数')
    parser.add_argument('--not-default', action='store_true', help='非默认模式，需要用户确认')
    parser.add_argument('--no-auto-create', action='store_true', help='不自动创建文件，仅生成内容')
    
    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        return None
    
    # Build parameters
    params = {
        'mode': parsed_args.mode,
        'style': parsed_args.style,
        'output_dir': parsed_args.output,
        'not_default': parsed_args.not_default,
        'no_auto_create': parsed_args.no_auto_create
    }
    
    if parsed_args.model:
        params['selected_model'] = parsed_args.model
    if parsed_args.max_tokens:
        params['max_tokens'] = parsed_args.max_tokens
    
    # Determine type based on arguments
    if parsed_args.paper:
        params['type'] = 'paper'
        params['input_type'] = 1  # PDF file
        params['paper_path'] = parsed_args.paper
        params['read_images'] = parsed_args.read_images
    elif parsed_args.url:
        params['type'] = 'paper'
        params['input_type'] = 2  # URL
        params['paper_url'] = parsed_args.url
        params['read_images'] = parsed_args.read_images
    elif parsed_args.description:
        params['type'] = 'paper'
        params['input_type'] = 3  # Description/Search
        params['paper_description'] = parsed_args.description
        params['read_images'] = parsed_args.read_images
    elif parsed_args.topic:
        params['type'] = 'general'
        params['topic'] = parsed_args.topic
    else:
        print("错误：必须指定学习主题或论文信息")
        return None
    
    return params


def get_openrouter_models():
    """Get available OpenRouter models."""
    try:
        script_dir = Path(__file__).parent
        openrouter_data_file = script_dir / "OPENROUTER_DATA" / "openrouter_models.json"
        
        if openrouter_data_file.exists():
            import json
            with open(openrouter_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                models_dict = data.get('models', {})
                if isinstance(models_dict, dict):
                    # Extract model names from dictionary format
                    models = list(models_dict.keys())
                    model_details = models_dict
                else:
                    # Handle list format (legacy)
                    models = models_dict
                    model_details = data.get('model_details', {})
                return models, model_details
        else:
            # Fallback to default models
            default_models = [
                "deepseek/deepseek-r1:free",
                "deepseek/deepseek-chat",
                "openai/gpt-4o-mini",
                "anthropic/claude-3-haiku"
            ]
            return default_models, {}
    except Exception as e:
        print(f"⚠️  获取模型列表失败: {e}")
        # Return minimal fallback
        return ["deepseek/deepseek-r1:free"], {}


def select_openrouter_model(params):
    """Select OpenRouter model with token limits."""
    models, model_details = get_openrouter_models()
    
    if not models:
        print("❌ 没有可用的模型")
        return None, None
    
    # Check if model is already specified
    if params.get("selected_model"):
        selected_model = params["selected_model"]
        max_tokens = params.get("max_tokens", 4000)
        print(f"✅ 使用指定模型: {selected_model}")
        return selected_model, max_tokens
    
    # Auto-select for default mode
    if not params.get('not_default', False):
        selected_model = models[0]  # Use first available model
        max_tokens = 4000
        print(f"🚀 默认模式：自动选择模型 {selected_model}")
        return selected_model, max_tokens
    
    # Interactive model selection
    print(f"\n🤖 选择OpenRouter模型")
    print("可用模型:")
    
    # Categorize models
    free_models = []
    paid_models = []
    
    for model in models:
        details = model_details.get(model, {})
        if ":free" in model or details.get('input_cost_per_1m', 0) == 0:
            free_models.append(model)
        else:
            paid_models.append(model)
    
    all_models = []
    
    if free_models:
        print("\n免费模型:")
        for model in free_models:
            print(f"  {len(all_models) + 1}. {model}")
            all_models.append(model)
    
    if paid_models:
        print("\n付费模型:")
        for model in paid_models:
            details = model_details.get(model, {})
            cost = details.get('input_cost_per_1m', 0)
            cost_str = f" (${cost:.2f}/1M tokens)" if cost > 0 else ""
            print(f"  {len(all_models) + 1}. {model}{cost_str}")
            all_models.append(model)
    
    # Select model
    while True:
        try:
            choice = input(f"\n选择模型 (1-{len(all_models)}, 默认: 1): ").strip()
            if not choice:
                selected_model = all_models[0]
                break
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(all_models):
                selected_model = all_models[choice_idx]
                break
            else:
                print(f"请输入 1-{len(all_models)} 之间的数字")
        except ValueError:
            print("请输入有效数字")
        except KeyboardInterrupt:
            print("\n操作取消")
            return None, None
    
    # Set token limit based on model
    details = model_details.get(selected_model, {})
    context_length = details.get('context_length', 8000)
    
    # Conservative token limit (reserve space for output)
    if context_length > 100000:
        max_tokens = 8000
    elif context_length > 32000:
        max_tokens = 4000
    else:
        max_tokens = 2000
    
    print(f"✅ 选择模型: {selected_model}")
    print(f"📊 Token限制: {max_tokens}")
    
    return selected_model, max_tokens


def generate_content_structure_prompt(params):
    """Generate prompt for content structure brainstorming."""
    if params["type"] == "general":
        topic = params['topic']
        mode = params['mode']
        style = params['style']
        
        return f"""请为"{topic}"这个学习主题进行头脑风暴分析。

学习水平：{mode}
解释风格：{style}

请分析以下内容：
1. 核心概念和知识点
2. 学习的重点和难点
3. 适合的学习顺序
4. 实践练习建议
5. 常见问题和误区

请提供结构化的分析，为后续创建详细教程做准备。"""

    elif params["type"] == "paper":
        mode = params['mode']
        style = params['style']
        
        # For paper type, prepare content first
        paper_content, paper_path, token_count = prepare_paper_content(params)
        if not paper_content:
            return None
            
        # Store prepared content in params
        params['paper_content'] = paper_content
        params['paper_path'] = paper_path
        params['token_count'] = token_count
        
        # Check if content is too long and needs summarization
        if token_count > 15000:
            print(f"⚠️  论文内容较长 ({token_count:,} tokens)，建议进行内容总结")
            
            # Ask user about processing approach
            approach_choice = interactive_select(
                "内容处理方式:",
                ["直接使用 (可能超出模型限制)", "智能摘要 (推荐)", "手动截取前部分"]
            )
            
            if approach_choice == 1:  # Smart summary
                print("📝 正在生成论文摘要...")
                # Generate summary prompt
                summary_prompt = f"""请为以下学术论文生成详细摘要，保留关键技术细节：

{paper_content[:20000]}

请包含：
1. 研究背景和问题
2. 主要方法和技术
3. 关键创新点
4. 实验结果
5. 结论和意义

摘要应该详细但简洁，适合后续教程创建。"""
                
                # Call API for summary
                summary_response, summary_token_info, _ = call_openrouter_with_retry(
                    summary_prompt, 
                    params.get("selected_model", "deepseek/deepseek-r1:free"), 
                    params.get("max_tokens", 4000), 
                    "论文摘要生成",
                    params=params
                )
                
                if summary_response:
                    paper_content = summary_response
                    print(f"✅ 摘要生成完成 ({count_tokens(paper_content)} tokens)")
                else:
                    print("❌ 摘要生成失败，使用原始内容")
                    
            elif approach_choice == 2:  # Manual truncate
                paper_content = paper_content[:60000]  # Keep first 60k characters
                print(f"✅ 截取前部分内容 ({count_tokens(paper_content)} tokens)")
        
        # Update params with processed content
        params['paper_content'] = paper_content
        
        # Generate brainstorming prompt for paper
        return f"""请分析这篇学术论文的内容，为创建教程做准备：

论文路径：{paper_path}
学习水平：{mode}
解释风格：{style}

论文内容：
{paper_content}

请分析：
1. 论文的核心贡献和创新点
2. 关键概念和技术方法
3. 适合{mode}水平学习者的重点内容
4. 可能的难点和解释策略
5. 实践应用和扩展思考

请提供结构化分析，为后续创建详细教程做准备。"""
    
    return None


def call_openrouter_for_structure(prompt, model=None, max_tokens=None, retry_count=0):
    """Call OpenRouter API for structure generation with improved error handling."""
    import time
    import json
    import re
    
    try:
        script_dir = Path(__file__).parent
        run_path = script_dir / "RUN.py"
        
        if retry_count == 0:
            print("🔄 正在连接OpenRouter API...", file=sys.stderr)
        else:
            print(f"🔄 重试API调用 (第{retry_count}次)...", file=sys.stderr)
            
        # 如果没有指定模型，使用第一个可用模型
        if not model:
            print("🔄 正在连接OpenRouter API...", file=sys.stderr)
            models, model_details = get_openrouter_models()
            if not models:
                return None, {"error": "No useable models available"}
            model = models[0]
        
        print(f"🤖 使用模型: {model}", file=sys.stderr)
        if max_tokens:
            print(f"🔢 最大tokens: {max_tokens}", file=sys.stderr)
        print("⏳ 这可能需要一会，请耐心等待...", file=sys.stderr)
        
        # 记录开始时间
        start_time = time.time()
        
        # 构建命令 - 使用RUN --show调用OPENROUTER工具，通过stdin传递prompt
        cmd = [sys.executable, str(run_path), "--show", "OPENROUTER"]
        
        if model:
            cmd.extend(["--model", model])
        
        # 传入max-tokens参数（OPENROUTER工具会自动处理动态调整）
        if max_tokens:
            cmd.extend(["--max-tokens", str(max_tokens)])
        
        # 使用RUN --show模式调用OPENROUTER工具，避免响应被截断
        try:
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE, text=True)
            try:
                stdout, stderr = process.communicate(input=prompt, timeout=120)  # 增加超时时间
                
                # 创建一个result对象来模拟subprocess.run的返回值
                class Result:
                    def __init__(self, returncode, stdout, stderr):
                        self.returncode = returncode
                        self.stdout = stdout
                        self.stderr = stderr
                
                result = Result(process.returncode, stdout, stderr)
            except subprocess.TimeoutExpired:
                end_time = time.time()
                api_duration = end_time - start_time
                print(f"⏰ OpenRouter API调用超时 (耗时: {api_duration:.2f}秒)", file=sys.stderr)
                process.kill()
                return None, None
        except KeyboardInterrupt:
            end_time = time.time()
            api_duration = end_time - start_time
            print(f"🚫 用户中断API调用 (耗时: {api_duration:.2f}秒)", file=sys.stderr)
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
            return None, None
        
        # 记录结束时间
        end_time = time.time()
        api_duration = end_time - start_time
        
        if result.returncode == 0:
            print(f"✅ OpenRouter API调用成功 (耗时: {api_duration:.2f}秒)", file=sys.stderr)
            
            # 解析JSON响应
            try:
                # 清理ANSI转义序列
                clean_output = re.sub(r'\x1b\[[0-9;]*[mJKH]', '', result.stdout)
                
                response_data = json.loads(clean_output)
                
                if response_data.get('success'):
                    # 提取响应内容和token信息
                    response_content, usage_info = extract_response_data(response_data)
                    
                    # 检查响应是否为空
                    if not response_content or response_content.strip() == '':
                        print(f"⚠️  OpenRouter API返回空内容 (耗时: {api_duration:.2f}秒)", file=sys.stderr)
                        return None, None
                    
                    # 处理可能的markdown代码块包装
                    response_content = clean_markdown_wrapper(response_content)
                    
                    # 构建token信息
                    token_info = {
                        'prompt_tokens': usage_info.get('input_tokens', 0),
                        'completion_tokens': usage_info.get('output_tokens', 0),
                        'total_tokens': usage_info.get('total_tokens', 0),
                        'cost': usage_info.get('cost', 0),
                        'api_duration': api_duration,
                        'model': model
                    }
                    
                    return response_content, token_info
                else:
                    error_msg = response_data.get('error', 'Unknown error')
                    print(f"❌ OpenRouter API返回错误: {error_msg} (耗时: {api_duration:.2f}秒)", file=sys.stderr)
                    return f"ERROR: {error_msg}", None
                    
            except json.JSONDecodeError as e:
                print(f"❌ 解析JSON响应失败: {e} (耗时: {api_duration:.2f}秒)", file=sys.stderr)
                print(f"原始输出: {result.stdout[:200]}...", file=sys.stderr)
                return None, None
                
        else:
            print(f"❌ RUN --show OPENROUTER执行失败: {result.stderr} (耗时: {api_duration:.2f}秒)", file=sys.stderr)
            return None, None

    except Exception as e:
        end_time = time.time()
        api_duration = end_time - start_time if 'start_time' in locals() else 0
        print(f"❌ 调用OpenRouter API时出错: {e} (耗时: {api_duration:.2f}秒)", file=sys.stderr)
        return None, None


def extract_response_data(response_data):
    """Extract response content and usage info from API response."""
    response_content = ""
    usage_info = {}
    
    # 检查是否是RUN --show的包装格式
    if 'output' in response_data:
        try:
            output_content = response_data['output']
            if output_content.strip().startswith('{'):
                # output是JSON格式
                import json
                inner_data = json.loads(output_content)
                if inner_data.get('success'):
                    response_content = inner_data.get('content', '')
                    usage = inner_data.get('usage', {})
                    usage_info = {
                        'input_tokens': usage.get('input_tokens', 0),
                        'output_tokens': usage.get('output_tokens', 0),
                        'total_tokens': usage.get('total_tokens', 0),
                        'cost': inner_data.get('cost', 0)
                    }
                else:
                    response_content = output_content
            else:
                # output是纯文本，但检查是否有RUN_DATA_FILE
                response_content = output_content
                # 尝试从RUN_DATA_FILE中读取token信息
                if '_RUN_DATA_file' in response_data:
                    try:
                        import json
                        with open(response_data['_RUN_DATA_file'], 'r', encoding='utf-8') as f:
                            run_data = json.load(f)
                            if 'usage' in run_data:
                                usage = run_data['usage']
                                usage_info = {
                                    'input_tokens': usage.get('input_tokens', 0),
                                    'output_tokens': usage.get('output_tokens', 0),
                                    'total_tokens': usage.get('total_tokens', 0),
                                    'cost': run_data.get('cost', 0)
                                }
                    except (FileNotFoundError, json.JSONDecodeError, KeyError):
                        pass
        except json.JSONDecodeError:
            # 如果解析失败，直接使用output内容
            response_content = response_data['output']
    else:
        # 直接从response_data中提取
        response_content = response_data.get('content', 
                          response_data.get('response', 
                          response_data.get('message', '')))
        usage = response_data.get('usage', {})
        usage_info = {
            'input_tokens': usage.get('input_tokens', 0),
            'output_tokens': usage.get('output_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0),
            'cost': response_data.get('cost', 0)
        }
    
    return response_content, usage_info


def clean_markdown_wrapper(content):
    """Clean markdown code block wrapper if present."""
    if '```markdown' in content:
        # 使用```markdown分割内容
        parts = content.split('```markdown')
        if len(parts) >= 2:
            # 取第二部分（```markdown之后的内容）
            markdown_content = parts[1]
            # 移除最后的```（如果存在）
            if '```' in markdown_content:
                markdown_content = markdown_content.split('```')[0]
            return markdown_content.strip()
    return content


def generate_tutorial_prompt(params, brainstorming_response):
    """Generate prompt for tutorial.md creation."""
    if params["type"] == "general":
        # General topic
        topic = params['topic']
        mode = params['mode']
        style = params['style']
        
        brainstorming_summary = brainstorming_response
        
        prompt = f"""请为"{topic}"创建一个简洁的tutorial.md文件。

学习模式：{mode}
解释风格：{style}

基于以下要点创建教程：
{brainstorming_summary}

请创建一个结构简洁的tutorial.md文件，包含：
1. 标题和目录
2. 3-4个核心概念的详细解释（包含代码示例，例题等，if applicable）
3. 简明的学习路径指导
4. 2-3个实践练习建议
5. 精选资源推荐

请确保内容适合{mode}水平的学习者，并采用{style}的解释风格。
请直接提供markdown格式的内容，不要使用任何分隔符。"""
        
    else:
        # Paper-based
        paper_path = params.get('paper_path', '论文')
        paper_content = params.get('paper_content', '')
        mode = params['mode']
        style = params['style']
        
        # Use brainstorming response if available, otherwise use paper content directly
        if brainstorming_response:
            content_base = f"""头脑风暴分析结果：
{brainstorming_response}

原论文内容（参考）：
{paper_content[:5000]}{'...' if len(paper_content) > 5000 else ''}"""
        else:
            content_base = f"""论文内容：
{paper_content}"""
        
        prompt = f"""请基于学术论文内容创建一个详细的tutorial.md教程文件。

论文：{paper_path}
学习模式：{mode}
解释风格：{style}

基于以下内容创建教程：
{content_base}

请创建一个完整的tutorial.md文件，包含：

1. **论文概览**
   - 论文标题、作者、发表信息
   - 研究背景和动机
   - 主要贡献和创新点

2. **核心概念详解**
   - 关键概念的定义和解释
   - 技术方法的详细说明
   - 算法或模型的工作原理

3. **技术细节**
   - 实现方法和技术路线
   - 实验设计和评估方法
   - 结果分析和讨论

4. **学习要点**
   - 重点知识点总结
   - 与现有方法的比较
   - 优势和局限性分析

5. **扩展阅读**
   - 相关论文推荐
   - 进一步学习资源

请确保内容适合{mode}水平的学习者，采用{style}的解释风格。
请直接提供markdown格式的内容，不要使用任何分隔符。"""
    
    return prompt


def generate_question_prompt(params, tutorial_content):
    """Generate prompt for question.md creation."""
    if params["type"] == "general":
        # General topic
        topic = params['topic']
        mode = params['mode']
        style = params['style']
        
        tutorial_summary = tutorial_content
        
        prompt = f"""请为"{topic}"创建简洁的练习题文件question.md。

学习模式：{mode}
解释风格：{style}

基于以下教程内容创建练习题：
{tutorial_summary}

请创建一个简洁的question.md文件，包含：
1. 基础知识测试题（3题）
2. 理解应用题（3题）
3. 实践练习题（2题）
4. 思考题（2题）
5. 每个问题都要有简洁明确的答案

请使用HTML的details/summary标签来创建可展开的答案区域。
请确保问题适合{mode}水平的学习者。
请控制内容长度，保持简洁。"""
        
    else:
        # Paper-based
        paper_path = params.get('paper_path', '论文')
        mode = params['mode']
        style = params['style']
        
        tutorial_summary = tutorial_content
        
        prompt = f"""请基于学术论文教程创建comprehensive的练习题文件question.md。

论文：{paper_path}
学习模式：{mode}
解释风格：{style}

基于以下教程内容创建练习题：
{tutorial_summary}

请创建一个全面的question.md文件，包含：

1. **论文理解题（4题）**
   - 研究背景和动机理解
   - 主要贡献和创新点
   - 技术方法和原理
   - 实验结果和结论

2. **概念解释题（3题）**
   - 关键概念定义
   - 技术术语解释
   - 方法比较分析

3. **批判性思考题（3题）**
   - 方法优缺点分析
   - 改进建议和扩展
   - 应用场景讨论

4. **实践应用题（2题）**
   - 实际应用设计
   - 实现思路分析

每个问题都必须：
- 基于教程中的具体内容
- 有详细准确的答案
- 使用HTML的<details>和<summary>标签实现答案折叠

格式示例：
### 问题1：这篇论文的主要贡献是什么？
<details>
<summary>点击查看答案</summary>

[详细答案内容...]

</details>

请确保问题适合{mode}水平的学习者，采用{style}的解释风格。"""
    
    return prompt


def create_learning_files_from_responses(params, tutorial_response, question_response, prompts_and_responses=None):
    """Create learning files from separate tutorial and question responses."""
    output_dir = params['output_dir']
    
    # 确保输出目录存在
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        # 创建tutorial.md
        tutorial_path = Path(output_dir) / "tutorial.md"
        with open(tutorial_path, 'w', encoding='utf-8') as f:
            f.write(tutorial_response)
        print(f"✅ 创建文件: {tutorial_path}")
        
        # 创建question.md
        question_path = Path(output_dir) / "question.md"
        with open(question_path, 'w', encoding='utf-8') as f:
            f.write(question_response)
        print(f"✅ 创建文件: {question_path}")
        
        # 创建OPENROUTER_prompts文件夹并保存prompts和responses
        if prompts_and_responses:
            prompts_dir = Path(output_dir) / "OPENROUTER_prompts"
            prompts_dir.mkdir(exist_ok=True)
            
            for i, (prompt, response, token_info) in enumerate(prompts_and_responses, 1):
                # 保存prompt
                prompt_path = prompts_dir / f"prompt_{i}.txt"
                with open(prompt_path, 'w', encoding='utf-8') as f:
                    f.write(prompt)
                    f.write(f"\n\n--- Openrouter API Call Info ---\n")
                    f.write(f"model: {token_info.get('model', 'unknown')}\n")
                    f.write(f"prompt_tokens: {token_info.get('prompt_tokens', 0)}\n")
                    f.write(f"completion_tokens: {token_info.get('completion_tokens', 0)}\n")
                    f.write(f"total_tokens: {token_info.get('total_tokens', 0)}\n")
                    f.write(f"cost: ${token_info.get('cost', 0):.6f}\n")
                    f.write(f"api_duration: {token_info.get('api_duration', 0):.2f} seconds\n")
                
                # 保存response
                response_path = prompts_dir / f"response_{i}.txt"
                with open(response_path, 'w', encoding='utf-8') as f:
                    f.write(response)
                    f.write(f"\n\n--- Openrouter API Call Info ---\n")
                    f.write(f"model: {token_info.get('model', 'unknown')}\n")
                    f.write(f"prompt_tokens: {token_info.get('prompt_tokens', 0)}\n")
                    f.write(f"completion_tokens: {token_info.get('completion_tokens', 0)}\n")
                    f.write(f"total_tokens: {token_info.get('total_tokens', 0)}\n")
                    f.write(f"cost: ${token_info.get('cost', 0):.6f}\n")
                    f.write(f"api_duration: {token_info.get('api_duration', 0):.2f} seconds\n")
                
                print(f"✅ 保存prompt和response: {prompt_path.name}, {response_path.name}")
                model_used = token_info.get('model', 'unknown')
                cost = token_info.get('cost', 0)
                print(f"📊 Token使用: {token_info.get('total_tokens', 0)} tokens (输入: {token_info.get('prompt_tokens', 0)}, 输出: {token_info.get('completion_tokens', 0)}) - 模型: {model_used} - 费用: ${cost:.6f} - 用时: {token_info.get('api_duration', 0):.2f}秒")
        
        file_count = 2 + (len(prompts_and_responses) * 2 if prompts_and_responses else 0)
        print(f"\n📁 创建了 {file_count} 个文件:")
        print(f"  - {tutorial_path}")
        print(f"  - {question_path}")
        if prompts_and_responses:
            print(f"  - OPENROUTER_prompts/ 文件夹包含 {len(prompts_and_responses)} 组prompt和response")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建文件时出错: {e}")
        return False


def call_openrouter_with_retry(prompt, model, max_tokens, step_name, max_retries=3, params=None):
    """Call OpenRouter API with retry mechanism and model switching."""
    current_model = model
    
    for attempt in range(max_retries):
        response, token_info = call_openrouter_for_structure(prompt, current_model, max_tokens, attempt)
        
        # 检查是否成功（不是None且不是错误）
        if response is not None and not (isinstance(response, str) and response.startswith("ERROR:")):
            return response, token_info, current_model
        
        print(f"❌ {step_name}失败 (第{attempt + 1}次尝试)", file=sys.stderr)
        
        # 检查是否是429错误（速率限制）或其他错误需要切换模型
        if should_switch_model(response, attempt, max_retries):
            current_model = handle_model_switching(current_model, params, step_name)
            if not current_model:
                break
            
            # 用新模型重试
            response, token_info = call_openrouter_for_structure(prompt, current_model, max_tokens, 0)
            if response is not None and not (isinstance(response, str) and response.startswith("ERROR:")):
                return response, token_info, current_model
    
    return None, None, current_model


def should_switch_model(response, attempt, max_retries):
    """Determine if we should switch models based on error type and attempt."""
    if response and isinstance(response, str):
        # 立即切换的情况：429错误
        if "429" in response or "rate-limited" in response:
            return True
        # 最后一次重试时切换的情况：其他错误
        if attempt == max_retries - 1:
            return True
    return False


def handle_model_switching(current_model, params, step_name):
    """Handle model switching logic."""
    # 获取所有可用模型
    all_models, model_details = get_openrouter_models()
    if not all_models:
        print("❌ 无法获取模型列表", file=sys.stderr)
        return None
    
    # 移除当前失败的模型
    available_models = [m for m in all_models if m != current_model]
    if not available_models:
        print("❌ 没有其他可用模型", file=sys.stderr)
        return None
    
    # 分类模型
    free_models = [m for m in available_models if ":free" in m]
    paid_models = [m for m in available_models if ":free" not in m]
    
    # 默认模式：自动切换
    if params and not params.get('not_default', False):
        if current_model and ":free" in current_model and free_models:
            new_model = free_models[0]
            print(f"🔄 自动切换到下一个免费模型: {new_model}", file=sys.stderr)
            return new_model
        elif paid_models:
            new_model = paid_models[0]
            print(f"🔄 自动切换到付费模型: {new_model}", file=sys.stderr)
            return new_model
    else:
        # 交互模式：让用户选择
        return interactive_model_selection(current_model, free_models, paid_models, step_name)
    
    return None


def interactive_model_selection(failed_model, free_models, paid_models, step_name):
    """Interactive model selection when switching models."""
    print(f"\n⚠️  模型 '{failed_model}' 调用失败", file=sys.stderr)
    print("可用的替代模型：", file=sys.stderr)
    
    all_available = []
    if free_models:
        print("免费模型：", file=sys.stderr)
        for i, model_name in enumerate(free_models):
            print(f"  {len(all_available) + 1}. {model_name}", file=sys.stderr)
            all_available.append(model_name)
    
    if paid_models:
        print("付费模型：", file=sys.stderr)
        for i, model_name in enumerate(paid_models):
            print(f"  {len(all_available) + 1}. {model_name}", file=sys.stderr)
            all_available.append(model_name)
    
    try:
        choice = input(f"\n选择模型 (1-{len(all_available)}) 或按回车跳过: ").strip()
        if choice and choice.isdigit():
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(all_available):
                new_model = all_available[choice_idx]
                print(f"✅ 切换到模型: {new_model}", file=sys.stderr)
                return new_model
    except (KeyboardInterrupt, EOFError):
        print("\n用户取消操作", file=sys.stderr)
    
    return None


def generate_learning_content(params):
    """Generate learning content based on collected parameters."""
    print("\n🤖 正在生成学习内容结构...")
    
    # 用于保存所有的prompts和responses，现在包含token信息
    prompts_and_responses = []
    
    # For paper type, model selection might already be done in generate_content_structure_prompt
    if params["type"] == "paper" and params.get("selected_model"):
        selected_model = params["selected_model"]
        max_tokens = params["max_tokens"]
        print(f"✅ 使用已选择的模型: {selected_model}")
    else:
        # 让用户选择模型
        selected_model, max_tokens = select_openrouter_model(params)
        if not selected_model:
            print("❌ 未选择模型")
            return None
        
        # Store selected model info in params for later use
        params["selected_model"] = selected_model
        params["max_tokens"] = max_tokens
    
    # Step 1: Brainstorming (optional for papers)
    brainstorming_response = None
    brainstorming_token_info = None
    
    print("\n📝 第1步：询问AI进行头脑风暴...")
    structure_prompt = generate_content_structure_prompt(params)
    
    if structure_prompt:  # Brainstorming was requested
        print("查询内容:")
        print("-" * 40)
        print(structure_prompt[:500] + "..." if len(structure_prompt) > 500 else structure_prompt)
        print("-" * 40)
        
        # Call OpenRouter API for brainstorming with retry
        brainstorming_response, brainstorming_token_info, current_model = call_openrouter_with_retry(
            structure_prompt, selected_model, max_tokens, "头脑风暴", params=params
        )
        
        if brainstorming_response is None:
            print("❌ 头脑风暴失败")
            return None
        
        # 保存第一组prompt和response
        prompts_and_responses.append((structure_prompt, brainstorming_response, brainstorming_token_info))
        
        # 如果是no_auto_create模式，只返回brainstorming结果
        if params.get("no_auto_create", False):
            print("\n📋 头脑风暴完成！以下是生成的结构建议：")
            print("=" * 60)
            print(brainstorming_response)
            print("=" * 60)
            print("\n💡 你可以基于以上建议手动创建tutorial.md和question.md文件")
            return {
                'brainstorming_response': brainstorming_response,
                'prompts_and_responses': prompts_and_responses
            }
    else:
        print("⏭️  跳过头脑风暴，直接生成教程")
        
        # For paper type without brainstorming, check if we should continue
        if params["type"] == "paper":
            creation_mode = determine_creation_mode(params, selected_model)
            if creation_mode == "manual":
                params["no_auto_create"] = True
    
    # Step 2: Generate tutorial.md
    print("\n📝 第2步：基于内容生成tutorial.md...")
    tutorial_prompt = generate_tutorial_prompt(params, brainstorming_response)
    
    print("查询内容:")
    print("-" * 40)
    print(tutorial_prompt[:500] + "..." if len(tutorial_prompt) > 500 else tutorial_prompt)
    print("-" * 40)
    
    tutorial_response, tutorial_token_info, current_model = call_openrouter_with_retry(
        tutorial_prompt, selected_model, max_tokens, "tutorial.md生成", params=params
    )
    
    if tutorial_response is None:
        print("❌ tutorial.md生成失败")
        return None
    
    # 保存第二组prompt和response
    prompts_and_responses.append((tutorial_prompt, tutorial_response, tutorial_token_info))
    
    # Check if manual creation mode after tutorial generation
    if params.get("no_auto_create", False):
        print("\n📋 Tutorial生成完成！")
        print("💡 你可以基于以下内容手动创建question.md文件")
        return {
            'tutorial_response': tutorial_response,
            'brainstorming_response': brainstorming_response,
            'prompts_and_responses': prompts_and_responses
        }
    
    # Step 3: Generate question.md
    print("\n📝 第3步：基于tutorial.md生成question.md...")
    question_prompt = generate_question_prompt(params, tutorial_response)
    
    print("查询内容:")
    print("-" * 40)
    print(question_prompt[:500] + "..." if len(question_prompt) > 500 else question_prompt)
    print("-" * 40)
    
    question_response, question_token_info, current_model = call_openrouter_with_retry(
        question_prompt, selected_model, max_tokens, "question.md生成", params=params
    )
    
    if question_response is None:
        print("❌ question.md生成失败")
        return None
    
    # 保存第三组prompt和response
    prompts_and_responses.append((question_prompt, question_response, question_token_info))
    
    # 返回所有生成的内容
    return {
        'tutorial_response': tutorial_response,
        'question_response': question_response,
        'brainstorming_response': brainstorming_response,
        'prompts_and_responses': prompts_and_responses
    }


def determine_creation_mode(params, selected_model):
    """Determine creation mode for paper type without brainstorming."""
    # Auto-proceed in default mode or with free models
    if not params.get('not_default', False):
        print("🚀 默认模式：自动选择创建模式...")
        return "auto"
    
    # Check if using free model
    if selected_model:
        models, model_details = get_openrouter_models()
        if models:
            details = model_details.get(selected_model, {})
            is_free_model = details.get('input_cost_per_1m', 0) == 0
            if is_free_model:
                print("🚀 免费模型：自动选择创建模式...")
                return "auto"
    
    # Ask user about creation mode
    print("\n🎯 选择创建模式:")
    creation_choice = interactive_select(
        "创建模式:", 
        ["自动创建 (AI生成3次)", "手动创建 (AI生成1次，你来创建文件)"]
    )
    
    return "manual" if creation_choice == 1 else "auto"


def count_tokens(text):
    """Simple token counting approximation."""
    # Rough approximation: 1 token ≈ 4 characters for Chinese/English mixed text
    return len(text) // 4


def prepare_paper_content(params):
    """Prepare paper content based on input type."""
    input_type = params.get("input_type", 1)
    paper_content = None
    paper_path = None
    
    if input_type == 0:  # Markdown file
        paper_content = params.get("paper_content")
        paper_path = params.get("paper_path")
        print("✅ 使用已提供的Markdown内容")
        
    elif input_type == 1:  # PDF file
        paper_path = params.get("paper_path")
        read_images = params.get("read_images", False)
        paper_content, processed_path = process_paper_with_extract_pdf(paper_path, read_images)
        if processed_path:
            paper_path = processed_path
            
    elif input_type == 2:  # URL
        paper_url = params.get("paper_url")
        print(f"📥 下载论文: {paper_url}")
        
        # Extract filename from URL or use generic name
        import urllib.parse
        parsed_url = urllib.parse.urlparse(paper_url)
        filename = Path(parsed_url.path).name or "downloaded_paper.pdf"
        
        downloaded_path, title = download_paper(paper_url, filename.replace('.pdf', ''))
        if downloaded_path:
            read_images = params.get("read_images", False)
            paper_content, processed_path = process_paper_with_extract_pdf(downloaded_path, read_images)
            if processed_path:
                paper_path = processed_path
        else:
            print("❌ 无法下载论文")
            return None, None, 0
            
    elif input_type == 3:  # Description/Search
        paper_description = params.get("paper_description")
        downloaded_path, title = search_and_download_paper(paper_description)
        if downloaded_path:
            read_images = params.get("read_images", False)
            paper_content, processed_path = process_paper_with_extract_pdf(downloaded_path, read_images)
            if processed_path:
                paper_path = processed_path
        else:
            print("❌ 无法找到或下载论文")
            return None, None, 0
    
    if not paper_content:
        print("❌ 无法获取论文内容")
        return None, None, 0
    
    # Count tokens
    token_count = count_tokens(paper_content)
    print(f"\n📊 论文内容统计:")
    print(f"   字符数: {len(paper_content):,}")
    print(f"   预估token数: {token_count:,}")
    
    return paper_content, paper_path, token_count


def search_and_download_paper(paper_description):
    """Search for paper and download if found."""
    print(f"\n🔍 搜索论文: {paper_description}")
    
    try:
        script_dir = Path(__file__).parent
        search_paper_path = script_dir / "SEARCH_PAPER"
        
        # Search for papers
        result = subprocess.run([
            str(search_paper_path), paper_description, "--max-results", "5"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ 搜索失败: {result.stderr}")
            return None, None
            
        print("✅ 搜索完成，正在解析结果...")
        
        # Parse search results to find download URLs
        search_results = parse_search_results()
        if not search_results:
            print("❌ 未找到相关论文")
            return None, None
        
        # Show papers to user and let them select
        selected_paper = interactive_paper_selection(search_results)
        if not selected_paper:
            return None, None
        
        # Try to download the paper
        pdf_url = selected_paper.get('pdf_url')
        if pdf_url:
            print(f"\n📥 尝试下载论文: {selected_paper.get('title', 'Unknown')}")
            return download_paper(pdf_url, selected_paper.get('title', 'paper'))
        else:
            print("❌ 未找到PDF下载链接")
            return None, None
            
    except Exception as e:
        print(f"❌ 搜索过程出错: {e}")
        return None, None


def parse_search_results():
    """Parse search results from SEARCH_PAPER_DATA."""
    try:
        script_dir = Path(__file__).parent
        search_data_dir = script_dir / "SEARCH_PAPER_DATA" / "results"
        
        if not search_data_dir.exists():
            return None
        
        # Get the most recent search results file
        result_files = list(search_data_dir.glob("search_results_*.json"))
        if not result_files:
            return None
        
        latest_file = max(result_files, key=lambda x: x.stat().st_mtime)
        
        import json
        with open(latest_file, 'r', encoding='utf-8') as f:
            search_results = json.load(f)
        
        return search_results if search_results else None
        
    except Exception as e:
        print(f"❌ 解析搜索结果失败: {e}")
        return None


def interactive_paper_selection(search_results):
    """Interactive paper selection from search results."""
    if not search_results or len(search_results) == 0:
        return None
    
    print(f"\n找到 {len(search_results)} 篇相关论文:")
    for i, paper in enumerate(search_results[:5]):  # Show first 5
        title = paper.get('title', 'Unknown')
        authors = paper.get('authors', [])
        author_str = ', '.join(authors[:3]) + ('...' if len(authors) > 3 else '')
        print(f"  {i+1}. {title}")
        print(f"     作者: {author_str}")
    
    # Let user select
    while True:
        try:
            choice = input(f"\n选择论文 (1-{min(5, len(search_results))}, 或输入 'q' 退出): ").strip()
            if choice.lower() == 'q':
                return None
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < min(5, len(search_results)):
                return search_results[choice_idx]
            else:
                print(f"请输入 1-{min(5, len(search_results))} 之间的数字")
        except ValueError:
            print("请输入有效的数字")
        except KeyboardInterrupt:
            return None


def download_paper(pdf_url, paper_title):
    """Download paper from URL."""
    try:
        script_dir = Path(__file__).parent
        download_path = script_dir / "DOWNLOAD"
        
        # Create a safe filename
        import re
        safe_title = re.sub(r'[^\w\s-]', '', paper_title)
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        filename = f"{safe_title}.pdf"
        
        # Try to download
        print(f"📥 下载中: {pdf_url}")
        result = subprocess.run([
            str(download_path), pdf_url, filename
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            downloaded_path = Path.cwd() / filename
            if downloaded_path.exists():
                print(f"✅ 下载成功: {downloaded_path}")
                return str(downloaded_path), paper_title
            else:
                print("❌ 下载的文件不存在")
                return None, None
        else:
            print(f"❌ 下载失败: {result.stderr}")
            print("🔄 尝试其他下载链接...")
            return None, None
            
    except Exception as e:
        print(f"❌ 下载过程出错: {e}")
        return None, None


def process_paper_with_extract_pdf(paper_path, read_images=False):
    """Process PDF with EXTRACT_PDF tool."""
    print(f"\n📄 处理PDF文件: {paper_path}")
    
    try:
        script_dir = Path(__file__).parent
        extract_pdf_path = script_dir / "EXTRACT_PDF_PROJ" / "pdf_extractor.py"
        
        # Build command
        cmd = ["python", str(extract_pdf_path), paper_path]
        if read_images:
            cmd.append("--post")
        else:
            cmd.append("--no-image-api")
        
        print(f"🔄 执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(script_dir))
        
        if result.returncode == 0:
            print("✅ PDF处理完成")
            
            # Find the generated markdown file
            paper_name = Path(paper_path).stem
            possible_md_files = [
                Path(paper_path).parent / f"{paper_name}.md",
                Path.cwd() / f"{paper_name}.md",
                script_dir / f"{paper_name}.md"
            ]
            
            for md_file in possible_md_files:
                if md_file.exists():
                    print(f"📝 找到生成的Markdown文件: {md_file}")
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return content, str(md_file)
            
            print("⚠️  PDF处理完成，但未找到生成的Markdown文件")
            return None, None
        else:
            print(f"❌ PDF处理失败: {result.stderr}")
            return None, None
            
    except Exception as e:
        print(f"❌ PDF处理过程出错: {e}")
        return None, None


def main():
    """Main function."""
    # Check if running in interactive mode (no arguments)
    if len(sys.argv) == 1:
        print("LEARN - 智能学习系统")
        print("启动交互模式...")
        print()
        
        params = run_interactive_mode()
        if params is None:
            return 1
        
        # Generate learning content
        result = generate_learning_content(params)
        if result is None:
            return 1
        
        # 如果是no_auto_create模式，不创建文件
        if params.get("no_auto_create", False):
            print("✅ 头脑风暴完成！")
            return 0
        
        # 创建文件
        print("\n📁 创建教程文件...")
        success = create_learning_files_from_responses(
            params, 
            result['tutorial_response'], 
            result['question_response'], 
            result['prompts_and_responses']
        )
        
        if success:
            print("✅ 文件创建完成！")
            return 0
        else:
            print("❌ 文件创建失败")
            return 1
    
    # Parse direct command
    try:
        params = parse_direct_command(sys.argv[1:])
        
        # 检查参数收集是否成功
        if not params:
            return 1
        
        # Generate learning content
        result = generate_learning_content(params)
        if result is None:
            return 1
        
        # 如果是no_auto_create模式，不创建文件
        if params.get("no_auto_create", False):
            print("✅ 头脑风暴完成！")
            return 0
        
        # 创建文件
        print("\n📁 创建教程文件...")
        success = create_learning_files_from_responses(
            params, 
            result['tutorial_response'], 
            result['question_response'], 
            result['prompts_and_responses']
        )
        
        if success:
            print("✅ 文件创建完成！")
            return 0
        else:
            print("❌ 文件创建失败")
            return 1
        
    except SystemExit:
        # argparse calls sys.exit on error
        return 1
    except Exception as e:
        print(f"错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())