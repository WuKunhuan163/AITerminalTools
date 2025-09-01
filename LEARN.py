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
import time
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# Parameter mappings for bilingual support
MODE_MAPPING = {
    # Chinese
    '初学者': 'beginner',
    '中级': 'intermediate', 
    '高级': 'advanced',
    '专家': 'expert',
    # English
    'beginner': 'beginner',
    'intermediate': 'intermediate',
    'advanced': 'advanced', 
    'expert': 'expert',
    # Capitalized English
    'Beginner': 'beginner',
    'Intermediate': 'intermediate',
    'Advanced': 'advanced',
    'Expert': 'expert'
}

STYLE_MAPPING = {
    # Chinese
    '简洁明了': 'concise',
    '详细深入': 'detailed',
    '实例丰富': 'practical',
    '理论导向': 'theoretical',
    # English
    'concise': 'concise',
    'detailed': 'detailed',
    'example-rich': 'practical',
    'theory-oriented': 'theoretical',
    # Alternative English
    'brief': 'concise',
    'comprehensive': 'detailed',
    'practical': 'practical',
    'theoretical': 'theoretical',
    # Capitalized/other variants
    'Concise': 'concise',
    'Detailed': 'detailed',
    'Practical': 'practical',
    'Theoretical': 'theoretical',
    'Witty': 'practical',  # Legacy support
    # Additional test mappings
    'RichExamples': 'practical',
    'TheoryOriented': 'theoretical'
}

# 全局时间跟踪器
LEARN_START_TIME = None

def get_elapsed_time():
    """获取从LEARN开始运行以来的经过时间"""
    if LEARN_START_TIME is None:
        return "00:00"
    elapsed = time.time() - LEARN_START_TIME
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    return f"{minutes:02d}:{seconds:02d}"

def log_progress(message, level="INFO"):
    """输出带时间戳的进度信息"""
    elapsed = get_elapsed_time()
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}|{elapsed}] {level}: {message}")

def start_timer():
    """启动全局计时器"""
    global LEARN_START_TIME
    LEARN_START_TIME = time.time()
    log_progress("LEARN系统启动", "START")

def normalize_parameters(args):
    """Normalize bilingual parameters to Chinese equivalents"""
    if args.mode and args.mode in MODE_MAPPING:
        args.mode = MODE_MAPPING[args.mode]
    elif args.mode and args.mode not in MODE_MAPPING:
        # If not found, suggest available options
        available_modes = list(set(MODE_MAPPING.keys()))
        print(f"Error: Invalid mode '{args.mode}'. Available options: {', '.join(available_modes)}")
        return None
        
    if args.style and args.style in STYLE_MAPPING:
        args.style = STYLE_MAPPING[args.style]
    elif args.style and args.style not in STYLE_MAPPING:
        # If not found, suggest available options
        available_styles = list(set(STYLE_MAPPING.keys()))
        print(f"Error: Invalid style '{args.style}'. Available options: {', '.join(available_styles)}")
        return None
        
    return args

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
            print(f"\nCancelled.")
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
        print(f"Overwriting existing files in {output_dir}: {', '.join(existing_files)}")
        return True, output_dir
    
    # 交互模式：询问用户
    print(f"\nWarning: The following files already exist in {output_dir}:")
    for file in existing_files:
        print(f"  - {file}")
    
    while True:
        try:
            choice = input("\nChoose action: (o) overwrite / (r) rename / (c) cancel [o/r/c]: ").strip().lower()
            if choice in ['o', 'overwrite', '覆盖']:
                return True, output_dir
            elif choice in ['r', 'rename', '重命名', 'rename']:
                return handle_auto_rename(output_dir)
            elif choice in ['c', 'cancel', '取消', '']:
                return False, None
            else:
                print(f"Please enter o (overwrite) / r (rename) / c (cancel)")
        except KeyboardInterrupt:
            print(f"\nOperation cancelled")
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
            print(f"Auto-renamed output directory: {new_path}")
            return True, str(new_path)
        
        counter += 1
        if counter > 100:  # 防止无限循环
            print(f"Error: Unable to find a suitable directory name, please manually clean up the output directory")
            return False, None


def get_output_directory():
    """Get output directory using tkinter directory selection."""
    print(f"Select project directory...")
    return get_output_directory_tkinter()


def get_output_directory_tkinter():
    """Get output directory using tkinter as fallback."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        print(f"Please select the output folder in the pop-up window...")
        
        # 创建tkinter根窗口并隐藏
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        # 打开目录选择对话框
        selected_dir = filedialog.askdirectory(
            title="Select project directory"
        )
        
        # 销毁tkinter窗口
        root.destroy()
        
        if selected_dir:
            print(f"Selected directory: {selected_dir}")
            return selected_dir
        else:
            print(f"Error: No directory selected")
            return None
            
    except ImportError:
        print(f"Error: tkinter is not available, please manually enter the directory path")
        return None
    except Exception as e:
        print(f"Error: Directory selection failed: {e}")
        return None


def get_paper_file():
    """Get paper file using tkinter file selection."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        print(f"Please select the paper file in the pop-up window...")
        
        # 创建tkinter根窗口并隐藏
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        # 打开文件选择对话框
        selected_file = filedialog.askopenfilename(
            title="Select paper file",
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
            print(f"Selected file: {selected_file}")
            return selected_file
        else:
            print(f"Error: No file selected")
            return None
            
    except ImportError:
        print(f"Error: tkinter is not available, please manually enter the file path")
        return None
    except Exception as e:
        print(f"Error: File selection failed: {e}")
        return None


def run_interactive_mode():
    """Run in interactive mode to collect parameters."""
    clear_terminal()
    print(f"=== LEARN Intelligent Learning System ===")
    print(f"Welcome to the intelligent learning content generation tool!")
    print()
    
    # Step 1: Select learning type
    print(f"Step 1: Select learning type")
    type_choice = interactive_select(
        "Learning type:",
        ["General topic learning", "Academic paper learning"]
    )
    if type_choice is None:
        return None
    
    params = {}
    
    if type_choice == 0:  # General topic
        params["type"] = "general"
        
        # Get topic
        print(f"\nStep 2: Input learning topic")
        while True:
            topic = input("Please enter the learning topic (e.g., Python basics, machine learning, data structure): ").strip()
            if topic:
                try:
                    # 解析文件引用
                    expanded_topic, has_file_ref = parse_file_references(topic)
                    params["topic"] = expanded_topic
                    params["has_file_reference"] = has_file_ref
                    # 如果检测到文件引用，自动启用context模式
                    if has_file_ref:
                        params['context_mode'] = True
                        print(f"Detected @file reference, automatically enable --context mode")
                    break
                except (FileNotFoundError, ValueError) as e:
                    print(f"Error: {e}")
                    print(f"Please enter a valid topic or file path")
                    continue
            print(f"Please enter a valid topic")
        
    else:  # Paper-based
        params["type"] = "paper"
        
        print(f"Step 2: Select paper input method")
        input_choice = interactive_select(
            "Paper input method:",
            ["Local Markdown file", "Local PDF file", "Paper URL", "Paper description/search"]
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
                print(f"Read Markdown file: {len(content)} characters")
            except Exception as e:
                print(f"Error: Read file failed: {e}")
                return None
                
        elif input_choice == 1:  # PDF file
            paper_file = get_paper_file()
            if not paper_file:
                return None
            params["paper_path"] = paper_file
            
            # Ask about image processing
            print(f"\n  Image processing options")
            image_choice = interactive_select(
                "Process images, formulas, and tables in PDF?",
                ["No (only extract text, faster)", "Yes (full processing, requires API call)"]
            )
            params["read_images"] = image_choice == 1
            
        elif input_choice == 2:  # URL
            while True:
                url = input("Please enter the paper URL: ").strip()
                if url:
                    params["paper_url"] = url
                    break
                print(f"Please enter a valid URL")
                
            # Ask about image processing
            print(f"\n  Image processing options")
            image_choice = interactive_select(
                "Process images, formulas, and tables in PDF?",
                ["No (only extract text, faster)", "Yes (full processing, requires API call)"]
            )
            params["read_images"] = image_choice == 1
            
        elif input_choice == 3:  # Description/Search
            while True:
                description = input("Please enter the paper description or keywords: ").strip()
                if description:
                    params["paper_description"] = description
                    break
                print(f"Please enter a valid description")
                
            # Ask about image processing
            print(f"\n  Image processing options")
            image_choice = interactive_select(
                "Process images, formulas, and tables in PDF?",
                ["No (only extract text, faster)", "Yes (full processing, requires API call)"]
            )
            params["read_images"] = image_choice == 1
    
    # Step 3: Select learning level
    print(f"\nStep 3: Select learning level")
    mode_choice = interactive_select(
        "Learning level:",
        ["Beginner", "Intermediate", "Advanced", "Expert"]
    )
    if mode_choice is None:
        return None
    
    modes = ["初学者", "中级", "高级", "专家"]
    params["mode"] = modes[mode_choice]
    
    # Step 4: Select explanation style
    print(f"\nStep 4: Select explanation style")
    style_choice = interactive_select(
        "Explanation style:",
        ["Concise and clear", "Detailed and in-depth", "Rich examples", "Theoretical导向"]
    )
    if style_choice is None:
        return None
    
    styles = ["Concise and clear", "Detailed and in-depth", "Rich examples", "Theoretical导向"]
    params["style"] = styles[style_choice]
    
    # Step 5: Get output directory
    print(f"\nStep 5: Select output directory")
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
        print(f"Operation cancelled")
        return None
    
    # Update output directory if it was renamed
    if final_output_dir != output_dir:
        params["output_dir"] = final_output_dir
    
    return params


def parse_direct_command(args):
    """Parse direct command line arguments."""
    parser = argparse.ArgumentParser(description='LEARN - Intelligent Learning System')
    
    # Basic options
    parser.add_argument('topic', nargs='?', help='Learning topic')
    parser.add_argument('-o', '--output-dir', help='Output directory')
    parser.add_argument('-m', '--mode', choices=list(MODE_MAPPING.keys()), 
                       default='Intermediate', help='Learning level (Intermediate)')
    parser.add_argument('-s', '--style', choices=list(STYLE_MAPPING.keys()),
                       default='Detailed and in-depth', help='Explanation style (Detailed and in-depth)')
    
    # File options
    parser.add_argument('--file', help='Directly process file path (supports PDF, MD, TXT)')
    parser.add_argument('-u', '--url', help='Paper URL')
    parser.add_argument('-d', '--description', help='Paper description/search keywords')
    parser.add_argument('--negative', help='Negative prompt: specify content or paper type you don\'t want')
    parser.add_argument('--read-images', action='store_true', help='Process images, formulas, and tables in PDF')
    parser.add_argument('--gen-command', help='Generate LEARN command based on description')
    parser.add_argument('--paper-based', action='store_true', help='Force use of paper-based learning mode, even if only a description is provided, it will search and download papers')
    parser.add_argument('--sources', help='Specify paper search engines, separated by commas (arxiv,google_scholar), default is automatic recommendation')
    
    # Model options
    parser.add_argument('--model', help='Specify OpenRouter model')
    parser.add_argument('--max-tokens', type=int, help='Maximum token number')
    parser.add_argument('--temperature', type=float, help='Temperature parameter (0.0-2.0, control creativity of response)')
    parser.add_argument('--key', help='Specify OpenRouter API key')
    parser.add_argument('--not-default', action='store_true', help='Non-default mode, requires user confirmation')
    parser.add_argument('--no-override-material', action='store_true', help='Do not overwrite existing files, automatically rename')
    parser.add_argument('--brainstorm-only', action='store_true', help='Do not automatically create files, only generate content')
    parser.add_argument('--context', action='store_true', help='Treat description as direct context for brainstorming, skip paper search')
    
    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        return None
    
    # Normalize bilingual parameters
    parsed_args = normalize_parameters(parsed_args)
    if parsed_args is None:
        return None
    
    # 检查互斥参数
    if parsed_args.context and parsed_args.brainstorm_only:
        print(f"Error: --context and --brainstorm-only options are mutually exclusive, cannot be used together")
        print(f"   --context: Skip brainstorming, directly generate tutorial")
        print(f"   --brainstorm-only: Only perform brainstorming, do not generate tutorial")
        return None
    
    # Check if output is required for actual operation (not for --help)
    if not parsed_args.output_dir and not any(arg in ['-h', '--help'] for arg in args):
        # Default to current directory if not specified
        parsed_args.output_dir = str(Path.cwd())
        print(f"No output directory specified, using current directory: {parsed_args.output_dir}")
    
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
    if parsed_args.temperature is not None:
        params['temperature'] = parsed_args.temperature
    if parsed_args.key:
        params['api_key'] = parsed_args.key
    
    # Determine type based on arguments
    if parsed_args.file:
        # --file选项处理
        file_path = parsed_args.file
        params['type'] = 'paper'
        
        # 根据文件扩展名判断类型
        if file_path.endswith('.md'):
            params['input_type'] = 0  # Markdown file
            # 读取markdown文件内容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    params['paper_content'] = f.read()
                params['paper_path'] = file_path
            except Exception as e:
                print(f"Error: Read markdown file failed: {e}")
                return 1
        elif file_path.endswith('.txt'):
            params['input_type'] = 0  # Text file (treated as markdown)
            # 读取文本文件内容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    params['paper_content'] = f.read()
                params['paper_path'] = file_path
            except Exception as e:
                print(f"Error: Read text file failed: {e}")
                return 1
        elif file_path.endswith('.pdf'):
            params['input_type'] = 1  # PDF file
            params['paper_path'] = file_path
        else:
            # 默认按PDF处理
            params['input_type'] = 1  # PDF file
            params['paper_path'] = file_path
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
                print(f"Detected @file reference, automatically enable --context mode")
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}")
            return None
        params['negative_prompt'] = parsed_args.negative
        params['read_images'] = parsed_args.read_images
        params['sources'] = parsed_args.sources
    elif parsed_args.topic:
        try:
            expanded_topic, has_file_ref = parse_file_references(parsed_args.topic)
            
            # 检查topic是否是一个文件路径
            topic_path = Path(parsed_args.topic)
            if topic_path.exists() and topic_path.is_file():
                # 如果是文件路径，按文件类型处理
                file_ext = topic_path.suffix.lower()
                if file_ext == '.pdf':
                    params['type'] = 'paper'
                    params['input_type'] = 1  # PDF file
                    params['paper_path'] = str(topic_path)
                    params['read_images'] = parsed_args.read_images
                    print(f"Detected PDF file path, switch to paper learning mode: {topic_path}")
                elif file_ext in ['.md', '.txt']:
                    params['type'] = 'paper'
                    params['input_type'] = 0 if file_ext == '.md' else 4  # Markdown or direct file
                    if file_ext == '.md':
                        # 读取markdown文件内容
                        with open(topic_path, 'r', encoding='utf-8') as f:
                            params['paper_content'] = f.read()
                        params['paper_path'] = str(topic_path)
                    else:
                        params['file_path'] = str(topic_path)
                    params['read_images'] = parsed_args.read_images
                else:
                    # 其他文件类型仍然按一般主题处理
                    params['type'] = 'general'
                    params['topic'] = expanded_topic
                    params['has_file_reference'] = has_file_ref
            else:
                # 检查是否指定了--paper-based标志
                if parsed_args.paper_based:
                    # 强制使用论文模式，将topic作为论文描述搜索
                    params['type'] = 'paper'
                    params['input_type'] = 3  # Description/Search
                    params['paper_description'] = expanded_topic
                    params['has_file_reference'] = has_file_ref
                    params['negative_prompt'] = parsed_args.negative
                    params['read_images'] = parsed_args.read_images
                    params['sources'] = parsed_args.sources
                    print(f"--paper-based mode: use topic as paper search keywords: {expanded_topic}")
                else:
                    # 不是文件路径，按一般主题处理
                    params['type'] = 'general'
                    params['topic'] = expanded_topic
                    params['has_file_reference'] = has_file_ref
            
            # 如果检测到@文件引用，自动启用context模式
            if has_file_ref:
                params['context_mode'] = True
                print(f"Detected @file reference, automatically enable --context mode")
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}")
            return None
    else:
        print(f"Error: must specify learning topic or paper information")
        return None
    
    # Check for existing files and handle overwrite in direct mode
    if params['output_dir']:
        can_continue, final_output_dir = check_and_confirm_overwrite(
            params['output_dir'], 
            params.get('not_default', False),
            params.get('no_override_material', False)
        )
        
        if not can_continue:
            print(f"Operation cancelled")
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
        print(f"Warning:  Get model list failed: {e}")
        # Return minimal fallback
        return ["deepseek/deepseek-r1:free"], {}


def select_openrouter_model(params):
    """Select OpenRouter model with token limits."""
    models, model_details = get_openrouter_models()
    
    if not models:
        print(f"Error:  No available models")
        return None, None
    
    # Check if model is already specified
    if params.get("selected_model"):
        selected_model = params["selected_model"]
        max_tokens = params.get("max_tokens", 4000)
        print(f"Using specified model: {selected_model}")
        return selected_model, max_tokens
    
    # Auto-select for default mode (use "auto" for automatic model selection)
    if not params.get('not_default', False):
        selected_model = "auto"  # 使用auto模式自动选择
        max_tokens = 4000
        print(f"Default mode: automatic model selection")
        return selected_model, max_tokens
    
    # Interactive mode - let user choose
    print(f"\nAvailable model list:")
    print(f"=" * 80)
    for i, model in enumerate(models):
        model_info = model_details.get(model, {})
        input_cost = model_info.get('input_cost_per_1m', 0)
        output_cost = model_info.get('output_cost_per_1m', 0)
        context_length = model_info.get('context_length', 0)
        
        print(f" {i+1}. {model}")
        print(f"    Rate: input ${input_cost:.2f}/1M, output ${output_cost:.2f}/1M")
        print(f"    Context length: {context_length:,} tokens")
        print()
    
    print(f" {len(models)+1}. auto (auto select best model)")
    print(f"The system will automatically select available models based on priority")
    print()
    
    while True:
        try:
            choice = input(f"Select model (1-{len(models)+1}, default: auto): ").strip()
            
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
                print(f"Error: Please enter a number between 1 and {len(models)+1}")
                
        except ValueError:
            print(f"Error:  Please enter a valid number")
        except KeyboardInterrupt:
            print(f"\nError: User cancelled")
            return None, None
    
    # Set max tokens based on model
    if selected_model == "auto":
        max_tokens = 40960  # Higher default value, will be dynamically adjusted when called
        print(f"Select auto mode")
    else:
        model_info = model_details.get(selected_model, {})
        context_length = model_info.get('context_length', 4000)
        max_tokens = context_length // 4  # Use 1/4 of context length
        print(f"Select model: {selected_model} (max_tokens: {max_tokens})")
    
    return selected_model, max_tokens


def generate_content_structure_prompt(params):
    """Generate prompt for content structure brainstorming."""
    if params["type"] == "general":
        topic = params['topic']
        mode = params['mode']
        style = params['style']
        
        # 检查是否包含文件引用
        if params.get("has_file_reference", False):
            print(f"Detected file reference, will create tutorial based on file content")
            return f'Create detailed learning tutorial structure based on the following content, suitable for {mode} level learners, using {style} explanation style:\n\n{topic}'
        else:
            return f'Create detailed learning tutorial structure for "{topic}", suitable for {mode} level learners, using {style} explanation style.'
        
    elif params["type"] == "paper":
        mode = params['mode']
        style = params['style']
        
        # 首先进行模型选择（如果还没有选择的话）
        if not params.get("selected_model"):
            selected_model, max_tokens = select_openrouter_model(params)
            if not selected_model:
                print(f"Error:  No model selected")
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
            print(f"Warning:  Paper content is too long ({token_count:,} tokens), exceeds recommended processing length ({content_threshold:,} tokens)")
            
            # 检查是否为默认模式
            if params.get("not_default", False):
                # 非默认模式：询问用户选择
                approach_choice = interactive_select(
                    "Content processing method:",
                    ["Direct use (may exceed model limit)", "Smart summary (recommended)", "Manual truncate"]
                )
            else:
                # 默认模式：自动选择第一个选项
                print(f"Content processing method:")
                print(f"  1. Direct use (may exceed model limit)")
                print(f"  2. Smart summary (recommended)")
                print(f"  3. Manual truncate")
                print(f"Choose (1-3, default: 1): 1")
                print(f"Selected: Direct use (may exceed model limit)")
                approach_choice = 0  # 对应第一个选项
            
            if approach_choice == 1:  # Smart summary
                print(f"Generating paper summary...")
                # Generate summary prompt
                summary_prompt = f"""Please generate a detailed summary of the following academic paper, preserving key technical details:

{paper_content[:20000]}

Please include:
1. Research background and problem
2. Main methods and techniques
3. Key innovations
4. Experimental results
5. Conclusion and significance

The summary should be detailed but concise, suitable for subsequent tutorial creation."""
                
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
                    print(f"Summary generated ({count_tokens(paper_content)} tokens)")
                else:
                    print(f"Error:  Summary generation failed, using original content")
                    
            elif approach_choice == 2:  # Manual truncate
                paper_content = paper_content[:60000]  # Keep first 60k characters
                print(f"Truncated first part of content ({count_tokens(paper_content)} tokens)")
        
        # Update params with processed content
        params['paper_content'] = paper_content
        
        # Generate brainstorming prompt for paper
        return f"""Please analyze the content of this academic paper, prepare for tutorial creation:

Paper path: {paper_path}
Learning level: {mode}
Explanation style: {style}

Paper content:
{paper_content}

Please analyze:
1. The core contributions and innovations of the paper
2. Key concepts and technical methods
3. Focused content suitable for {mode} level learners
4. Possible difficulties and misconceptions
5. Practical applications and extended thinking

Please provide structured analysis, prepare for subsequent detailed tutorial creation."""
    
    return None


def call_openrouter_for_structure(prompt, model=None, max_tokens=None, retry_count=0, temperature=None, api_key=None):
    """Call OpenRouter API for structure generation with improved error handling."""
    import time
    import json
    import re
    
    try:
        script_dir = Path(__file__).parent
        run_path = script_dir / "RUN.py"
        
        if retry_count == 0:
            print(f"Connecting to OpenRouter API...", file=sys.stderr)
        else:
            print(f"Retrying API call (attempt {retry_count})...", file=sys.stderr)
            
        # 处理模型选择
        if not model or model == "auto":
            print(f"Using auto model selection", file=sys.stderr)
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
            print(f"Using model: {model}", file=sys.stderr)
            if max_tokens:
                print(f"Maximum tokens: {max_tokens}", file=sys.stderr)
            print(f"Please wait ...", file=sys.stderr)
            
            # 记录开始时间
            start_time = time.time()
            
            # 构建命令 - 使用RUN --show调用OPENROUTER工具，通过stdin传递prompt
            cmd = [sys.executable, str(run_path), "--show", "OPENROUTER"]
            
            if model:
                cmd.extend(["--model", model])
            
            # 传入max-tokens参数（OPENROUTER工具会自动处理动态调整）
            if max_tokens:
                cmd.extend(["--max-tokens", str(max_tokens)])
            
            # 传入temperature参数
            if temperature is not None:
                cmd.extend(["--temperature", str(temperature)])
            
            # 传入API密钥参数
            if api_key:
                cmd.extend(["--key", api_key])
            
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
                            
                            print(f"OpenRouter API call successful (duration: {api_duration:.2f} seconds)", file=sys.stderr)
                            return content, usage_info
                        else:
                            error_msg = response_data.get('error', 'Unknown error')
                            print(f"Error: OpenRouter API returned error: {error_msg}", file=sys.stderr)
                            return f"ERROR: {error_msg}", {"error": error_msg}
                            
                    except json.JSONDecodeError as e:
                        print(f"Error: Parsing OpenRouter response failed: {e}", file=sys.stderr)
                        print(f"Original response: {result.stdout[:500]}...", file=sys.stderr)
                        return f"ERROR: JSON parsing failed: {e}", {"error": f"JSON parsing failed: {e}"}
                else:
                    error_msg = result.stderr or "Command execution failed"
                    print(f"Error: OpenRouter command execution failed: {error_msg}", file=sys.stderr)
                    return f"ERROR: {error_msg}", {"error": error_msg}
                    
            except subprocess.TimeoutExpired:
                print(f"Error:  OpenRouter API call timed out", file=sys.stderr)
                return "ERROR: API call timed out", {"error": "API call timed out"}
            except Exception as e:
                print(f"Error: OpenRouter API call exception: {e}", file=sys.stderr)
                return f"ERROR: {e}", {"error": str(e)}
        
    except Exception as e:
        print(f"Error: call_openrouter_for_structure exception: {e}", file=sys.stderr)
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
        
        prompt = f"""Please create a concise tutorial.md file for "{topic}".

Learning mode: {mode}
Explanation style: {style}

Based on the following points, create a tutorial.md file:
{brainstorming_summary}

Please create a concise tutorial.md file, including:
1. Title and table of contents
2. Detailed explanation of 3-4 core concepts (including code examples, practice questions, etc., if applicable)
3. Simple learning path guidance
4. 2-3 practice exercise suggestions
5. Selected resource recommendations

Please ensure the content is suitable for {mode} level learners, and use {style} explanation style.
Please provide markdown format content, do not use any separators."""
        
    else:
        # Paper-based
        paper_path = params.get('paper_path', 'Paper')
        paper_content = params.get('paper_content', '')
        mode = params['mode']
        style = params['style']
        
        # Use brainstorming response if available, otherwise use paper content directly
        if brainstorming_response:
            content_base = f"""Brainstorming analysis result:
{brainstorming_response}

Original paper content (reference):
{paper_content[:5000]}{'...' if len(paper_content) > 5000 else ''}"""
        else:
            content_base = f"""Paper content:
{paper_content}"""
        
        prompt = f"""Please create a detailed tutorial.md file based on the academic paper content.

Paper: {paper_path}
Learning mode: {mode}
Explanation style: {style}

Based on the following content, create a tutorial.md file:
{content_base}

Please create a complete tutorial.md file, including:

1. **Paper overview**
   - Paper title, author, publication information
   - Research background and motivation
   - Main contributions and innovations

2. **Core concept explanation**
   - Definition and explanation of key concepts
   - Detailed explanation of technical methods
   - How the algorithm or model works

3. **Technical details**
   - Implementation methods and technical路线
   - Experimental design and evaluation methods
   - Result analysis and discussion

4. **Learning points**
   - Summary of key points
   - Comparison with existing methods
   - Analysis of advantages and limitations

5. **Extended reading**
   - Recommended related papers
   - Further learning resources

Please ensure the content is suitable for {mode} level learners, and use {style} explanation style.
Please provide markdown format content, do not use any separators."""
    
    return prompt


def generate_question_prompt(params, tutorial_content):
    """Generate prompt for question.md creation."""
    if params["type"] == "general":
        # General topic
        topic = params['topic']
        mode = params['mode']
        style = params['style']
        
        tutorial_summary = tutorial_content
        
        prompt = f"""Please create a concise question.md file for "{topic}".

Learning mode: {mode}
Explanation style: {style}

Based on the following tutorial content, create a question.md file:
{tutorial_summary}

Please create a concise question.md file, including:
1. Basic knowledge test questions (3 questions)
2. Understanding application questions (3 questions)
3. Practice exercise questions (2 questions)
4. Thinking questions (2 questions)
5. Each question must have a clear and concise answer

Please use HTML's details/summary tags to create expandable answer regions.
Please ensure the questions are suitable for {mode} level learners.
Please control the content length, keep it concise."""
        
    else:
        # Paper-based
        paper_path = params.get('paper_path', 'Paper')
        mode = params['mode']
        style = params['style']
        
        tutorial_summary = tutorial_content
        
        prompt = f"""Please create a comprehensive question.md file based on the academic paper tutorial.

Paper: {paper_path}
Learning mode: {mode}
Explanation style: {style}

Based on the following tutorial content, create a question.md file:
{tutorial_summary}

Please create a comprehensive question.md file, including:

1. **Paper understanding questions (4 questions)**
   - Understanding the research background and motivation
   - Main contributions and innovations
   - Technical methods and principles
   - Experimental results and conclusions

2. **Concept explanation questions (3 questions)**
   - Key concept definition
   - Technical terminology explanation
   - Method comparison analysis

3. **Critical thinking questions (3 questions)**
   - Analysis of method advantages and disadvantages
   - Improvement suggestions and extensions
   - Application scenario discussion

4. **Practice application questions (2 questions)**
   - Practical application design
   - Implementation analysis

Each question must:
- Based on the specific content in the tutorial
- Have a detailed and accurate answer
- Use HTML's <details> and <summary> tags to implement answer folding

Format example:
### Question 1: What are the main contributions of this paper?
<details>
<summary>Click to view answer</summary>

[Detailed answer content...]

</details>

Please ensure the questions are suitable for {mode} level learners, and use {style} explanation style."""
    
    return prompt


def create_learning_files_from_responses(params, tutorial_response, question_response, prompts_and_responses=None):
    """Create learning files from separate tutorial and question responses."""
    log_progress("Start creating files", "FILE")
    output_dir = params['output_dir']
    
    # 确保输出目录存在
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    log_progress(f"Output directory prepared: {output_dir}", "FILE")
    
    try:
        # 创建tutorial.md
        log_progress("Create tutorial.md file", "FILE")
        tutorial_path = Path(output_dir) / "tutorial.md"
        with open(tutorial_path, 'w', encoding='utf-8') as f:
            f.write(tutorial_response)
        log_progress(f"tutorial.md created successfully: {tutorial_path}", "FILE")
        print(f"Create file: {tutorial_path}")
        
        # 创建question.md
        log_progress("Create question.md file", "FILE")
        question_path = Path(output_dir) / "question.md"
        with open(question_path, 'w', encoding='utf-8') as f:
            f.write(question_response)
        log_progress(f"question.md created successfully: {question_path}", "FILE")
        print(f"Create file: {question_path}")
        
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
                
                print(f"Save prompt and response: {prompt_path.name}, {response_path.name}")
                model_used = token_info.get('model', 'unknown')
                cost = token_info.get('cost', 0)
                print(f"Token usage: {token_info.get('total_tokens', 0)} tokens - Model: {model_used} - Cost: ${cost:.6f} - Duration: {token_info.get('api_duration', 0):.2f} seconds")
        
        file_count = 2 + (len(prompts_and_responses) * 2 if prompts_and_responses else 0)
        print(f"\nCreated {file_count} files:")
        print(f"  - {tutorial_path}")
        print(f"  - {question_path}")
        if prompts_and_responses:
            print(f"  - OPENROUTER_prompts/ folder contains {len(prompts_and_responses)} groups of prompts and responses")
        
        return True
        
    except Exception as e:
        print(f"Error: Error creating files: {e}")
        return False


def call_openrouter_with_retry(prompt, model, max_tokens, step_name, max_retries=3, params=None):
    """Call OpenRouter API with retry mechanism and model switching."""
    log_progress(f"Start {step_name}", "API")
    current_model = model
    
    # 提取额外参数
    temperature = params.get('temperature') if params else None
    api_key = params.get('api_key') if params else None
    
    for attempt in range(max_retries):
        log_progress(f"{step_name} - Attempt {attempt + 1}", "API")
        response, token_info = call_openrouter_for_structure(prompt, current_model, max_tokens, attempt, temperature, api_key)
        
        # 检查是否成功（不是None且不是错误）
        if response is not None and not (isinstance(response, str) and response.startswith("ERROR:")):
            log_progress(f"{step_name} completed successfully - Using model: {current_model}", "API")
            return response, token_info, current_model
        
        log_progress(f"{step_name} failed (Attempt {attempt + 1}) - Error: {str(response)[:100]}...", "ERROR")
        print(f"Error: {step_name} failed (Attempt {attempt + 1})", file=sys.stderr)
        
        # 检查是否是429错误（速率限制）或其他错误需要切换模型
        if should_switch_model(response, attempt, max_retries):
            current_model = handle_model_switching(current_model, params, step_name)
            if not current_model:
                break
            
            # 用新模型重试
            response, token_info = call_openrouter_for_structure(prompt, current_model, max_tokens, 0, temperature, api_key)
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
        print(f"Error:  Unable to get model list", file=sys.stderr)
        return None
    
    # 移除当前失败的模型
    available_models = [m for m in all_models if m != current_model]
    if not available_models:
        print(f"Error:  No other available models", file=sys.stderr)
        return None
    
    # 分类模型
    free_models = [m for m in available_models if ":free" in m]
    paid_models = [m for m in available_models if ":free" not in m]
    
    # 默认模式：自动切换
    if params and not params.get('not_default', False):
        if current_model and ":free" in current_model and free_models:
            new_model = free_models[0]
            print(f"Automatically switch to next free model: {new_model}", file=sys.stderr)
            return new_model
        elif paid_models:
            new_model = paid_models[0]
            print(f"Automatically switch to paid model: {new_model}", file=sys.stderr)
            return new_model
    else:
        # 交互模式：让用户选择
        return interactive_model_selection(current_model, free_models, paid_models, step_name)
    
    return None


def interactive_model_selection(failed_model, free_models, paid_models, step_name):
    """Interactive model selection when switching models."""
    print(f"\nWarning: Model '{failed_model}' call failed", file=sys.stderr)
    print(f"Available alternative models:", file=sys.stderr)
    
    all_available = []
    if free_models:
        print(f"Free models:", file=sys.stderr)
        for i, model_name in enumerate(free_models):
            print(f"  {len(all_available) + 1}. {model_name}", file=sys.stderr)
            all_available.append(model_name)
    
    if paid_models:
        print(f"Paid models:", file=sys.stderr)
        for i, model_name in enumerate(paid_models):
            print(f"  {len(all_available) + 1}. {model_name}", file=sys.stderr)
            all_available.append(model_name)
    
    try:
        choice = input(f"\nSelect model (1-{len(all_available)}) or press Enter to skip: ").strip()
        if choice and choice.isdigit():
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(all_available):
                new_model = all_available[choice_idx]
                print(f"Switch to model: {new_model}", file=sys.stderr)
                return new_model
    except (KeyboardInterrupt, EOFError):
        print(f"\nUser cancelled operation", file=sys.stderr)
    
    return None


def generate_learning_content(params):
    """Generate learning content based on collected parameters."""
    log_progress("Start generating learning content", "MAIN")
    print(f"\nGenerating learning content structure...")
    
    # 用于保存所有的prompts和responses，现在包含token信息
    prompts_and_responses = []
    
    # For paper type, model selection might already be done in generate_content_structure_prompt
    if params["type"] == "paper" and params.get("selected_model"):
        selected_model = params["selected_model"]
        max_tokens = params["max_tokens"]
        log_progress(f"Using pre-selected model: {selected_model}", "MODEL")
        print(f"Using pre-selected model: {selected_model}")
    else:
        # 让用户选择模型
        log_progress("Start model selection process", "MODEL")
        selected_model, max_tokens = select_openrouter_model(params)
        if not selected_model:
            log_progress("Model selection failed", "ERROR")
            print(f"Error:  No model selected")
            return None
        
        log_progress(f"Model selection completed: {selected_model}", "MODEL")
        # Store selected model info in params for later use
        params["selected_model"] = selected_model
        params["max_tokens"] = max_tokens
    
    # Step 1: Brainstorming (optional for papers)
    brainstorming_response = None
    brainstorming_token_info = None
    
    # 检查是否跳过brainstorming（只有context模式才跳过）
    if params.get("context_mode", False):
        log_progress("Skip brainstorming step (context mode)", "SKIP")
        print(f"\nSkip brainstorming step (--context mode)")
        # 直接准备论文内容用于后续步骤
        if params["type"] == "paper":
            structure_prompt = generate_content_structure_prompt(params)
            if structure_prompt is None:
                print(f"Error:  Content preparation failed, cannot continue generating learning materials")
                return None
    else:
        print(f"\nStep 1: Ask AI for brainstorming...")
        structure_prompt = generate_content_structure_prompt(params)
        
        # Check if content preparation failed (e.g., PDF extraction failed)
        if structure_prompt is None and params["type"] == "paper":
            print(f"Error:  Content preparation failed, cannot continue generating learning materials")
            return None
    
    if structure_prompt and not params.get("context_mode", False):  # Brainstorming was requested
        log_progress("Start brainstorming step", "STEP")
        print(f"Query content:")
        print(f"-" * 40)
        print(structure_prompt[:500] + "..." if len(structure_prompt) > 500 else structure_prompt)
        print(f"-" * 40)
        
        # Call OpenRouter API for brainstorming with retry
        brainstorming_response, brainstorming_token_info, current_model = call_openrouter_with_retry(
            structure_prompt, selected_model, max_tokens, "头脑风暴", params=params
        )
        
        if brainstorming_response is None:
            log_progress("Brainstorming step failed", "ERROR")
            print(f"Error:  Brainstorming failed")
            return None
        
        log_progress("Brainstorming step completed", "STEP")
        # 保存第一组prompt和response
        prompts_and_responses.append((structure_prompt, brainstorming_response, brainstorming_token_info))
        
        # 如果是brainstorm_only模式，只返回brainstorming结果
        if params.get("brainstorm_only", False):
            log_progress("Only brainstorming mode, return results", "COMPLETE")
            print(f"\nBrainstorming completed! Here are the generated structure suggestions:")
            print(f"=" * 60)
            print(brainstorming_response)
            print(f"=" * 60)
            print(f"\nYou can manually create tutorial.md and question.md files based on the above suggestions")
            return {
                'brainstorming_response': brainstorming_response,
                'prompts_and_responses': prompts_and_responses
            }
    else:
        print(f"Skip brainstorming, directly generate tutorial")
        
        # For paper type without brainstorming, check if we should continue
        if params["type"] == "paper":
            creation_mode = determine_creation_mode(params, selected_model)
            if creation_mode == "manual":
                params["brainstorm_only"] = True
    
    # Step 2: Generate tutorial.md
    log_progress("Start generating tutorial.md", "STEP")
    print(f"\nStep 2: Generate tutorial.md based on content...")
    tutorial_prompt = generate_tutorial_prompt(params, brainstorming_response)
    
    print(f"Query content:")
    print(f"-" * 40)
    print(tutorial_prompt[:500] + "..." if len(tutorial_prompt) > 500 else tutorial_prompt)
    print(f"-" * 40)
    
    tutorial_response, tutorial_token_info, current_model = call_openrouter_with_retry(
        tutorial_prompt, selected_model, max_tokens, "tutorial.md生成", params=params
    )
    
    if tutorial_response is None:
        log_progress("tutorial.md generation failed", "ERROR")
        print(f"Error:  tutorial.md generation failed")
        return None
    
    log_progress("tutorial.md generation completed", "STEP")
    # 保存第二组prompt和response
    prompts_and_responses.append((tutorial_prompt, tutorial_response, tutorial_token_info))
    
    # Step 3: Generate question.md
    log_progress("Start generating question.md", "STEP")
    print(f"\nStep 3: Generate question.md based on tutorial.md...")
    question_prompt = generate_question_prompt(params, tutorial_response)
    
    print(f"Query content:")
    print(f"-" * 40)
    print(question_prompt[:500] + "..." if len(question_prompt) > 500 else question_prompt)
    print(f"-" * 40)
    
    question_response, question_token_info, current_model = call_openrouter_with_retry(
        question_prompt, selected_model, max_tokens, "question.md生成", params=params
    )
    
    if question_response is None:
        log_progress("question.md generation failed", "ERROR")
        print(f"Error:  question.md generation failed")
        return None
    
    log_progress("question.md generation completed", "STEP")
    # 保存第三组prompt和response
    prompts_and_responses.append((question_prompt, question_response, question_token_info))
    
    log_progress("All content generation completed", "COMPLETE")
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
        print(f"Default mode: automatically select creation mode...")
        return "auto"
    
    # Check if using free model
    if selected_model:
        models, model_details = get_openrouter_models()
        if models:
            details = model_details.get(selected_model, {})
            is_free_model = details.get('input_cost_per_1m', 0) == 0
            if is_free_model:
                print(f"Free model: automatically select creation mode...")
                return "auto"
    
    # Ask user about creation mode
    print(f"\nSelect creation mode:")
    creation_choice = interactive_select(
        "Creation mode:", 
        ["Auto create (AI generates 3 times)", "Manual create (AI generates 1 time, you create the file)"]
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
        print(f"Using provided Markdown content")
        
    elif input_type == 1:  # PDF file
        paper_path = params.get("paper_path")
        read_images = params.get("read_images", False)
        paper_content, processed_path = process_paper_with_extract_pdf(paper_path, read_images)
        if processed_path:
            paper_path = processed_path
            
    elif input_type == 2:  # URL
        paper_url = params.get("paper_url")
        print(f"Download paper: {paper_url}")
        
        # Extract filename from URL or use generic name
        import urllib.parse
        parsed_url = urllib.parse.urlparse(paper_url)
        filename = Path(parsed_url.path).name or "downloaded_paper.pdf"
        
        downloaded_path, title = download_paper(paper_url, filename.replace('.pdf', ''), 
                                               output_dir=params.get('output_dir'))
        if downloaded_path:
            read_images = params.get("read_images", False)
            paper_content, processed_path = process_paper_with_extract_pdf(downloaded_path, read_images)
            if processed_path:
                paper_path = processed_path
        else:
            print(f"Error:  Unable to download paper")
            return None, None, 0
            
    elif input_type == 3:  # Description/Search
        paper_description = params.get("paper_description")
        
        # 检查是否为context模式（包括文件引用或手动启用）
        if params.get("context_mode", False):
            print(f"Context mode: directly use description content instead of searching for papers")
            # 直接使用description中的内容
            paper_content = paper_description
            paper_path = "context_content"
            # 估算token数量
            token_count = len(paper_content) // 4  # 粗略估算
            print(f"Context content processed, content length: {token_count} tokens")
        else:
            paper_content, downloaded_path, token_count = search_and_download_paper(paper_description, params)
            if paper_content:
                print(f"Paper processed, content length: {token_count} tokens")
                paper_path = downloaded_path  # PDF路径
            else:
                print(f"Error:  Unable to find or download paper")
                return None, None, 0
    

    
    if not paper_content:
        print(f"Error:  Unable to get paper content")
        return None, None, 0
    
    # Count tokens
    token_count = count_tokens(paper_content)
    print(f"\nPaper content statistics:")
    print(f"   Character count: {len(paper_content):,}")
    print(f"   Estimated token count: {token_count:,}")
    
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
                print(f"Error:  No useable models")
                return {"success": False, "error": "No useable models available"}
            
            # 尝试按顺序调用模型
            for i, model_id in enumerate(useable_models):
                print(f"Try model {i+1}/{len(useable_models)}: {model_id}")
                
                try:
                    result = call_openrouter_api(prompt, model=model_id)
                    if result['success']:
                        print(f"Model {model_id} call successful")
                        return result
                    else:
                        print(f"Warning: Model {model_id} call failed: {result.get('error', 'Unknown error')}")
                        if i < len(useable_models) - 1:  # 不是最后一个模型
                            print(f"Try next model...")
                            continue
                        
                except Exception as e:
                    print(f"Warning: Model {model_id} call exception: {e}")
                    if i < len(useable_models) - 1:
                        print(f"Try next model...")
                        continue
            
            # 所有模型都失败了
            return {"success": False, "error": "All models failed"}
        
        else:
            # 使用指定模型
            print(f"Use specified model: {model}")
            return call_openrouter_api(prompt, model=model)
            
    except Exception as e:
        return {"success": False, "error": f"API调用异常: {e}"}


def optimize_search_query_with_ai(user_description):
    """使用AI优化搜索查询，将用户描述转换为更好的英文搜索词"""
    try:
        prompt = f"""You are an academic search expert. The user wants to search for papers on the following topic:

User description: {user_description}

Please help optimize this search query and generate 2-4 best English search keywords or phrases for searching related papers in academic databases.

Requirements:
1. Use English keywords or phrases
2. Each keyword/phrase is no more than 3 words
3. Total vocabulary is no more than 10 words
4. Include core technical terms to ensure precise matching
5. Avoid too broad vocabulary (e.g. "machine learning" alone)
6. Suitable for searching in arXiv, Google Scholar, etc.
7. Prioritize specific algorithm names or technical terms

Please only return search keywords, separated by commas, no other explanation.

For example:
- If the user says "3DGS mesh reconstruction", return: "3D Gaussian Splatting, mesh reconstruction, neural rendering"
- If the user says "machine learning optimization algorithm", return: "gradient descent optimization, SGD algorithms, optimization methods"
- If the user says "Hong Kong environmental movement", return: "Hong Kong environmental policy, sustainability initiatives, urban environmental management"

Search keywords: """

        print(f"Calling OpenRouter to optimize search query...")
        result = call_openrouter_with_auto_model(prompt, model="auto")
        
        if result['success']:
            optimized_query = result['content'].strip()
            print(f"Optimized search keywords: {optimized_query}")
            return optimized_query
        else:
            print(f"Warning: AI optimization failed, using original description: {result['error']}")
            return user_description
            
    except Exception as e:
        print(f"Warning: AI optimization failed, using original description: {e}")
        return user_description


def recommend_search_engines_with_ai(user_description, optimized_query):
    """使用AI推荐最适合的论文搜索引擎"""
    try:
        prompt = f"""You are an academic search expert. Please recommend the most suitable paper search platform based on the user's search requirements.

User description: {user_description}
Optimized search keywords: {optimized_query}

Available search platforms:
1. arxiv - Mainly includes preprint papers in computer science, physics, mathematics, statistics, etc.
2. google_scholar - Covers all academic fields, including published journal papers, conference papers, and thesis papers.

Please recommend the most suitable search platform based on the user's search requirements:

- If the user is searching for computer science, AI, machine learning, deep learning, physics, mathematics, etc., recommend: arxiv,google_scholar
- If the user is searching for optimization algorithms, machine learning algorithms, specific algorithm research, etc., recommend: google_scholar (Google Scholar has more algorithm papers)
- If the user is searching for social science, environmental policy, economics, management, medicine, etc., recommend: google_scholar
- If the user is searching for cross-disciplinary or uncertain fields, recommend: arxiv,google_scholar

Please only return the recommended search engines, separated by commas, no other explanation.
For example: arxiv,google_scholar or google_scholar

Recommended search engines: """

        print(f"Calling OpenRouter to recommend the most suitable search engines...")
        result = call_openrouter_with_auto_model(prompt, model="auto")
        
        if result['success']:
            recommended_sources = result['content'].strip()
            print(f"Recommended search engines: {recommended_sources}")
            return recommended_sources
        else:
            print(f"Warning: Search engine recommendation failed, using default: arxiv,google_scholar")
            return "arxiv,google_scholar"
            
    except Exception as e:
        print(f"Warning: Search engine recommendation failed, using default: {e}")
        return "arxiv,google_scholar"


def select_best_papers_with_ai(search_results, user_description, max_papers=3, negative_prompt=None):
    """使用AI从搜索结果中选择最相关的论文"""
    try:
        # 准备论文信息
        papers_info = []
        for i, paper in enumerate(search_results[:10]):  # 最多分析前10篇
            info = f"""Paper {i+1}:
Title: {paper.get('title', 'Unknown')}
Authors: {', '.join(paper.get('authors', [])[:3])}
Abstract: {paper.get('abstract', 'No abstract')[:300]}...
Published time: {paper.get('published', 'Unknown')}
Citation count: {paper.get('citation_count', 'Unknown')}
Source: {paper.get('source', 'Unknown')}
"""
            papers_info.append(info)
        
        papers_text = '\n\n'.join(papers_info)
        
        # 构建基础prompt
        prompt = f"""You are an academic research expert. The user is looking for papers on the following topic:

User requirements: {user_description}

Here is the list of papers found:

{papers_text}

Please select the most relevant and valuable {max_papers} papers from these papers, considering the following factors:
1. Direct relevance to user requirements (must have clear topic association)
2. Quality and impact of the paper (citation count, publication time, etc.)
3. Novelty and importance of the research

**Screening criteria**：
- The title and abstract of the paper must contain core concepts or technical terms related to the user's requirements
- For technical topics, the paper should involve the same or related algorithms, methods, or technical fields
- Completely irrelevant papers (e.g. movie generation vs optimization algorithm, antenna design vs machine learning) should be excluded
- If no truly relevant papers are found, please be honest and say "No relevant papers"

**Example**：
- User requirements "machine learning optimization algorithm" → Accept: gradient descent, SGD, Adam optimizer related papers
- User requirements "machine learning optimization algorithm" → Reject: movie generation, antenna design, medical imaging, etc. irrelevant papers"""

        # 如果有negative prompt，添加到指令中
        if negative_prompt:
            prompt += f"""

**Special attention**: Please avoid selecting papers related to the following descriptions: {negative_prompt}
Prioritize papers that are directly relevant to the user's requirements and do not contain the above unwanted content."""

        prompt += f"""

Please return the selected paper numbers (1-{len(papers_info)}), separated by commas.
For example: if you select the 1st, 3rd, and 5th papers, return: 1,3,5

Only return the numbers, no other explanation: """

        print(f"Calling OpenRouter to smartly select the best papers...")
        result = call_openrouter_with_auto_model(prompt, model="auto")
        
        if result['success']:
            selected_indices = result['content'].strip()
            print(f"AI recommended papers: {selected_indices}")
            
            # 检查是否AI认为没有相关论文 - 但如果用户明确要求基于论文学习，则放宽标准
            strict_no_relevant_keywords = ['no relevant paper', 'none of the provided']
            if any(keyword in selected_indices.lower() for keyword in strict_no_relevant_keywords):
                # 检查是否有备选推荐（即使AI认为不是很相关）
                if any(char.isdigit() for char in selected_indices):
                    print(f"AI thinks the papers are not highly relevant, but still provides alternative recommendations, continue processing...")
                else:
                    print(f"Error:  AI judgment: no relevant papers found")
                    return []  # 返回空列表表示没有相关论文
            
            # 解析选择的论文编号 - 改进的解析逻辑
            try:
                # 方法1: 尝试直接解析（适用于简洁回答如 "1,3,5"）
                if ',' in selected_indices and len(selected_indices.strip()) < 20:
                    indices = [int(x.strip()) - 1 for x in selected_indices.split(',')]
                    selected_papers = [search_results[i] for i in indices if 0 <= i < len(search_results)]
                    return selected_papers[:max_papers]
                
                # 方法2: 从长文本中提取数字（适用于详细解释）
                import re
                
                # 查找 "Final selection:" 或类似模式后的数字
                final_selection_patterns = [
                    r'Final selection:\s*([0-9,\s]+)',
                    r'final selection:\s*([0-9,\s]+)', 
                    r'选择:\s*([0-9,\s]+)',
                    r'推荐:\s*([0-9,\s]+)'
                ]
                
                for pattern in final_selection_patterns:
                    match = re.search(pattern, selected_indices, re.IGNORECASE)
                    if match:
                        numbers_str = match.group(1).strip()
                        indices = [int(x.strip()) - 1 for x in numbers_str.split(',') if x.strip().isdigit()]
                        if indices:
                            selected_papers = [search_results[i] for i in indices if 0 <= i < len(search_results)]
                            print(f"Extracted from detailed reply: {[i+1 for i in indices]}")
                            return selected_papers[:max_papers]
                
                # 方法3: 查找所有数字模式（如 "8,6,9" 或 "8, 6, 9"）
                number_patterns = re.findall(r'\b\d+(?:\s*,\s*\d+)+\b', selected_indices)
                if number_patterns:
                    # 使用最后一个找到的数字序列（通常是最终选择）
                    numbers_str = number_patterns[-1]
                    indices = [int(x.strip()) - 1 for x in numbers_str.split(',') if x.strip().isdigit()]
                    if indices:
                        selected_papers = [search_results[i] for i in indices if 0 <= i < len(search_results)]
                        print(f"Extracted from text: {[i+1 for i in indices]}")
                        return selected_papers[:max_papers]
                
                # 如果所有方法都失败，抛出异常进入fallback逻辑
                raise ValueError("Failed to extract valid paper numbers from AI response")
                
            except (ValueError, IndexError) as e:
                print(f"Warning:  Failed to parse AI selection: {e}")
                # 如果解析失败且包含"无相关"等关键词，返回空列表
                if any(keyword in selected_indices for keyword in ['no relevant paper', 'no relevant', 'no relevant']):
                    print(f"Error:  No relevant papers found")
                    return []
                print(f"Return the first {max_papers} papers as backup")
                return search_results[:max_papers]
        else:
            print(f"Warning:  AI selection failed, return the first {max_papers} papers: {result['error']}")
            return search_results[:max_papers]
            
    except Exception as e:
        print(f"Warning:  AI selection failed, return the first {max_papers} papers: {e}")
        return search_results[:max_papers]


def process_paper_with_extract_pdf(paper_path, read_images=False):
    """使用EXTRACT_PDF处理PDF文件，返回内容和处理后的路径"""
    try:
        import subprocess
        from pathlib import Path
        
        paper_path = Path(paper_path)
        if not paper_path.exists():
            print(f"Error: PDF file does not exist: {paper_path}")
            return None, None
        
        # 使用EXTRACT_PDF处理PDF
        extract_pdf_path = Path(__file__).parent / "EXTRACT_PDF.py"
        if not extract_pdf_path.exists():
            print(f"Error:  EXTRACT_PDF.py does not exist")
            return None, None
        
        print(f"Using EXTRACT_PDF to process: {paper_path.name}")
        
        # 构建命令
        cmd = ["/usr/bin/python3", str(extract_pdf_path)]
        cmd.append(str(paper_path))
        
        if not read_images:
            cmd.extend(["--engine", "basic-asyn"])
        
        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"Error: EXTRACT_PDF processing failed: {result.stderr}")
            return None, None
        
        # 查找生成的markdown文件
        md_path = paper_path.with_suffix('.md')
        if md_path.exists():
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"PDF processing completed: {md_path.name}")
            return content, str(md_path)
        else:
            print(f"Error:  No generated markdown file found")
            return None, None
            
    except Exception as e:
        print(f"Error: Error processing PDF: {e}")
        return None, None


def search_and_download_paper(paper_description, params=None):
    """Search for paper and download if found."""
    print(f"\nSearching for papers: {paper_description}")
    
    try:
        # 步骤1: 使用AI优化搜索查询
        print(f"Step 1: Using AI to optimize search query...")
        optimized_query = optimize_search_query_with_ai(paper_description)
        
        # 步骤2: 推荐搜索引擎（如果用户没有指定）
        print(f"Step 2: Recommend search engines...")
        sources = params.get('sources') if params else None
        if not sources:
            sources = recommend_search_engines_with_ai(paper_description, optimized_query)
        else:
            print(f"Using user-specified search engines: {sources}")
        
        script_dir = Path(__file__).parent
        search_paper_path = script_dir / "SEARCH_PAPER"
        
        # 步骤3: 使用优化后的查询和推荐的搜索引擎搜索论文
        print(f"Step 3: Execute SEARCH_PAPER search...")
        
        # 对于技术主题，增加搜索结果数量以获得更好的匹配
        max_results = 15 if any(keyword in paper_description.lower() 
                               for keyword in ['algorithm', 'optimization', 'machine learning', 'deep learning', 'neural']) else 10
        
        cmd = [str(search_paper_path), optimized_query, "--max-results", str(max_results)]
        if sources:
            cmd.extend(["--sources", sources])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error: Search failed: {result.stderr}")
            return None, None, 0
            
        print(f"SEARCH_PAPER search completed")
        
        # 步骤4: 解析搜索结果
        print(f"Step 4: Parse search results...")
        search_results = parse_search_results()
        if not search_results:
            print(f"Error:  No relevant papers found")
            return None, None, 0

        print(f"Found {len(search_results)} relevant papers")
        
        # 步骤5: 使用AI筛选最佳论文
        print(f"Step 5: Using AI to select the best papers...")
        selected_papers = select_best_papers_with_ai(
            search_results, 
            paper_description, 
            max_papers=3, 
            negative_prompt=params.get('negative_prompt') if params else None
        )
        
        if not selected_papers:
            print(f"Error:  No relevant papers found, cannot continue")
            return None, None, 0
        
        # 步骤6: 显示AI推荐的论文供用户选择
        print(f"AI selection completed")
        print(f"Step 6: Display {len(selected_papers)} best papers recommended by AI:")
        for i, paper in enumerate(selected_papers):
            title = paper.get('title', 'Unknown')
            authors = paper.get('authors', [])
            author_str = ', '.join(authors[:3]) + ('...' if len(authors) > 3 else '')
            citation_count = paper.get('citation_count', 'Unknown')
            print(f"  {i+1}. {title}")
            print(f"     Authors: {author_str}")
            print(f"     Citation count: {citation_count}")
            print()
        
        # 步骤7: 让用户选择或自动选择第一篇
        print(f"Step 7: Select papers...")
        if len(selected_papers) == 1:
            selected_paper = selected_papers[0]
            print(f"Automatically select the only recommended paper")
        else:
            # 简化选择：自动选择第一篇（AI推荐的最佳论文）
            selected_paper = selected_papers[0]
            print(f"Automatically select the best paper recommended by AI: {selected_paper.get('title', 'Unknown')}")

        # 步骤8: 尝试下载论文
        print(f"Step 8: Download papers...")
        pdf_url = selected_paper.get('pdf_url')
        if not pdf_url:
            print(f"Error:  No PDF download link found")
            return None, None, 0
        
        print(f"Downloading paper: {selected_paper.get('title', 'Unknown')}")
        # 确定下载目录：测试时使用/tmp，正常使用时使用params中的output_dir
        download_dir = None
        if params and params.get('output_dir'):
            # 如果output_dir是测试目录（包含test、tmp等），使用/tmp
            output_dir_str = str(params.get('output_dir')).lower()
            if any(keyword in output_dir_str for keyword in ['test', 'tmp', '/tmp']):
                download_dir = '/tmp'
            else:
                download_dir = params.get('output_dir')
        
        downloaded_path, original_title = download_paper(
            pdf_url, 
            selected_paper.get('title', 'paper'),
            output_dir=download_dir
        )
        
        if not downloaded_path:
            print(f"Error:  Paper download failed")
            return None, None, 0
        
        # 步骤9: 使用AI给PDF重命名为简洁明了的名字
        print(f"Step 9: Generate a simple and clear filename for the PDF...")
        new_filename = generate_simple_filename_with_ai(selected_paper, paper_description)
        
        # 重命名PDF文件
        downloaded_pdf_path = Path(downloaded_path)
        new_pdf_path = downloaded_pdf_path.parent / f"{new_filename}.pdf"
        
        try:
            downloaded_pdf_path.rename(new_pdf_path)
            print(f"PDF has been renamed: {new_pdf_path.name}")
            downloaded_path = str(new_pdf_path)
        except Exception as e:
            print(f"Warning:  Renaming failed, using original filename: {e}")
        
        # 步骤10: 使用EXTRACT_PDF提取论文内容
        print(f"Step 10: Extract PDF content...")
        markdown_path = extract_pdf_content(downloaded_path, params)
        
        if not markdown_path:
            print(f"Error:  PDF content extraction failed")
            return None, None, 0
        
        # 步骤11: 读取提取的markdown内容
        print(f"Step 11: Read extracted markdown content...")
        try:
            with open(markdown_path, 'r', encoding='utf-8') as f:
                paper_content = f.read()
            
            print(f"Paper content extraction completed: {markdown_path}")
            token_count = len(paper_content.split())  # 简单的token估算
            print(f"Extracted content length: {token_count} tokens")
            
            # 检查内容长度，如果太少就中断
            min_content_length = 1000  # 最少1000个字符
            if len(paper_content.strip()) < min_content_length:
                print(f"Error: Paper content is too short ({len(paper_content)} characters < {min_content_length}), possibly extraction failed")
                raise Exception(f"Paper content extraction incomplete: only {len(paper_content)} characters, less than the minimum requirement of {min_content_length} characters")
            
            return paper_content, downloaded_path, token_count
            
        except Exception as e:
            print(f"Error: Failed to read markdown file: {e}")
            return None, None, 0
            
    except Exception as e:
        print(f"Error: Search process error: {e}")
        return None, None, 0


def generate_simple_filename_with_ai(paper_info, user_description):
    """使用AI为论文生成简洁明了的文件名"""
    try:
        title = paper_info.get('title', 'Unknown')
        authors = paper_info.get('authors', [])
        
        prompt = f"""Please generate a simple and clear English filename for the PDF file.

Paper information:
Title: {title}
Authors: {', '.join(authors[:3])}
User search description: {user_description}

Requirements:
1. The filename should be simple and clear, no more than 50 characters
2. Only use English letters, numbers, underscores, and hyphens
3. Avoid special symbols and spaces
4. Reflect the core theme of the paper
5. Easy to understand and identify

Examples:
- "3D Gaussian Splatting for Real-Time Radiance Field Rendering" -> "3DGS_Real_Time_Rendering"
- "Neural Radiance Fields" -> "NeRF"
- "Instant Neural Graphics Primitives" -> "InstantNGP"

Please only return the filename (without the .pdf extension), no other explanation: """

        result = call_openrouter_with_auto_model(prompt, model="auto")
        
        if result['success']:
            filename = result['content'].strip()
            # 清理文件名，确保符合文件系统要求
            import re
            filename = re.sub(r'[^\w\-_]', '', filename)
            filename = re.sub(r'[-_]+', '_', filename)
            
            if len(filename) > 50:
                filename = filename[:50]
            
            print(f"AI generated filename: {filename}")
            return filename
        else:
            print(f"Warning:  AI generated filename failed: {result['error']}")
            # 使用简化的标题作为备选
            import re
            safe_title = re.sub(r'[^\w\s-]', '', title)
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            return safe_title[:30]
            
    except Exception as e:
        print(f"Warning:  Error generating filename: {e}")
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
            print(f"  Enable image, formula, and table processing")
            cmd.extend(["--engine", "full"])  # 使用full模式
        else:
            print(f" Only extract text content (skip image processing)")
            cmd.extend(["--engine", "basic-asyn"])  # 使用basic-asyn模式，更快的异步处理
        
        print(f" Executing command: {' '.join(cmd)}")
        
        # 执行EXTRACT_PDF命令
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=86400)  # 1 day timeout (dummy)
        
        if result.returncode == 0:
            # 查找生成的markdown文件
            pdf_path_obj = Path(pdf_path)
            expected_md_path = pdf_path_obj.with_suffix('.md')
            
            if expected_md_path.exists():
                print(f"PDF content extraction successful: {expected_md_path}")
                return str(expected_md_path)
            else:
                print(f"Error: No expected markdown file found: {expected_md_path}")
                # 尝试查找其他可能的markdown文件
                possible_paths = [
                    pdf_path_obj.parent / f"{pdf_path_obj.stem}.md",
                    Path.cwd() / f"{pdf_path_obj.stem}.md"
                ]
                for path in possible_paths:
                    if path.exists():
                        print(f"Found markdown file: {path}")
                        return str(path)
                return None
        else:
            print(f"Error: EXTRACT_PDF execution failed:")
            print(f"    Return code: {result.returncode}")
            print(f"    Standard output: {result.stdout}")
            print(f"    Error output: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"Error:  PDF extraction timeout")
        return None
    except Exception as e:
        print(f"Error: PDF extraction error: {e}")
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
        print(f"Error: Failed to parse search results: {e}")
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
        print(f"Downloading: {pdf_url}")
        print(f"Target directory: {download_dir}")
        
        result = subprocess.run([
            str(download_path), pdf_url, str(target_path)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            if target_path.exists():
                print(f"Download successful: {target_path}")
                return str(target_path), paper_title
            else:
                print(f"Error:  Downloaded file does not exist")
                return None, None
        else:
            print(f"Error: Download failed: {result.stderr}")
            print(f"Trying other download links...")
            return None, None
            
    except Exception as e:
        print(f"Error: Download process error: {e}")
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
                raise FileNotFoundError(f"File referenced by @ symbol does not exist: {file_path}")
                
            # 检查是否是符号链接或其他特殊情况
            if not path_obj.is_file():
                raise ValueError(f"Path referenced by @ symbol is not a valid file: {file_path}")
            
            # 检查文件类型
            allowed_extensions = {'.txt', '.md', '.pdf'}
            if path_obj.suffix.lower() not in allowed_extensions:
                return f"[Unsupported file type: {file_path}, only .txt, .md, and .pdf files are supported]"
            
            # 读取文件内容
            try:
                if path_obj.suffix.lower() == '.pdf':
                    # 处理PDF文件 - 使用basic引擎进行解析
                    import tempfile
                    import subprocess
                    
                    print(f"Parsing PDF file: {file_path} (using basic engine)")
                    
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
                                    print(f"PDF parsing completed: {file_path} ({cleaned_length} characters, cleaned and saved approximately {tokens_saved} tokens)")
                                    
                                    return f"\n\n--- Referenced PDF file: {file_path} ---\n{content}\n--- File reference end ---\n"
                                else:
                                    return f"[PDF parsing failed: {file_path} - No markdown file generated]"
                            else:
                                return f"[PDF parsing failed: {file_path} - {result.stderr}]"
                        except subprocess.TimeoutExpired:
                            return f"[PDF parsing timeout: {file_path}]"
                        except Exception as e:
                            return f"[PDF parsing error: {file_path} - {str(e)}]"
                
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
                            print(f"Expanding file reference: {file_path} ({cleaned_length} characters, cleaned and saved approximately {tokens_saved} tokens)")
                        else:
                            print(f"Expanding file reference: {file_path} ({cleaned_length} characters)")
                    else:
                        print(f"Expanding file reference: {file_path} ({len(content)} characters)")
                    
                    return f"\n\n--- Referenced file: {file_path} ---\n{content}\n--- File reference end ---\n"
                
            except (FileNotFoundError, ValueError):
                # 重新抛出文件不存在或路径无效的异常
                raise
            except Exception as e:
                return f"[Failed to read file: {file_path} - {str(e)}]"
                
        except (FileNotFoundError, ValueError):
            # 重新抛出文件不存在或路径无效的异常
            raise
        except Exception as e:
            return f"[File path parsing failed: {file_path} - {str(e)}]"
    
    # 替换所有文件引用
    expanded_text = re.sub(pattern, replace_reference, text)
    
    # 检查是否有引用被展开
    has_file_reference = expanded_text != text
    if has_file_reference:
        print(f"Detected file reference, automatically expanded and cleaned useless content")
    
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
        prompt = f"""You are an expert assistant for the LEARN tool. Please generate the corresponding LEARN command based on the user's description.

LEARN工具文档：
{learn_doc}

用户描述：{description}

Please analyze the user's needs and generate the most appropriate LEARN command. Consider the following factors:
1. Whether the user needs to learn specific papers, topics, or general knowledge
2. Learning level (beginner, intermediate, advanced, expert)
3. Explanation style (simple and clear, detailed and deep, rich examples, theoretical oriented)
4. Whether special options are needed (e.g., --file, --description, --negative, --read-images, etc.)
5. Output directory suggestion
6. OpenRouter model options:
   - --model: Specify a specific AI model
   - --max-tokens: Control output length
   - --temperature: Control creativity (0.0-2.0, the higher the value, the more creative)
   - --key: Use a specific API key

Please return the complete LEARN command starting with "LEARN", without any other explanation.
If a file path is needed, use placeholders like "/path/to/file".
If the user needs a creative response, add the --temperature parameter.
If the user needs to specify a model, add the --model parameter.

Example format:
LEARN -o ~/tutorials -m beginner -s simple and clear "Python basic programming"
LEARN -o ~/tutorials -m intermediate --file "/path/to/paper.pdf"
LEARN -o ~/tutorials -m advanced -d "Deep learning" --negative "GAN"
LEARN -o ~/tutorials -m expert -s rich examples --temperature 0.8 "Creative writing skills"
LEARN -o ~/tutorials -m intermediate --model "deepseek/deepseek-r1" --max-tokens 8000 "Machine learning algorithms"

Generated command: """

        print(f"Calling OpenRouter to analyze user needs and generate LEARN command...")
        result = call_openrouter_with_auto_model(prompt, model="auto")
        
        if result['success']:
            command = result['content'].strip()
            print(f"\nGenerated LEARN command:")
            print(f"```bash")
            print(f"{command}")
            print(f"```")
            return True
        else:
            print(f"Error: Command generation failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"Error: Error generating command: {e}")
        return False


def main():
    """Main function."""
    # 启动全局计时器 - 放在最开始，确保在任何OpenRouter调用之前
    start_timer()
    
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
        print(f"LEARN - Intelligent learning system")
        print(f"Starting interactive mode...")
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
            print(f"Brainstorming completed!")
            return 0
        
        # 创建文件
        print(f"\nCreating tutorial files...")
        success = create_learning_files_from_responses(
            params, 
            result['tutorial_response'], 
            result['question_response'], 
            result['prompts_and_responses']
        )
        
        if success:
            print(f"File creation completed!")
            return 0
        else:
            print(f"Error:  File creation failed")
            return 1
    
    # Parse direct command
    try:
        # 先检查是否是--help模式
        if '--help' in sys.argv or '-h' in sys.argv:
            parser = argparse.ArgumentParser(description='LEARN - Intelligent learning system')
            parser.add_argument('topic', nargs='?', help='Learning topic')
            parser.add_argument('-o', '--output-dir', help='Output directory')
            parser.add_argument('-m', '--mode', choices=list(MODE_MAPPING.keys()),
                               default='intermediate', help='Learning level (beginner, intermediate, advanced, expert)')
            parser.add_argument('-s', '--style', choices=list(STYLE_MAPPING.keys()),
                               default='detailed and deep', help='Explanation style (simple and clear, detailed and deep, rich examples, theoretical oriented)')
            parser.add_argument('--file', help='Directly process file path (supports PDF, MD, TXT)')
            parser.add_argument('-u', '--url', help='Paper URL')
            parser.add_argument('-d', '--description', help='Paper description/search keywords')
            parser.add_argument('--negative', help='Negative prompt: specify content or paper type you do not want')
            parser.add_argument('--read-images', action='store_true', help='Process images, formulas, and tables in PDF')
            parser.add_argument('--gen-command', help='Generate LEARN command based on description')
            parser.add_argument('--paper-based', action='store_true', help='Force use of paper-based learning mode, even if only a description is provided')
            parser.add_argument('--sources', help='Specify paper search engines, separated by commas (arxiv,google_scholar), default is automatic recommendation')
            parser.add_argument('--model', help='指定OpenRouter模型')
            parser.add_argument('--max-tokens', type=int, help='最大token数')
            parser.add_argument('--temperature', type=float, help='温度参数 (0.0-2.0，控制回复的创造性)')
            parser.add_argument('--key', help='指定OpenRouter API密钥')
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
            print(f"Brainstorming completed!")
            return 0
        
        # 创建文件
        print(f"\nCreating tutorial files...")
        success = create_learning_files_from_responses(
            params, 
            result['tutorial_response'], 
            result['question_response'], 
            result['prompts_and_responses']
        )
        
        if success:
            print(f"File creation completed!")
            return 0
        else:
            print(f"Error:  File creation failed")
            return 1
    
    except Exception as e:
        print(f"Error: Error during runtime: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())