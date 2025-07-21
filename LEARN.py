#!/usr/bin/env python3
"""
LEARN.py - 智能学习系统
独立的学习材料生成工具，支持交互模式和直接调用
"""

import os
import sys
import argparse
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def is_run_environment(command_identifier=None):
    """Check if running in RUN environment by checking environment variables"""
    if command_identifier:
        return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
    return False

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
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing to JSON output file: {e}")
        return False

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


def check_and_confirm_overwrite(output_dir, not_default=False, no_override_material=False):
    """Check if tutorial.md or question.md exists and handle overwrite based on options."""
    tutorial_path = Path(output_dir) / "tutorial.md"
    question_path = Path(output_dir) / "question.md"
    
    existing_files = []
    if tutorial_path.exists():
        existing_files.append("tutorial.md")
    if question_path.exists():
        existing_files.append("question.md")
    
    if not existing_files:
        return True, output_dir  # No files to overwrite, use original directory
    
    # 如果指定了--no-override-material，自动重命名
    if no_override_material:
        return handle_auto_rename(output_dir)
    
    # 默认模式（--not-default未指明）：直接覆盖
    if not not_default:
        print(f"📝 默认模式：将覆盖 {output_dir} 中的现有文件: {', '.join(existing_files)}")
        return True, output_dir
    
    # 交互模式：询问用户
    print(f"\n⚠️  以下文件已存在于 {output_dir}:")
    for file in existing_files:
        print(f"  - {file}")
    
    while True:
        try:
            choice = input("\n选择操作: (o)覆盖 / (r)重命名 / (c)取消 [o/r/c]: ").strip().lower()
            if choice in ['o', 'overwrite', '覆盖']:
                return True, output_dir
            elif choice in ['r', 'rename', '重命名']:
                return handle_auto_rename(output_dir)
            elif choice in ['c', 'cancel', '取消', '']:
                return False, None
            else:
                print("请输入 o (覆盖) / r (重命名) / c (取消)")
        except KeyboardInterrupt:
            print("\n操作已取消")
            return False, None


def handle_auto_rename(output_dir):
    """Handle automatic renaming of output directory to avoid overwriting files."""
    output_path = Path(output_dir)
    base_name = output_path.name
    parent_dir = output_path.parent
    
    counter = 1
    while True:
        new_name = f"{base_name}_{counter}"
        new_path = parent_dir / new_name
        
        # 检查新目录中是否也有冲突文件
        tutorial_path = new_path / "tutorial.md"
        question_path = new_path / "question.md"
        
        if not new_path.exists() or (not tutorial_path.exists() and not question_path.exists()):
            # 创建新目录
            new_path.mkdir(parents=True, exist_ok=True)
            print(f"📁 自动重命名输出目录为: {new_path}")
            return True, str(new_path)
        
        counter += 1
        if counter > 100:  # 防止无限循环
            print("❌ 无法找到合适的目录名，请手动清理输出目录")
            return False, None


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
                try:
                    # 解析文件引用
                    expanded_topic, has_file_ref = parse_file_references(topic)
                    params["topic"] = expanded_topic
                    params["has_file_reference"] = has_file_ref
                    # 如果检测到文件引用，自动启用context模式
                    if has_file_ref:
                        params['context_mode'] = True
                        print("📄 检测到@文件引用，自动启用--context模式")
                    break
                except (FileNotFoundError, ValueError) as e:
                    print(f"❌ 错误: {e}")
                    print("请重新输入正确的主题或文件路径")
                    continue
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
    
    # Check for existing files and handle overwrite
    can_continue, final_output_dir = check_and_confirm_overwrite(
        output_dir, 
        params.get('not_default', False),
        params.get('no_override_material', False)
    )
    
    if not can_continue:
        print("操作已取消")
        return None
    
    # Update output directory if it was renamed
    if final_output_dir != output_dir:
        params["output_dir"] = final_output_dir
    
    return params


def parse_direct_command(args):
    """Parse direct command line arguments."""
    parser = argparse.ArgumentParser(description='LEARN - 智能学习系统')
    
    # Basic options
    parser.add_argument('topic', nargs='?', help='学习主题')
    parser.add_argument('-o', '--output-dir', help='输出目录')
    parser.add_argument('-m', '--mode', choices=['初学者', '中级', '高级', '专家'], 
                       default='中级', help='学习水平')
    parser.add_argument('-s', '--style', choices=['简洁明了', '详细深入', '实例丰富', '理论导向'],
                       default='详细深入', help='解释风格')
    
    # Paper options
    parser.add_argument('-p', '--paper', help='论文文件路径')
    parser.add_argument('--file', help='直接处理文件路径 (支持PDF、MD、TXT)')
    parser.add_argument('--pdf', help='直接指定PDF文件路径 (已弃用，请使用--file)')
    parser.add_argument('-u', '--url', help='论文URL')
    parser.add_argument('-d', '--description', help='论文描述/搜索关键词')
    parser.add_argument('--negative', help='负面提示词：指定不想要的内容或论文类型')
    parser.add_argument('--read-images', action='store_true', help='处理PDF中的图像、公式和表格')
    parser.add_argument('--gen-command', help='根据描述生成LEARN命令')
    
    # Model options
    parser.add_argument('--model', help='指定OpenRouter模型')
    parser.add_argument('--max-tokens', type=int, help='最大token数')
    parser.add_argument('--not-default', action='store_true', help='非默认模式，需要用户确认')
    parser.add_argument('--no-override-material', action='store_true', help='不覆盖已存在的文件，自动重命名')
    parser.add_argument('--brainstorm-only', action='store_true', help='不自动创建文件，仅生成内容')
    parser.add_argument('--context', action='store_true', help='将description视作直接context进入brainstorming，跳过论文搜索')
    
    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        return None
    
    # 检查互斥参数
    if parsed_args.context and parsed_args.brainstorm_only:
        print("❌ 错误: --context 和 --brainstorm-only 选项互斥，不能同时使用")
        print("   --context: 跳过brainstorming，直接生成教程")
        print("   --brainstorm-only: 只进行brainstorming，不生成教程")
        return None
    
    # Check if output is required for actual operation (not for --help)
    if not parsed_args.output_dir and not any(arg in ['-h', '--help'] for arg in args):
        print("错误: 需要指定输出目录 (-o/--output-dir)")
        return None
    
    # Build parameters
    params = {
        'mode': parsed_args.mode,
        'style': parsed_args.style,
        'output_dir': parsed_args.output_dir,
        'not_default': parsed_args.not_default,
        'no_override_material': parsed_args.no_override_material,
        'brainstorm_only': parsed_args.brainstorm_only,
        'context_mode': parsed_args.context
    }
    
    if parsed_args.model:
        params['selected_model'] = parsed_args.model
    if parsed_args.max_tokens:
        params['max_tokens'] = parsed_args.max_tokens
    
    # Determine type based on arguments
    if parsed_args.paper:
        params['type'] = 'paper'
        paper_path = parsed_args.paper
        # 根据文件扩展名判断类型
        if paper_path.endswith('.md'):
            params['input_type'] = 0  # Markdown file
            # 读取markdown文件内容
            try:
                with open(paper_path, 'r', encoding='utf-8') as f:
                    params['paper_content'] = f.read()
                params['paper_path'] = paper_path
            except Exception as e:
                print(f"❌ 读取markdown文件失败: {e}")
                return 1
        else:
            params['input_type'] = 1  # PDF file
            params['paper_path'] = paper_path
        params['read_images'] = parsed_args.read_images
    elif parsed_args.file or parsed_args.pdf:
        # --file选项或向后兼容的--pdf选项
        file_path = parsed_args.file or parsed_args.pdf
        params['type'] = 'paper'
        params['input_type'] = 4  # Direct file
        params['file_path'] = file_path
        params['read_images'] = parsed_args.read_images
    elif parsed_args.url:
        params['type'] = 'paper'
        params['input_type'] = 2  # URL
        params['paper_url'] = parsed_args.url
        params['read_images'] = parsed_args.read_images
    elif parsed_args.description:
        params['type'] = 'paper'
        params['input_type'] = 3  # Description/Search
        try:
            expanded_description, has_file_ref = parse_file_references(parsed_args.description)
            params['paper_description'] = expanded_description
            params['has_file_reference'] = has_file_ref
            # 如果检测到文件引用，自动启用context模式
            if has_file_ref:
                params['context_mode'] = True
                print("📄 检测到@文件引用，自动启用--context模式")
        except (FileNotFoundError, ValueError) as e:
            print(f"❌ 错误: {e}")
            return None
        params['negative_prompt'] = parsed_args.negative
        params['read_images'] = parsed_args.read_images
    elif parsed_args.topic:
        try:
            expanded_topic, has_file_ref = parse_file_references(parsed_args.topic)
            params['type'] = 'general'
            params['topic'] = expanded_topic
            params['has_file_reference'] = has_file_ref
            # 如果检测到文件引用，自动启用context模式
            if has_file_ref:
                params['context_mode'] = True
                print("📄 检测到@文件引用，自动启用--context模式")
        except (FileNotFoundError, ValueError) as e:
            print(f"❌ 错误: {e}")
            return None
    else:
        print("错误：必须指定学习主题或论文信息")
        return None
    
    # Check for existing files and handle overwrite in direct mode
    if params['output_dir']:
        can_continue, final_output_dir = check_and_confirm_overwrite(
            params['output_dir'], 
            params.get('not_default', False),
            params.get('no_override_material', False)
        )
        
        if not can_continue:
            print("操作已取消")
            return None
        
        # Update output directory if it was renamed
        if final_output_dir != params['output_dir']:
            params['output_dir'] = final_output_dir
    
    return params


def get_openrouter_models():
    """Get available OpenRouter models."""
    try:
        script_dir = Path(__file__).parent
        openrouter_data_file = script_dir / "OPENROUTER_PROJ" / "openrouter_models.json"
        
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
    
    # Auto-select for default mode (use "auto" for automatic model selection)
    if not params.get('not_default', False):
        selected_model = "auto"  # 使用auto模式自动选择
        max_tokens = 4000
        print(f"🚀 默认模式：自动模型选择")
        return selected_model, max_tokens
    
    # Interactive mode - let user choose
    print(f"\n📋 可用模型列表:")
    print("=" * 80)
    for i, model in enumerate(models):
        model_info = model_details.get(model, {})
        input_cost = model_info.get('input_cost_per_1m', 0)
        output_cost = model_info.get('output_cost_per_1m', 0)
        context_length = model_info.get('context_length', 0)
        
        print(f" {i+1}. {model}")
        print(f"    📊 费率: 输入 ${input_cost:.2f}/1M, 输出 ${output_cost:.2f}/1M")
        print(f"    📏 上下文长度: {context_length:,} tokens")
        print()
    
    print(f" {len(models)+1}. auto (自动选择最佳模型)")
    print("    🤖 系统会按优先级自动选择可用模型")
    print()
    
    while True:
        try:
            choice = input(f"选择模型 (1-{len(models)+1}, 默认: auto): ").strip()
            
            if not choice or choice.lower() == 'auto':
                selected_model = "auto"
                break
            
            choice_num = int(choice)
            if choice_num == len(models) + 1:  # auto选项
                selected_model = "auto"
                break
            elif 1 <= choice_num <= len(models):
                selected_model = models[choice_num - 1]
                break
            else:
                print(f"❌ 请输入1-{len(models)+1}之间的数字")
                
        except ValueError:
            print("❌ 请输入有效的数字")
        except KeyboardInterrupt:
            print("\n❌ 用户取消")
            return None, None
    
    # Set max tokens based on model
    if selected_model == "auto":
        max_tokens = 40960  # 更高的默认值，会在实际调用时动态调整
        print(f"🤖 选择自动模式")
    else:
        model_info = model_details.get(selected_model, {})
        context_length = model_info.get('context_length', 4000)
        max_tokens = context_length // 4  # Use 1/4 of context length
        print(f"✅ 选择模型: {selected_model} (max_tokens: {max_tokens})")
    
    return selected_model, max_tokens


def generate_content_structure_prompt(params):
    """Generate prompt for content structure brainstorming."""
    if params["type"] == "general":
        topic = params['topic']
        mode = params['mode']
        style = params['style']
        
        # 检查是否包含文件引用
        if params.get("has_file_reference", False):
            print("📄 检测到文件引用，将基于文件内容创建教程")
            return f'基于以下内容创建详细的学习教程结构，适合{mode}水平的学习者，采用{style}的解释风格：\n\n{topic}'
        else:
            return f'请为"{topic}"创建详细的学习教程结构，适合{mode}水平的学习者，采用{style}的解释风格。'
        
    elif params["type"] == "paper":
        mode = params['mode']
        style = params['style']
        
        # 首先进行模型选择（如果还没有选择的话）
        if not params.get("selected_model"):
            selected_model, max_tokens = select_openrouter_model(params)
            if not selected_model:
                print("❌ 未选择模型")
                return None
            
            # Store selected model info in params
            params["selected_model"] = selected_model
            params["max_tokens"] = max_tokens
        
        # For paper type, prepare content first
        paper_content, paper_path, token_count = prepare_paper_content(params)
        if not paper_content:
            return None
            
        # Store prepared content in params
        params['paper_content'] = paper_content
        params['paper_path'] = paper_path
        params['token_count'] = token_count
        
        # Check if content is too long and needs summarization
        # 获取动态max_tokens设置
        dynamic_max_tokens = params.get("max_tokens", 40960)  # 默认值
        
        # 如果是自动模式，使用更合理的阈值（基于deepseek模型的context length）
        if params.get("selected_model") == "auto" or not params.get("selected_model"):
            # 自动模式：使用deepseek模型的实际context length计算阈值
            deepseek_context_length = 163840
            dynamic_max_tokens = deepseek_context_length // 4  # 40960
            content_threshold = dynamic_max_tokens  # 直接使用max_tokens作为阈值
        else:
            # 直接使用max_tokens作为阈值
            content_threshold = dynamic_max_tokens
        
        if token_count > content_threshold:
            print(f"⚠️  论文内容较长 ({token_count:,} tokens)，超出推荐处理长度 ({content_threshold:,} tokens)")
            
            # 检查是否为默认模式
            if params.get("not_default", False):
                # 非默认模式：询问用户选择
                approach_choice = interactive_select(
                    "内容处理方式:",
                    ["直接使用 (可能超出模型限制)", "智能摘要 (推荐)", "手动截取前部分"]
                )
            else:
                # 默认模式：自动选择第一个选项
                print("内容处理方式:")
                print("  1. 直接使用 (可能超出模型限制)")
                print("  2. 智能摘要 (推荐)")
                print("  3. 手动截取前部分")
                print("Choose (1-3, default: 1): 1")
                print("Selected: 直接使用 (可能超出模型限制)")
                approach_choice = 0  # 对应第一个选项
            
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
            
        # 处理模型选择
        if not model or model == "auto":
            print("🤖 使用自动模型选择", file=sys.stderr)
            # 使用call_openrouter_with_auto_model进行自动选择
            result = call_openrouter_with_auto_model(prompt, model="auto")
            
            if result['success']:
                content = result['content']
                usage_info = {
                    'input_tokens': result['usage']['input_tokens'],
                    'output_tokens': result['usage']['output_tokens'],
                    'total_tokens': result['usage']['total_tokens'],
                    'cost': result['cost'],
                    'model': result['model'],
                    'api_duration': 0  # call_openrouter_with_auto_model doesn't return duration
                }
                return content, usage_info
            else:
                return f"ERROR: {result['error']}", {"error": result['error']}
        
        else:
            # 使用指定模型
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
                result = subprocess.run(
                    cmd,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    timeout=120,  # 2分钟超时
                    encoding='utf-8'
                )
                
                # 记录结束时间
                end_time = time.time()
                api_duration = end_time - start_time
                
                # 解析JSON响应
                if result.returncode == 0:
                    try:
                        response_data = json.loads(result.stdout)
                        
                        if response_data.get('success'):
                            content = response_data.get('content', '')
                            
                            # 提取token使用信息
                            usage = response_data.get('usage', {})
                            cost = response_data.get('cost', 0)
                            model_used = response_data.get('model', model)
                            
                            usage_info = {
                                'input_tokens': usage.get('input_tokens', 0),
                                'output_tokens': usage.get('output_tokens', 0),
                                'total_tokens': usage.get('total_tokens', 0),
                                'cost': cost,
                                'model': model_used,
                                'api_duration': api_duration
                            }
                            
                            print(f"✅ OpenRouter API调用成功 (耗时: {api_duration:.2f}秒)", file=sys.stderr)
                            return content, usage_info
                        else:
                            error_msg = response_data.get('error', 'Unknown error')
                            print(f"❌ OpenRouter API返回错误: {error_msg}", file=sys.stderr)
                            return f"ERROR: {error_msg}", {"error": error_msg}
                            
                    except json.JSONDecodeError as e:
                        print(f"❌ 解析OpenRouter响应失败: {e}", file=sys.stderr)
                        print(f"原始响应: {result.stdout[:500]}...", file=sys.stderr)
                        return f"ERROR: JSON解析失败: {e}", {"error": f"JSON解析失败: {e}"}
                else:
                    error_msg = result.stderr or "命令执行失败"
                    print(f"❌ OpenRouter命令执行失败: {error_msg}", file=sys.stderr)
                    return f"ERROR: {error_msg}", {"error": error_msg}
                    
            except subprocess.TimeoutExpired:
                print("❌ OpenRouter API调用超时", file=sys.stderr)
                return "ERROR: API调用超时", {"error": "API调用超时"}
            except Exception as e:
                print(f"❌ OpenRouter API调用异常: {e}", file=sys.stderr)
                return f"ERROR: {e}", {"error": str(e)}
        
    except Exception as e:
        print(f"❌ call_openrouter_for_structure异常: {e}", file=sys.stderr)
        return f"ERROR: {e}", {"error": str(e)}


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
                print(f"📊 Token使用: {token_info.get('total_tokens', 0)} tokens - 模型: {model_used} - 费用: ${cost:.6f} - 用时: {token_info.get('api_duration', 0):.2f}秒")
        
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
    
    # 检查是否跳过brainstorming（只有context模式才跳过）
    if params.get("context_mode", False):
        print("\n⏭️  跳过头脑风暴步骤（--context模式）")
        # 直接准备论文内容用于后续步骤
        if params["type"] == "paper":
            structure_prompt = generate_content_structure_prompt(params)
            if structure_prompt is None:
                print("❌ 内容准备失败，无法继续生成学习材料")
                return None
    else:
        print("\n📝 第1步：询问AI进行头脑风暴...")
        structure_prompt = generate_content_structure_prompt(params)
        
        # Check if content preparation failed (e.g., PDF extraction failed)
        if structure_prompt is None and params["type"] == "paper":
            print("❌ 内容准备失败，无法继续生成学习材料")
            return None
    
    if structure_prompt and not params.get("context_mode", False):  # Brainstorming was requested
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
        
        # 如果是brainstorm_only模式，只返回brainstorming结果
        if params.get("brainstorm_only", False):
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
                params["brainstorm_only"] = True
    
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
    if params.get("brainstorm_only", False):
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
        
        # 检查是否为context模式（包括文件引用或手动启用）
        if params.get("context_mode", False):
            print("📄 Context模式：直接使用description内容而非搜索论文")
            # 直接使用description中的内容
            paper_content = paper_description
            paper_path = "context_content"
            # 估算token数量
            token_count = len(paper_content) // 4  # 粗略估算
            print(f"✅ Context内容处理完成，内容长度: {token_count} tokens")
        else:
            paper_content, downloaded_path, token_count = search_and_download_paper(paper_description, params)
            if paper_content:
                print(f"✅ 论文处理完成，内容长度: {token_count} tokens")
                paper_path = downloaded_path  # PDF路径
            else:
                print("❌ 无法找到或下载论文")
            return None, None, 0
    
    elif input_type == 4:  # Direct file
        file_path = params.get("file_path") or params.get("pdf_path")  # 向后兼容
        file_path_obj = Path(file_path)
        print(f"📄 直接处理文件: {file_path}")
        
        # 检查文件是否存在
        if not file_path_obj.exists():
            print(f"❌ 文件不存在: {file_path}")
            return None, None, 0
        
        # 根据文件类型处理
        file_extension = file_path_obj.suffix.lower()
        
        if file_extension == '.pdf':
            # 使用EXTRACT_PDF提取PDF内容
            markdown_path = extract_pdf_content(file_path, params)
            if not markdown_path:
                print("❌ PDF内容提取失败")
                return None, None, 0
            
            # 读取提取的markdown内容
            try:
                with open(markdown_path, 'r', encoding='utf-8') as f:
                    paper_content = f.read()
            except Exception as e:
                print(f"❌ 读取提取的内容失败: {e}")
                return None, None, 0
            paper_path = markdown_path
            
        elif file_extension in ['.md', '.txt']:
            # 直接读取markdown或文本文件
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    paper_content = f.read()
                paper_path = file_path
                print(f"✅ 直接读取{file_extension}文件内容完成")
            except Exception as e:
                print(f"❌ 读取文件失败: {e}")
                return None, None, 0
        else:
            print(f"❌ 不支持的文件类型: {file_extension}，支持 .pdf、.md、.txt")
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


def call_openrouter_with_auto_model(prompt, model="auto", max_retries=3):
    """
    调用OPENROUTER API，支持自动模型选择
    
    Args:
        prompt: 提示词
        model: 模型ID，"auto"表示自动选择
        max_retries: 最大重试次数
        
    Returns:
        API调用结果
    """
    try:
        from OPENROUTER import call_openrouter_api, get_useable_models
        
        if model == "auto":
            # 获取可用模型列表，按优先级排序
            useable_models = get_useable_models()
            if not useable_models:
                print("❌ 没有可用的模型")
                return {"success": False, "error": "No useable models available"}
            
            # 尝试按顺序调用模型
            for i, model_id in enumerate(useable_models):
                print(f"🤖 尝试模型 {i+1}/{len(useable_models)}: {model_id}")
                
                try:
                    result = call_openrouter_api(prompt, model=model_id)
                    if result['success']:
                        print(f"✅ 模型 {model_id} 调用成功")
                        return result
                    else:
                        print(f"⚠️  模型 {model_id} 调用失败: {result.get('error', 'Unknown error')}")
                        if i < len(useable_models) - 1:  # 不是最后一个模型
                            print(f"🔄 尝试下一个模型...")
                            continue
                        
                except Exception as e:
                    print(f"⚠️  模型 {model_id} 调用异常: {e}")
                    if i < len(useable_models) - 1:
                        print(f"🔄 尝试下一个模型...")
                        continue
            
            # 所有模型都失败了
            return {"success": False, "error": "All models failed"}
        
        else:
            # 使用指定模型
            print(f"🎯 使用指定模型: {model}")
            return call_openrouter_api(prompt, model=model)
            
    except Exception as e:
        return {"success": False, "error": f"API调用异常: {e}"}


def optimize_search_query_with_ai(user_description):
    """使用AI优化搜索查询，将用户描述转换为更好的英文搜索词"""
    try:
        prompt = f"""你是一个学术搜索专家。用户想要搜索以下主题的论文：

用户描述：{user_description}

请帮助优化这个搜索查询，生成3-5个最佳的英文搜索关键词或短语，用于在学术数据库中搜索相关论文。

要求：
1. 使用英文关键词
2. 包含核心技术术语
3. 避免过于宽泛或过于具体
4. 适合在arXiv、Google Scholar等平台搜索

请只返回搜索关键词，用逗号分隔，不要其他解释。

例如：
- 如果用户说"3DGS mesh reconstruction"，返回："3D Gaussian Splatting, mesh reconstruction, neural surface reconstruction, 3DGS geometry"
- 如果用户说"机器学习分类算法"，返回："machine learning classification, classification algorithms, supervised learning"

搜索关键词："""

        print("🤖 正在优化搜索查询...")
        result = call_openrouter_with_auto_model(prompt, model="auto")
        
        if result['success']:
            optimized_query = result['content'].strip()
            print(f"✅ 优化后的搜索词: {optimized_query}")
            return optimized_query
        else:
            print(f"⚠️  AI优化失败，使用原始描述: {result['error']}")
            return user_description
            
    except Exception as e:
        print(f"⚠️  AI优化出错，使用原始描述: {e}")
        return user_description


def select_best_papers_with_ai(search_results, user_description, max_papers=3, negative_prompt=None):
    """使用AI从搜索结果中选择最相关的论文"""
    try:
        # 准备论文信息
        papers_info = []
        for i, paper in enumerate(search_results[:10]):  # 最多分析前10篇
            info = f"""论文 {i+1}:
标题: {paper.get('title', 'Unknown')}
作者: {', '.join(paper.get('authors', [])[:3])}
摘要: {paper.get('abstract', 'No abstract')[:300]}...
发表时间: {paper.get('published', 'Unknown')}
引用量: {paper.get('citation_count', 'Unknown')}
来源: {paper.get('source', 'Unknown')}
"""
            papers_info.append(info)
        
        papers_text = '\n\n'.join(papers_info)
        
        # 构建基础prompt
        prompt = f"""你是一个学术研究专家。用户正在寻找以下主题的论文：

用户需求：{user_description}

以下是搜索到的论文列表：

{papers_text}

请从这些论文中选择最相关和最有价值的{max_papers}篇论文，考虑以下因素：
1. 与用户需求的相关性
2. 论文的质量和影响力（引用量、发表时间等）
3. 研究的新颖性和重要性"""

        # 如果有negative prompt，添加到指令中
        if negative_prompt:
            prompt += f"""

特别注意：请避免选择与以下描述相关的论文：{negative_prompt}
优先选择与用户需求直接相关且不包含上述不想要内容的论文。"""

        prompt += f"""

请返回选择的论文编号（1-{len(papers_info)}），用逗号分隔。
例如：如果选择第1、3、5篇论文，返回：1,3,5

只返回编号，不要其他解释："""

        print("🤖 正在智能筛选最佳论文...")
        result = call_openrouter_with_auto_model(prompt, model="auto")
        
        if result['success']:
            selected_indices = result['content'].strip()
            print(f"✅ AI推荐论文: {selected_indices}")
            
            # 解析选择的论文编号
            try:
                indices = [int(x.strip()) - 1 for x in selected_indices.split(',')]  # 转换为0-based索引
                selected_papers = [search_results[i] for i in indices if 0 <= i < len(search_results)]
                return selected_papers[:max_papers]
            except (ValueError, IndexError) as e:
                print(f"⚠️  解析AI选择失败: {e}，返回前{max_papers}篇")
                return search_results[:max_papers]
        else:
            print(f"⚠️  AI筛选失败，返回前{max_papers}篇: {result['error']}")
            return search_results[:max_papers]
            
    except Exception as e:
        print(f"⚠️  AI筛选出错，返回前{max_papers}篇: {e}")
        return search_results[:max_papers]


def process_paper_with_extract_pdf(paper_path, read_images=False):
    """使用EXTRACT_PDF处理PDF文件，返回内容和处理后的路径"""
    try:
        import subprocess
        from pathlib import Path
        
        paper_path = Path(paper_path)
        if not paper_path.exists():
            print(f"❌ PDF文件不存在: {paper_path}")
            return None, None
        
        # 使用EXTRACT_PDF处理PDF
        extract_pdf_path = Path(__file__).parent / "EXTRACT_PDF.py"
        if not extract_pdf_path.exists():
            print("❌ EXTRACT_PDF.py不存在")
            return None, None
        
        print(f"🔄 使用EXTRACT_PDF处理: {paper_path.name}")
        
        # 构建命令
        cmd = ["/usr/bin/python3", str(extract_pdf_path)]
        cmd.append(str(paper_path))
        
        if not read_images:
            cmd.extend(["--engine", "basic-asyn"])
        
        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"❌ EXTRACT_PDF处理失败: {result.stderr}")
            return None, None
        
        # 查找生成的markdown文件
        md_path = paper_path.with_suffix('.md')
        if md_path.exists():
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"✅ PDF处理完成: {md_path.name}")
            return content, str(md_path)
        else:
            print("❌ 未找到生成的markdown文件")
            return None, None
            
    except Exception as e:
        print(f"❌ 处理PDF时发生错误: {e}")
        return None, None


def search_and_download_paper(paper_description, params=None):
    """Search for paper and download if found."""
    print(f"\n🔍 搜索论文: {paper_description}")
    
    try:
        # 步骤1: 使用AI优化搜索查询
        optimized_query = optimize_search_query_with_ai(paper_description)
        
        script_dir = Path(__file__).parent
        search_paper_path = script_dir / "SEARCH_PAPER"
        
        # 步骤2: 使用优化后的查询搜索论文
        result = subprocess.run([
            str(search_paper_path), optimized_query, "--max-results", "10"  # 增加搜索结果数量
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ 搜索失败: {result.stderr}")
            return None, None, 0
            
        print("✅ 搜索完成，正在解析结果...")
        
        # 步骤3: 解析搜索结果
        search_results = parse_search_results()
        if not search_results:
            print("❌ 未找到相关论文")
            return None, None, 0

        print(f"\n找到 {len(search_results)} 篇相关论文")
        
        # 步骤4: 使用AI筛选最佳论文
        selected_papers = select_best_papers_with_ai(
            search_results, 
            paper_description, 
            max_papers=3, 
            negative_prompt=params.get('negative_prompt') if params else None
        )
        
        if not selected_papers:
            print("❌ AI筛选后无可用论文")
            return None, None, 0
        
        # 步骤5: 显示AI推荐的论文供用户选择
        print(f"\n🎯 AI推荐的{len(selected_papers)}篇最佳论文:")
        for i, paper in enumerate(selected_papers):
            title = paper.get('title', 'Unknown')
            authors = paper.get('authors', [])
            author_str = ', '.join(authors[:3]) + ('...' if len(authors) > 3 else '')
            citation_count = paper.get('citation_count', 'Unknown')
            print(f"  {i+1}. {title}")
            print(f"     作者: {author_str}")
            print(f"     引用量: {citation_count}")
            print()
        
        # 步骤6: 让用户选择或自动选择第一篇
        if len(selected_papers) == 1:
            selected_paper = selected_papers[0]
            print(f"✅ 自动选择唯一推荐论文")
        else:
            # 简化选择：自动选择第一篇（AI推荐的最佳论文）
            selected_paper = selected_papers[0]
            print(f"✅ 自动选择AI推荐的最佳论文: {selected_paper.get('title', 'Unknown')}")

        # 步骤7: 尝试下载论文
        pdf_url = selected_paper.get('pdf_url')
        if not pdf_url:
            print("❌ 未找到PDF下载链接")
            return None, None, 0
        
        print(f"\n📥 尝试下载论文: {selected_paper.get('title', 'Unknown')}")
        downloaded_path, original_title = download_paper(
            pdf_url, 
            selected_paper.get('title', 'paper'),
            output_dir=params.get('output_dir') if params else None
        )
        
        if not downloaded_path:
            print("❌ 论文下载失败")
            return None, None, 0
        
        # 步骤8: 使用AI给PDF重命名为简洁明了的名字
        print("\n🤖 正在为PDF生成简洁明了的文件名...")
        new_filename = generate_simple_filename_with_ai(selected_paper, paper_description)
        
        # 重命名PDF文件
        downloaded_pdf_path = Path(downloaded_path)
        new_pdf_path = downloaded_pdf_path.parent / f"{new_filename}.pdf"
        
        try:
            downloaded_pdf_path.rename(new_pdf_path)
            print(f"✅ PDF已重命名为: {new_pdf_path.name}")
            downloaded_path = str(new_pdf_path)
        except Exception as e:
            print(f"⚠️  重命名失败，使用原文件名: {e}")
        
        # 步骤9: 使用EXTRACT_PDF提取论文内容
        print(f"\n📄 正在提取PDF内容...")
        markdown_path = extract_pdf_content(downloaded_path, params)
        
        if not markdown_path:
            print("❌ PDF内容提取失败")
            return None, None, 0
        
        # 步骤10: 读取提取的markdown内容
        try:
            with open(markdown_path, 'r', encoding='utf-8') as f:
                paper_content = f.read()
            
            print(f"✅ 论文内容提取完成: {markdown_path}")
            token_count = len(paper_content.split())  # 简单的token估算
            print(f"📊 提取内容长度: {token_count} tokens")
            
            # 检查内容长度，如果太少就中断
            min_content_length = 1000  # 最少1000个字符
            if len(paper_content.strip()) < min_content_length:
                print(f"❌ 论文内容太少（{len(paper_content)}字符 < {min_content_length}），可能提取失败")
                raise Exception(f"论文内容提取不完整：仅有{len(paper_content)}字符，少于最小要求{min_content_length}字符")
            
            return paper_content, downloaded_path, token_count
            
        except Exception as e:
            print(f"❌ 读取markdown文件失败: {e}")
            return None, None, 0
            
    except Exception as e:
        print(f"❌ 搜索过程出错: {e}")
        return None, None, 0


def generate_simple_filename_with_ai(paper_info, user_description):
    """使用AI为论文生成简洁明了的文件名"""
    try:
        title = paper_info.get('title', 'Unknown')
        authors = paper_info.get('authors', [])
        
        prompt = f"""请为以下学术论文生成一个简洁明了的英文文件名，用于保存PDF文件。

论文信息：
标题: {title}
作者: {', '.join(authors[:3])}
用户搜索描述: {user_description}

要求：
1. 文件名应该简洁明了，不超过50个字符
2. 只使用英文字母、数字、下划线和连字符
3. 避免特殊符号和空格
4. 体现论文的核心主题
5. 易于理解和识别

例如：
- "3D Gaussian Splatting for Real-Time Radiance Field Rendering" -> "3DGS_Real_Time_Rendering"
- "Neural Radiance Fields" -> "NeRF"
- "Instant Neural Graphics Primitives" -> "Instant_NGP"

请只返回文件名（不包含.pdf扩展名），不要其他解释："""

        result = call_openrouter_with_auto_model(prompt, model="auto")
        
        if result['success']:
            filename = result['content'].strip()
            # 清理文件名，确保符合文件系统要求
            import re
            filename = re.sub(r'[^\w\-_]', '', filename)
            filename = re.sub(r'[-_]+', '_', filename)
            
            if len(filename) > 50:
                filename = filename[:50]
            
            print(f"✅ AI生成的文件名: {filename}")
            return filename
        else:
            print(f"⚠️  AI生成文件名失败: {result['error']}")
            # 使用简化的标题作为备选
            import re
            safe_title = re.sub(r'[^\w\s-]', '', title)
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            return safe_title[:30]
            
    except Exception as e:
        print(f"⚠️  生成文件名出错: {e}")
        return "paper"


def extract_pdf_content(pdf_path, params=None):
    """使用EXTRACT_PDF提取PDF内容"""
    try:
        script_dir = Path(__file__).parent
        extract_pdf_path = script_dir / "EXTRACT_PDF"
        
        # 构建EXTRACT_PDF命令
        cmd = [str(extract_pdf_path), str(pdf_path)]
        
        # 根据LEARN参数决定是否处理图像
        if params and params.get('read_images', False):
            print("🖼️  启用图像、公式和表格处理")
            cmd.extend(["--engine", "full"])  # 使用full模式
        else:
            print("📝 仅提取文本内容（跳过图像处理）")
            cmd.extend(["--engine", "basic-asyn"])  # 使用basic-asyn模式，更快的异步处理
        
        print(f"🔄 执行命令: {' '.join(cmd)}")
        
        # 执行EXTRACT_PDF命令
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=86400)  # 1 day timeout (dummy)
        
        if result.returncode == 0:
            # 查找生成的markdown文件
            pdf_path_obj = Path(pdf_path)
            expected_md_path = pdf_path_obj.with_suffix('.md')
            
            if expected_md_path.exists():
                print(f"✅ PDF内容提取成功: {expected_md_path}")
                return str(expected_md_path)
            else:
                print(f"❌ 未找到预期的markdown文件: {expected_md_path}")
                # 尝试查找其他可能的markdown文件
                possible_paths = [
                    pdf_path_obj.parent / f"{pdf_path_obj.stem}.md",
                    Path.cwd() / f"{pdf_path_obj.stem}.md"
                ]
                for path in possible_paths:
                    if path.exists():
                        print(f"✅ 找到markdown文件: {path}")
                        return str(path)
                return None
        else:
            print(f"❌ EXTRACT_PDF执行失败:")
            print(f"   返回码: {result.returncode}")
            print(f"   标准输出: {result.stdout}")
            print(f"   错误输出: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("❌ PDF提取超时")
        return None
    except Exception as e:
        print(f"❌ PDF提取出错: {e}")
        return None


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
        
        # 确保返回的是列表格式
        if isinstance(search_results, dict):
            # 如果是字典格式，尝试提取论文列表
            if 'papers' in search_results:
                search_results = search_results['papers']
            elif 'results' in search_results:
                search_results = search_results['results']
            else:
                # 如果字典中没有明确的论文列表，将整个字典作为单个结果
                search_results = [search_results]
        
        # 确保是列表且不为空
        if isinstance(search_results, list) and search_results:
            return search_results
        else:
            return None
            
    except Exception as e:
        print(f"❌ 解析搜索结果失败: {e}")
        return None


def download_paper(pdf_url, paper_title, output_dir=None):
    """Download paper from URL."""
    try:
        script_dir = Path(__file__).parent
        download_path = script_dir / "DOWNLOAD"
        
        # Create a safe filename
        import re
        safe_title = re.sub(r'[^\w\s-]', '', paper_title)
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        filename = f"{safe_title}.pdf"
        
        # Determine download directory
        if output_dir:
            download_dir = Path(output_dir)
            download_dir.mkdir(parents=True, exist_ok=True)
        else:
            download_dir = Path.cwd()
        
        target_path = download_dir / filename
        
        # Try to download
        print(f"📥 下载中: {pdf_url}")
        print(f"📁 目标目录: {download_dir}")
        
        result = subprocess.run([
            str(download_path), pdf_url, str(target_path)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            if target_path.exists():
                print(f"✅ 下载成功: {target_path}")
                return str(target_path), paper_title
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


def parse_file_references(text):
    """解析文本中的@"文件路径"引用，展开为文件内容
    
    Returns:
        tuple: (expanded_text, has_file_reference)
    """
    import re
    from pathlib import Path
    
    # 匹配 @"文件路径" 模式
    pattern = r'@"([^"]+)"'
    
    def clean_markdown_content(content, file_path):
        """清理markdown内容中的placeholder和本地图片链接"""
        # 移除各种类型的placeholder
        # [placeholder: xxx], [image: xxx], [formula: xxx], [table: xxx]
        content = re.sub(r'\[(?:placeholder|image|formula|table):\s*[^\]]*\]\s*\n?', '', content, flags=re.IGNORECASE)
        
        # 移除包含"placeholder"的整行
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            if '[placeholder:' not in line.lower() and '[image:' not in line.lower() and '[formula:' not in line.lower() and '[table:' not in line.lower() and '[formula:' not in line.lower():
                cleaned_lines.append(line)
        content = '\n'.join(cleaned_lines)
        
        # 移除图片hash ID（通常是32-64位十六进制字符串）
        content = re.sub(r'\b[a-f0-9]{32,64}\b\s*\n?', '', content)
        
        # 移除图片引用（包含hash的）
        content = re.sub(r'!\[[^\]]*\]\([^)]*[a-f0-9]{32,64}[^)]*\)\s*\n?', '', content)
        
        # 移除本地图片引用 ![...](images/xxx) 或 ![...](./images/xxx) 等
        # 保留网络图片链接 (http/https)
        content = re.sub(r'!\[[^\]]*\]\((?!https?://)[^)]*\)\s*\n?', '', content)
        
        # 移除错误信息占位符
        content = re.sub(r'\[message:\s*[^\]]*\]\s*\n?', '', content, flags=re.IGNORECASE)
        
        # 移除包含特定关键词的行（更全面的清理）
        forbidden_keywords = ['image_', 'formula_', 'table_', '图片处理失败', 'images/']
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            line_lower = line.lower()
            if not any(keyword.lower() in line_lower for keyword in forbidden_keywords):
                cleaned_lines.append(line)
        content = '\n'.join(cleaned_lines)
        
        # 清理多余的空行（3个或更多连续空行压缩为2个）
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 移除行首尾空白但保留段落结构
        lines = content.split('\n')
        cleaned_lines = [line.rstrip() for line in lines]
        content = '\n'.join(cleaned_lines)
        
        return content.strip()
    
    def replace_reference(match):
        file_path = match.group(1)
        try:
            path_obj = Path(file_path).expanduser().resolve()
            
            # 检查文件是否存在
            if not path_obj.exists():
                raise FileNotFoundError(f"@符号引用的文件不存在: {file_path}")
                
            # 检查是否是符号链接或其他特殊情况
            if not path_obj.is_file():
                raise ValueError(f"@符号引用的路径不是有效文件: {file_path}")
            
            # 检查文件类型
            allowed_extensions = {'.txt', '.md', '.pdf'}
            if path_obj.suffix.lower() not in allowed_extensions:
                return f"[不支持的文件类型: {file_path}，仅支持 .txt、.md 和 .pdf 文件]"
            
            # 读取文件内容
            try:
                if path_obj.suffix.lower() == '.pdf':
                    # 处理PDF文件 - 使用basic引擎进行解析
                    import tempfile
                    import subprocess
                    
                    print(f"📎 正在解析PDF文件: {file_path} (使用basic引擎)")
                    
                    # 在/tmp中创建临时目录进行PDF解析
                    with tempfile.TemporaryDirectory(prefix='learn_pdf_', dir='/tmp') as temp_dir:
                        temp_dir_path = Path(temp_dir)
                        
                        # 调用EXTRACT_PDF进行解析
                        extract_cmd = [
                            'python3', str(Path(__file__).parent / 'EXTRACT_PDF.py'),
                            str(path_obj),
                            '--engine', 'basic-asyn',  # 使用basic引擎，不进行图像处理
                            '--output', str(temp_dir_path)
                        ]
                        
                        try:
                            result = subprocess.run(extract_cmd, capture_output=True, text=True, timeout=60)
                            if result.returncode == 0:
                                # 查找生成的markdown文件
                                md_files = list(temp_dir_path.glob('*.md'))
                                if md_files:
                                    md_file = md_files[0]
                                    with open(md_file, 'r', encoding='utf-8') as f:
                                        content = f.read()
                                    
                                    # 清理PDF解析生成的markdown内容
                                    original_length = len(content)
                                    content = clean_markdown_content(content, file_path)
                                    cleaned_length = len(content)
                                    
                                    tokens_saved = (original_length - cleaned_length) // 4
                                    print(f"📎 PDF解析完成: {file_path} ({cleaned_length}字符，清理后节省约{tokens_saved} tokens)")
                                    
                                    return f"\n\n--- 引用PDF文件: {file_path} ---\n{content}\n--- 文件引用结束 ---\n"
                                else:
                                    return f"[PDF解析失败: {file_path} - 未生成markdown文件]"
                            else:
                                return f"[PDF解析失败: {file_path} - {result.stderr}]"
                        except subprocess.TimeoutExpired:
                            return f"[PDF解析超时: {file_path}]"
                        except Exception as e:
                            return f"[PDF解析出错: {file_path} - {str(e)}]"
                
                else:
                    # 处理文本文件
                    with open(path_obj, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 如果是markdown文件，进行智能清理
                    if path_obj.suffix.lower() == '.md':
                        original_length = len(content)
                        content = clean_markdown_content(content, file_path)
                        cleaned_length = len(content)
                        
                        if original_length > cleaned_length:
                            tokens_saved = (original_length - cleaned_length) // 4  # 粗略估算节省的tokens
                            print(f"📎 展开文件引用: {file_path} ({cleaned_length}字符，清理后节省约{tokens_saved} tokens)")
                        else:
                            print(f"📎 展开文件引用: {file_path} ({cleaned_length}字符)")
                    else:
                        print(f"📎 展开文件引用: {file_path} ({len(content)}字符)")
                    
                    return f"\n\n--- 引用文件: {file_path} ---\n{content}\n--- 文件引用结束 ---\n"
                
            except (FileNotFoundError, ValueError):
                # 重新抛出文件不存在或路径无效的异常
                raise
            except Exception as e:
                return f"[读取文件失败: {file_path} - {str(e)}]"
                
        except (FileNotFoundError, ValueError):
            # 重新抛出文件不存在或路径无效的异常
            raise
        except Exception as e:
            return f"[文件路径解析失败: {file_path} - {str(e)}]"
    
    # 替换所有文件引用
    expanded_text = re.sub(pattern, replace_reference, text)
    
    # 检查是否有引用被展开
    has_file_reference = expanded_text != text
    if has_file_reference:
        print("🔗 检测到文件引用，已自动展开并清理无用内容")
    
    return expanded_text, has_file_reference


def generate_learn_command(description):
    """根据用户描述生成LEARN命令"""
    try:
        # 读取LEARN.md文档作为参考
        script_dir = Path(__file__).parent
        learn_md_path = script_dir / "LEARN.md"
        
        learn_doc = ""
        if learn_md_path.exists():
            with open(learn_md_path, 'r', encoding='utf-8') as f:
                learn_doc = f.read()
        
        # 构建prompt
        prompt = f"""你是一个LEARN工具的专家助手。请根据用户的描述生成对应的LEARN命令。

LEARN工具文档：
{learn_doc}

用户描述：{description}

请分析用户的需求，并生成最合适的LEARN命令。考虑以下因素：
1. 用户是否需要学习特定论文、主题还是通用知识
2. 学习水平（初学者、中级、高级、专家）
3. 解释风格（简洁明了、详细深入、实例丰富、理论导向）
4. 是否需要特殊选项（如--pdf、--description、--negative、--read-images等）
5. 输出目录建议

请直接返回完整的LEARN命令，以"LEARN"开头，不要包含其他解释。
如果需要文件路径，请使用占位符如"/path/to/file"。

示例格式：
LEARN -o ~/tutorials -m 初学者 -s 简洁明了 "Python基础编程"
LEARN -o ~/tutorials -m 中级 --pdf "/path/to/paper.pdf"
LEARN -o ~/tutorials -m 高级 -d "深度学习" --negative "GAN"

生成的命令："""

        print("🤖 正在分析用户需求，生成LEARN命令...")
        result = call_openrouter_with_auto_model(prompt, model="auto")
        
        if result['success']:
            command = result['content'].strip()
            print(f"\n✅ 生成的LEARN命令：")
            print(f"```bash")
            print(f"{command}")
            print(f"```")
            return True
        else:
            print(f"❌ 命令生成失败: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ 生成命令时出错: {e}")
        return False


def main():
    """Main function."""
    # 获取command_identifier
    args = sys.argv[1:]
    command_identifier = None
    
    # 检查是否被RUN调用（第一个参数是command_identifier）
    if args and is_run_environment(args[0]):
        command_identifier = args[0]
        args = args[1:]  # 移除command_identifier，保留实际参数
        # 重新构建sys.argv以供argparse使用
        sys.argv = [sys.argv[0]] + args
    
    # Check if running in interactive mode (no arguments)
    if len(args) == 0:
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
        
        # 如果是brainstorm_only模式，不创建文件
        if params.get("brainstorm_only", False):
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
        # 先检查是否是--help模式
        if '--help' in sys.argv or '-h' in sys.argv:
            parser = argparse.ArgumentParser(description='LEARN - 智能学习系统')
            parser.add_argument('topic', nargs='?', help='学习主题')
            parser.add_argument('-o', '--output-dir', help='输出目录')
            parser.add_argument('-m', '--mode', choices=['初学者', '中级', '高级', '专家'], 
                               default='中级', help='学习水平')
            parser.add_argument('-s', '--style', choices=['简洁明了', '详细深入', '实例丰富', '理论导向'],
                               default='详细深入', help='解释风格')
            parser.add_argument('-p', '--paper', help='论文文件路径')
            parser.add_argument('--file', help='直接处理文件路径 (支持PDF、MD、TXT)')
            parser.add_argument('--pdf', help='直接指定PDF文件路径 (已弃用，请使用--file)')
            parser.add_argument('-u', '--url', help='论文URL')
            parser.add_argument('-d', '--description', help='论文描述/搜索关键词')
            parser.add_argument('--negative', help='负面提示词：指定不想要的内容或论文类型')
            parser.add_argument('--read-images', action='store_true', help='处理PDF中的图像、公式和表格')
            parser.add_argument('--gen-command', help='根据描述生成LEARN命令')
            parser.add_argument('--model', help='指定OpenRouter模型')
            parser.add_argument('--max-tokens', type=int, help='最大token数')
            parser.add_argument('--not-default', action='store_true', help='非默认模式，需要用户确认')
            parser.add_argument('--no-override-material', action='store_true', help='不覆盖已存在的文件，自动重命名')
            parser.add_argument('--brainstorm-only', action='store_true', help='不自动创建文件，仅生成内容')
            parser.add_argument('--context', action='store_true', help='将description视作直接context进入brainstorming，跳过论文搜索')
            
            # 捕获help输出而不是让它exit
            import io
            from contextlib import redirect_stdout
            
            help_output = io.StringIO()
            try:
                with redirect_stdout(help_output):
                    parser.print_help()
                print(help_output.getvalue())
                return 0
            except:
                parser.print_help()
                return 0
        
        # 先检查是否是gen-command模式
        elif '--gen-command' in sys.argv:
            parser = argparse.ArgumentParser(description='LEARN - 智能学习系统')
            parser.add_argument('--gen-command', help='根据描述生成LEARN命令')
            
            # 只解析gen-command参数，忽略其他参数
            args, _ = parser.parse_known_args()
            
            if args.gen_command:
                success = generate_learn_command(args.gen_command)
                return 0 if success else 1
        
        params = parse_direct_command(sys.argv[1:])
        
        # 检查参数收集是否成功
        if not params:
            return 1
        
        # Generate learning content
        result = generate_learning_content(params)
        if result is None:
            return 1
        
        # 如果是brainstorm_only模式，不创建文件
        if params.get("brainstorm_only", False):
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