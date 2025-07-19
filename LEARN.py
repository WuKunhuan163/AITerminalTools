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
        
        root.destroy()
        
        if selected_dir:
            print(f"选择的目录: {selected_dir}")
            return selected_dir
        else:
            print("未选择目录")
            return None
            
    except ImportError:
        print("tkinter不可用，请手动输入目录路径")
        output_dir = input("请输入目标目录路径: ").strip()
        if output_dir and Path(output_dir).exists():
            return output_dir
        else:
            print("无效的目录路径")
            return None
    except Exception as e:
        print(f"目录选择出错: {e}")
        print("请手动输入目录路径")
        output_dir = input("请输入目标目录路径: ").strip()
        if output_dir and Path(output_dir).exists():
            return output_dir
        else:
            print("无效的目录路径")
            return None


def get_topic_type():
    """Get the type of learning topic from user."""
    print("你想学习什么内容？")
    choice = interactive_select("学习类型:", ["通用主题 (如Python、机器学习等)", "学术论文 (PDF文件)"])
    if choice is None:
        return None
    elif choice == 0:
        return "general"
    else:
        return "paper"


def get_general_topic_params():
    """Get parameters for general topic learning."""
    # Get topic
    topic = input("请输入要学习的主题: ").strip()
    if not topic:
        topic = "Python basics"
        print(f"使用默认主题: {topic}")
    
    # Get mode
    mode_choice = interactive_select("学习模式:", ["Beginner (初学者)", "Advanced (高级)", "Practical (实践型)"])
    if mode_choice is None:
        return None
    mode = ["Beginner", "Advanced", "Practical"][mode_choice]
    
    # Get style
    style_choice = interactive_select("解释风格:", ["Rigorous (严谨)", "Witty (幽默)"])
    if style_choice is None:
        return None
    style = ["Rigorous", "Witty"][style_choice]
    
    # Get output directory
    output_dir = get_output_directory()
    if output_dir is None:
        return None
    
    return {
        "topic": topic,
        "mode": mode,
        "style": style,
        "type": "general",
        "output_dir": output_dir
    }


def get_paper_input_type():
    """Get paper input type."""
    return interactive_select(
        "论文输入方式:", 
        [
            "已处理的Markdown文件 (.md)", 
            "PDF文件路径",
            "论文URL链接", 
            "论文描述/标题 (自动搜索)"
        ]
    )


def show_file_selection_guidance():
    """Show tkinter dialog to guide user through file selection process."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        # Create root window but hide it
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        # Show guidance message
        result = messagebox.askyesnocancel(
            "LEARN - 论文文件选择",
            "接下来将打开文件选择对话框。\n\n"
            "请选择以下类型的文件：\n"
            "• PDF论文文件 (.pdf)\n"
            "• Markdown论文文件 (.md)\n\n"
            "如果您没有本地文件，请点击\"取消\"，\n"
            "然后可以提供论文URL或描述进行搜索。\n\n"
            "是否继续文件选择？",
            icon='question'
        )
        
        root.destroy()
        return result  # True = Yes, False = No, None = Cancel
        
    except ImportError:
        print("📁 接下来将打开文件选择对话框...")
        print("   - 可以选择PDF或Markdown论文文件")
        print("   - 如果没有本地文件，可以取消选择，然后提供URL或描述")
        return True


def get_paper_params():
    """Get parameters for paper learning with enhanced input handling."""
    # Show guidance dialog first
    guidance_result = show_file_selection_guidance()
    
    paper_content = None
    paper_path = None
    paper_url = None
    paper_description = None
    input_type = None
    
    if guidance_result is True:  # User chose to proceed with file selection
        print("📁 打开文件选择对话框...")
        try:
            script_dir = Path(__file__).parent
            file_select_path = script_dir / "FILE_SELECT"
            
            result = subprocess.run([
                str(file_select_path), "--types", "pdf,md", "--title", "选择论文文件 (PDF或Markdown)"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                selected_file = result.stdout.strip()
                if selected_file and Path(selected_file).exists():
                    print(f"选择的文件: {selected_file}")
                    
                    if selected_file.endswith('.md'):
                        # Markdown file
                        with open(selected_file, 'r', encoding='utf-8') as f:
                            paper_content = f.read()
                        paper_path = selected_file
                        input_type = 0
                        print("✅ 已读取Markdown论文内容")
                        
                    elif selected_file.endswith('.pdf'):
                        # PDF file
                        paper_path = selected_file
                        input_type = 1
                        print("✅ 已选择PDF论文文件")
                        
                else:
                    print("⚠️  文件选择被取消或文件无效")
                    guidance_result = None  # Treat as cancel
            else:
                print("⚠️  文件选择对话框执行失败")
                guidance_result = None  # Treat as cancel
                
        except Exception as e:
            print(f"❌ 文件选择过程出错: {e}")
            guidance_result = None  # Treat as cancel
    
    # If file selection was cancelled or failed, ask for URL or description
    if guidance_result is None or guidance_result is False:
        print("\n📝 请提供论文信息：")
        
        choice = interactive_select(
            "论文来源:", 
            ["论文URL链接", "论文描述/标题 (将自动搜索)"]
        )
        
        if choice is None:
            return None
        
        if choice == 0:  # URL
            paper_url = input("请输入论文URL: ").strip()
            if not paper_url:
                print("❌ 未输入有效的URL")
                return None
            print(f"论文URL: {paper_url}")
            input_type = 2
            
        elif choice == 1:  # Description
            paper_description = input("请输入论文描述或标题: ").strip()
            if not paper_description:
                print("❌ 未输入有效的描述")
                return None
            print(f"论文描述: {paper_description}")
            input_type = 3
    
    if input_type is None:
        print("❌ 未选择有效的论文输入方式")
        return None
    
    # Get image analysis option (only for PDF processing)
    read_images = False
    if input_type == 1 or (input_type == 2 and paper_url):  # PDF file or URL
        image_choice = interactive_select("是否分析图片:", ["否", "是"])
        if image_choice is None:
            return None
        read_images = image_choice == 1

    # Get learning mode and style
    mode_choice = interactive_select("学习模式:", ["Beginner (初学者)", "Advanced (高级)", "Practical (实践型)"])
    if mode_choice is None:
        return None
    mode = ["Beginner", "Advanced", "Practical"][mode_choice]

    style_choice = interactive_select("解释风格:", ["Rigorous (严谨)", "Witty (幽默)"])
    if style_choice is None:
        return None
    style = ["Rigorous", "Witty"][style_choice]

    # Get output directory
    output_dir = get_output_directory()
    if output_dir is None:
        return None

    return {
        "paper_path": paper_path,
        "paper_content": paper_content,
        "paper_url": paper_url,
        "paper_description": paper_description,
        "input_type": input_type,
        "read_images": read_images,
        "mode": mode,
        "style": style,
        "type": "paper",
        "output_dir": output_dir
    }


def run_interactive_mode():
    """Run interactive mode to collect parameters."""
    # Clear terminal
    clear_terminal()
    
    # Get topic type
    topic_type = get_topic_type()
    if topic_type is None:
        print("设置已取消")
        return None
    
    # Get parameters based on type
    if topic_type == "general":
        params = get_general_topic_params()
    else:
        params = get_paper_params()
    
    if params is None:
        print("设置已取消")
        return None
    
    return params


def parse_direct_command(args):
    """Parse direct command arguments."""
    parser = argparse.ArgumentParser(description="LEARN - 智能学习系统")
    parser.add_argument("topic", help="学习主题或PDF文件路径")
    parser.add_argument("--type", choices=["general", "paper"], help="学习类型 (general: 通用主题, paper: 学术论文)")
    parser.add_argument("--mode", choices=["Beginner", "Advanced", "Practical"], help="学习模式")
    parser.add_argument("--style", choices=["Rigorous", "Witty"], help="解释风格")
    parser.add_argument("--output-dir", help="输出目录 (如果未提供，将弹出选择对话框)")
    parser.add_argument("--read-images", action="store_true", help="分析PDF中的图片")
    parser.add_argument("--no-auto-create", action="store_true", help="不自动创建文件，只获取结构建议")
    parser.add_argument("--not-default", action="store_true", help="不使用默认设置，启用交互式选择")
    
    parsed_args = parser.parse_args(args)
    
    # 处理输出目录逻辑
    if not parsed_args.output_dir:
        if parsed_args.not_default:
            # 使用交互式选择
            print("📁 未指定输出目录，请选择输出文件夹...")
            parsed_args.output_dir = get_output_directory()
            if not parsed_args.output_dir:
                print("❌ 未选择输出目录，退出程序")
                return None
        else:
            # 使用默认设置：当前目录
            parsed_args.output_dir = os.getcwd()
            print(f"📁 使用默认输出目录：{parsed_args.output_dir}")
    
    # 处理mode和style的默认值
    if not parsed_args.mode:
        if parsed_args.not_default:
            # 使用交互式选择（这里应该调用交互式选择函数）
            parsed_args.mode = "Beginner"  # 临时使用默认值，后续可以改为交互式
        else:
            # 使用默认设置：第一项
            parsed_args.mode = "Beginner"
            print(f"📚 使用默认学习模式：{parsed_args.mode}")
    
    if not parsed_args.style:
        if parsed_args.not_default:
            # 使用交互式选择（这里应该调用交互式选择函数）
            parsed_args.style = "Rigorous"  # 临时使用默认值，后续可以改为交互式
        else:
            # 使用默认设置：第一项
            parsed_args.style = "Rigorous"
            print(f"🎨 使用默认解释风格：{parsed_args.style}")
    
    # 检查文件覆盖（仅在非--not-default模式下）
    if not parsed_args.not_default and not parsed_args.no_auto_create:
        if check_and_confirm_overwrite(parsed_args.output_dir):
            print("✅ 确认继续")
        else:
            print("❌ 用户取消操作")
            return None
    
    # Determine if it's a paper or general topic
    # Check if type is explicitly specified
    if parsed_args.type:
        if parsed_args.type == "paper":
            # Force paper type regardless of topic content
            if parsed_args.topic.endswith('.pdf'):
                return {
                    "paper_path": parsed_args.topic,
                    "input_type": 1,  # PDF file
                    "read_images": parsed_args.read_images,
                    "mode": parsed_args.mode,
                    "style": parsed_args.style,
                    "type": "paper",
                    "output_dir": parsed_args.output_dir,
                    "no_auto_create": parsed_args.no_auto_create,
                    "not_default": parsed_args.not_default
                }
            elif parsed_args.topic.endswith('.md'):
                try:
                    with open(parsed_args.topic, 'r', encoding='utf-8') as f:
                        paper_content = f.read()
                except FileNotFoundError:
                    print(f"❌ 找不到Markdown文件: {parsed_args.topic}")
                    return None
                except Exception as e:
                    print(f"❌ 读取Markdown文件失败: {e}")
                    return None
                    
                return {
                    "paper_path": parsed_args.topic,
                    "paper_content": paper_content,
                    "input_type": 0,  # Markdown file
                    "read_images": False,
                    "mode": parsed_args.mode,
                    "style": parsed_args.style,
                    "type": "paper",
                    "output_dir": parsed_args.output_dir,
                    "no_auto_create": parsed_args.no_auto_create,
                    "not_default": parsed_args.not_default
                }
            elif parsed_args.topic.startswith('http://') or parsed_args.topic.startswith('https://'):
                return {
                    "paper_url": parsed_args.topic,
                    "input_type": 2,  # URL
                    "read_images": parsed_args.read_images,
                    "mode": parsed_args.mode,
                    "style": parsed_args.style,
                    "type": "paper",
                    "output_dir": parsed_args.output_dir,
                    "no_auto_create": parsed_args.no_auto_create,
                    "not_default": parsed_args.not_default
                }
            else:
                # Treat as paper description
                return {
                    "paper_description": parsed_args.topic,
                    "input_type": 3,  # Description/Search
                    "read_images": parsed_args.read_images,
                    "mode": parsed_args.mode,
                    "style": parsed_args.style,
                    "type": "paper",
                    "output_dir": parsed_args.output_dir,
                    "no_auto_create": parsed_args.no_auto_create,
                    "not_default": parsed_args.not_default
                }
        else:  # general
            # Force general type
            return {
                "topic": parsed_args.topic,
                "mode": parsed_args.mode,
                "style": parsed_args.style,
                "type": "general",
                "output_dir": parsed_args.output_dir,
                "no_auto_create": parsed_args.no_auto_create,
                "not_default": parsed_args.not_default
            }
    
    # Auto-detect type if not specified
    if parsed_args.topic.endswith('.pdf'):
        return {
            "paper_path": parsed_args.topic,
            "input_type": 1,  # PDF file
            "read_images": parsed_args.read_images,
            "mode": parsed_args.mode,
            "style": parsed_args.style,
            "type": "paper",
            "output_dir": parsed_args.output_dir,
            "no_auto_create": parsed_args.no_auto_create,
            "not_default": parsed_args.not_default
        }
    elif parsed_args.topic.endswith('.md'):
        # Markdown file
        try:
            with open(parsed_args.topic, 'r', encoding='utf-8') as f:
                paper_content = f.read()
        except FileNotFoundError:
            print(f"❌ 找不到Markdown文件: {parsed_args.topic}")
            return None
        except Exception as e:
            print(f"❌ 读取Markdown文件失败: {e}")
            return None
            
        return {
            "paper_path": parsed_args.topic,
            "paper_content": paper_content,
            "input_type": 0,  # Markdown file
            "read_images": False,  # Not applicable for MD files
            "mode": parsed_args.mode,
            "style": parsed_args.style,
            "type": "paper",
            "output_dir": parsed_args.output_dir,
            "no_auto_create": parsed_args.no_auto_create,
            "not_default": parsed_args.not_default
        }
    elif parsed_args.topic.startswith('http://') or parsed_args.topic.startswith('https://'):
        # URL
        return {
            "paper_url": parsed_args.topic,
            "input_type": 2,  # URL
            "read_images": parsed_args.read_images,
            "mode": parsed_args.mode,
            "style": parsed_args.style,
            "type": "paper",
            "output_dir": parsed_args.output_dir,
            "no_auto_create": parsed_args.no_auto_create,
            "not_default": parsed_args.not_default
        }
    else:
        # Check if it's a file path that exists
        if os.path.exists(parsed_args.topic):
            if parsed_args.topic.endswith('.pdf'):
                return {
                    "paper_path": parsed_args.topic,
                    "input_type": 1,  # PDF file
                    "read_images": parsed_args.read_images,
                    "mode": parsed_args.mode,
                    "style": parsed_args.style,
                    "type": "paper",
                    "output_dir": parsed_args.output_dir,
                    "no_auto_create": parsed_args.no_auto_create,
                    "not_default": parsed_args.not_default
                }
            elif parsed_args.topic.endswith('.md'):
                try:
                    with open(parsed_args.topic, 'r', encoding='utf-8') as f:
                        paper_content = f.read()
                except Exception as e:
                    print(f"❌ 读取Markdown文件失败: {e}")
                    return None
                    
                return {
                    "paper_path": parsed_args.topic,
                    "paper_content": paper_content,
                    "input_type": 0,  # Markdown file
                    "read_images": False,
                    "mode": parsed_args.mode,
                    "style": parsed_args.style,
                    "type": "paper",
                    "output_dir": parsed_args.output_dir,
                    "no_auto_create": parsed_args.no_auto_create,
                    "not_default": parsed_args.not_default
                }
        
        # Treat as general topic or paper description
        # If it looks like a paper description (contains academic keywords), treat as paper search
        academic_keywords = ['paper', 'research', 'study', 'analysis', 'algorithm', 'model', 'neural', 'learning', 'deep', 'machine']
        if any(keyword in parsed_args.topic.lower() for keyword in academic_keywords):
            return {
                "paper_description": parsed_args.topic,
                "input_type": 3,  # Description/Search
                "read_images": parsed_args.read_images,
                "mode": parsed_args.mode,
                "style": parsed_args.style,
                "type": "paper",
                "output_dir": parsed_args.output_dir,
                "no_auto_create": parsed_args.no_auto_create,
                "not_default": parsed_args.not_default
            }
        else:
            # General topic
            return {
                "topic": parsed_args.topic,
                "mode": parsed_args.mode,
                "style": parsed_args.style,
                "type": "general",
                "output_dir": parsed_args.output_dir,
                "no_auto_create": parsed_args.no_auto_create,
                "not_default": parsed_args.not_default
            }


def generate_content_structure_prompt(params):
    """Generate a detailed prompt for content structure planning."""
    if params["type"] == "general":
        # General topic prompt
        topic = params["topic"]
        mode = params["mode"]
        style = params["style"]
        
        prompt = f"""请对"{topic}"这个主题进行全面的头脑风暴（brainstorming），为创建教程提供丰富的想法和建议。

学习模式：{mode}
解释风格：{style}

请从以下角度提供尽可能多的建议：

1. **核心概念和知识点**
   - 这个主题包含哪些核心概念？
   - 哪些是{mode}水平学习者必须掌握的？
   - 哪些概念之间有依赖关系？

2. **学习路径和章节结构**
   - 建议的学习顺序是什么？
   - 如何从基础到进阶循序渐进？
   - 每个阶段的重点是什么？

3. **实践和练习**
   - 有哪些经典的练习题目？
   - 哪些实际项目适合练习？
   - 如何设计从简单到复杂的练习序列？

4. **常见问题和难点**
   - 学习者通常在哪些地方遇到困难？
   - 有哪些常见的误解需要澄清？
   - 如何帮助学习者克服这些难点？

5. **资源和工具**
   - 需要哪些工具或软件？
   - 有哪些有用的参考资料？
   - 推荐哪些在线资源？

6. **应用场景**
   - 这个主题在实际中有哪些应用？
   - 有哪些具体的应用案例？
   - 如何将理论与实践结合？

请提供详细、全面的建议，越多越好！这些建议将用于构建一个完整的学习教程。"""

        return prompt

    else:
        # Paper-based prompt - need to prepare paper content first
        print("\n📄 准备论文内容...")
        
        # Prepare paper content based on input type
        paper_result = prepare_paper_content(params)
        if paper_result is None:
            return None
            
        paper_content, paper_path, token_count = paper_result
        
        # Store paper content in params for later use
        params["paper_content"] = paper_content
        params["paper_path"] = paper_path
        params["token_count"] = token_count
        
        # Ask user about brainstorming
        print(f"\n🧠 论文内容已准备完毕 (预估 {token_count:,} tokens)")
        
        # Auto-proceed with brainstorming if:
        # 1. Not using --not-default (default mode), OR
        # 2. Using free model and content fits within context
        should_auto_proceed = False
        
        if not params.get('not_default', False):
            # Default mode - auto proceed
            should_auto_proceed = True
            print("🚀 默认模式：自动开始AI头脑风暴分析...")
        else:
            # Check if using free model and content fits
            models, model_details = get_openrouter_models()
            if models and params.get("selected_model"):
                selected_model = params["selected_model"]
                details = model_details.get(selected_model, {})
                is_free_model = details.get('input_cost_per_1m', 0) == 0
                context_length = details.get('context_length', 0)
                
                if is_free_model and context_length and token_count < context_length * 0.8:  # Use 80% of context as safe limit
                    should_auto_proceed = True
                    print("🚀 免费模型且内容适量：自动开始AI头脑风暴分析...")
        
        if not should_auto_proceed:
            while True:
                try:
                    choice = input("是否要进行AI头脑风暴分析？ (Y/n): ").strip().lower()
                    if choice in ['y', 'yes', '']:
                        break
                    elif choice in ['n', 'no']:
                        print("跳过头脑风暴，直接进入教程生成...")
                        return None  # Skip brainstorming
                    else:
                        print("请输入 y 或 n")
                except KeyboardInterrupt:
                    print("\n操作已取消")
                    return None
        
        # Get OpenRouter models and check token limits
        print("\n🤖 检查模型token限制...")
        models, model_details = get_openrouter_models()
        if not models:
            print("❌ 无法获取可用模型列表")
            return None
        
        # Use already selected model from params if available
        if params.get("selected_model") and params.get("max_tokens") is not None:
            selected_model = params["selected_model"]
            max_tokens = params["max_tokens"]
            print(f"✅ 使用已选择的模型: {selected_model}")
        else:
            # This shouldn't happen in normal flow, but as fallback
            selected_model, max_tokens = select_openrouter_model(params)
            if not selected_model:
                print("❌ 未选择模型")
                return None
        
        # Check if content will be truncated
        estimated_prompt_tokens = count_tokens("基于论文进行头脑风暴分析...") + token_count
        
        if max_tokens and estimated_prompt_tokens > max_tokens:
            print(f"\n⚠️  警告：输入内容可能会被截断")
            print(f"   论文内容: {token_count:,} tokens")
            print(f"   模型限制: {max_tokens:,} tokens") 
            print(f"   预估总输入: {estimated_prompt_tokens:,} tokens")
            
            # Calculate truncation point
            available_tokens = max_tokens - 1000  # Reserve 1000 tokens for prompt structure
            if available_tokens > 0:
                truncation_chars = available_tokens * 4  # Approximate characters
                print(f"   内容将被截断到约 {available_tokens:,} tokens ({truncation_chars:,} 字符)")
                
                while True:
                    try:
                        choice = input("\n继续处理 (使用截断的内容) 还是取消？ (c/Q): ").strip().lower()
                        if choice in ['c', 'continue']:
                            # Truncate content
                            paper_content = paper_content[:truncation_chars]
                            params["paper_content"] = paper_content
                            params["token_count"] = count_tokens(paper_content)
                            print(f"✂️  内容已截断到 {params['token_count']:,} tokens")
                            break
                        elif choice in ['q', 'quit', '']:
                            print("操作已取消")
                            return None
                        else:
                            print("请输入 c (继续) 或 q (退出)")
                    except KeyboardInterrupt:
                        print("\n操作已取消")
                        return None
            else:
                print("❌ 内容过长，无法处理")
                return None
        elif max_tokens is None:
            print(f"✅ 使用免费模型，无token限制 (论文内容: {token_count:,} tokens)")
        else:
            print(f"✅ 内容大小合适 (论文: {token_count:,} tokens, 限制: {max_tokens:,} tokens)")
        
        # Store selected model info
        params["selected_model"] = selected_model
        params["max_tokens"] = max_tokens
        
        mode = params["mode"]
        style = params["style"]
        read_images = params.get("read_images", False)
        
        # Generate prompt with paper content
        prompt = f"""请基于以下学术论文内容进行全面的头脑风暴分析，为创建学习教程提供详细建议。

**论文内容：**
{paper_content}

**教程要求：**
- 学习模式：{mode}
- 解释风格：{style}
- 图片分析：{"已启用" if read_images else "未启用"}

请从以下角度提供详细的教程设计建议：

1. **论文核心内容分析**
   - 论文的主要贡献和创新点是什么？
   - 关键概念和技术有哪些？
   - 论文解决了什么问题？

2. **教程章节结构建议**
   - 如何将论文内容转化为{mode}水平的教程章节？
   - 建议的学习顺序和章节划分？
   - 每个章节应该重点讲解什么内容？

3. **概念解释策略**
   - 哪些概念需要详细解释？
   - 如何用{style}的风格解释复杂概念？
   - 需要哪些背景知识铺垫？

4. **实践练习设计**
   - 基于论文内容可以设计哪些理解题？
   - 有哪些实际应用练习？
   - 如何设计批判性思考题？

5. **教学重点和难点**
   - 学习者可能在哪些地方遇到困难？
   - 如何帮助理解论文中的创新点？
   - 需要特别强调哪些内容？

请提供详细、具体的建议，这将用于生成完整的学习教程！"""

        return prompt


def get_openrouter_models():
    """Get available OpenRouter models with details (only useable ones)."""
    try:
        # 直接调用OPENROUTER --list，设置RUN_DATA_FILE环境变量
        env = os.environ.copy()
        env['RUN_DATA_FILE'] = '/tmp/dummy_run_data.json'
        
        script_dir = Path(__file__).parent
        openrouter_path = script_dir / "OPENROUTER.py"
        
        result = subprocess.run([
            sys.executable, str(openrouter_path), "--list"
        ], capture_output=True, text=True, timeout=30, env=env)
        
        if result.returncode == 0:
            try:
                import json
                import re
                
                # 清理ANSI转义序列
                clean_output = re.sub(r'\x1b\[[0-9;]*[mJHK]', '', result.stdout)
                
                response_data = json.loads(clean_output)
                
                if response_data.get('success'):
                    # 从JSON中直接获取模型列表和详细信息
                    models = response_data.get('models', [])
                    model_details = response_data.get('model_details', {})
                    
                    if models:
                        return models, model_details
                    else:
                        print("⚠️  没有找到可用的OpenRouter模型", file=sys.stderr)
                        return [], {}
                else:
                    print(f"⚠️  获取模型列表失败: {response_data.get('message', 'Unknown error')}", file=sys.stderr)
                    return [], {}
                    
            except json.JSONDecodeError:
                print("⚠️  解析模型列表JSON失败", file=sys.stderr)
                return [], {}
        else:
            print(f"⚠️  调用OPENROUTER --list失败: {result.stderr}", file=sys.stderr)
            return [], {}
            
    except Exception as e:
        print(f"⚠️  获取OpenRouter模型列表时出错: {e}", file=sys.stderr)
        return [], {}


def select_openrouter_model(params=None):
    """Let user select OpenRouter model."""
    print("\n🤖 选择AI模型...")
    
    # 获取可用模型和详细信息
    models, model_details = get_openrouter_models()
    
    if not models:
        print("❌ 没有可用的OpenRouter模型", file=sys.stderr)
        models, model_details = get_openrouter_models()  # 重试一次
        if not models:
            print("❌ 重试后仍然没有可用的OpenRouter模型", file=sys.stderr)
            return None, None
    
    # 检查是否使用默认设置
    if params and not params.get('not_default', False):
        selected_model = models[0]
        print(f"🤖 使用默认模型: {selected_model}")
    else:
        # 交互式选择
        print("可用模型:")
        for i, model in enumerate(models):
            # 显示模型信息包括context length
            details = model_details.get(model, {})
            context_length = details.get('context_length', 'Unknown')
            cost_info = ""
            if details.get('input_cost_per_1m', 0) == 0:
                cost_info = " (免费)"
            else:
                cost_info = f" (${details.get('input_cost_per_1m', 0):.1f}/$M)"
            print(f"  {i+1}. {model} [Context: {context_length:,}]{cost_info}")
        
        while True:
            try:
                choice = input(f"选择模型 (1-{len(models)}, 默认: 1): ").strip()
                if not choice:
                    selected_model = models[0]
                    break
                
                choice_num = int(choice) - 1
                if 0 <= choice_num < len(models):
                    selected_model = models[choice_num]
                    break
                else:
                    print(f"请输入 1 到 {len(models)} 之间的数字")
            except ValueError:
                print(f"请输入有效的数字")
            except KeyboardInterrupt:
                print("\n取消选择，使用默认模型")
                # 获取第一个可用模型
                models, model_details = get_openrouter_models()
                if models:
                    return models[0], None
                return None, None
        
        print(f"选择的模型: {selected_model}")
    
    # 获取模型详细信息
    details = model_details.get(selected_model, {})
    context_length = details.get('context_length')
    
    # 计算max_tokens为context_length的1/4
    max_tokens = None
    if context_length:
        max_tokens = context_length // 4
        print(f"📊 模型信息: Context Length: {context_length:,}, Max Tokens: {max_tokens:,}")
    
    # 检查是否为免费模型
    is_free_model = details.get('input_cost_per_1m', 0) == 0
    
    if not is_free_model and max_tokens:
        # 检查是否是默认模型（第一个模型）
        is_default_model = selected_model == models[0]
        
        # 只有非默认模型才显示付费提示
        if not is_default_model:
            print(f"\n💰 这是付费模型，当前max_tokens设置为: {max_tokens:,}")
            while True:
                try:
                    choice = input(f"是否要修改max_tokens设置？ (y/N): ").strip().lower()
                    if choice in ['y', 'yes']:
                        while True:
                            try:
                                new_max_tokens = input(f"请输入max_tokens (当前: {max_tokens:,}, 最大: {context_length:,}): ").strip()
                                if not new_max_tokens:
                                    break  # 使用默认值
                                
                                new_max_tokens = int(new_max_tokens)
                                if 1 <= new_max_tokens <= context_length:
                                    max_tokens = new_max_tokens
                                    print(f"✅ Max tokens设置为: {max_tokens:,}")
                                    break
                                else:
                                    print(f"请输入 1 到 {context_length:,} 之间的数字")
                            except ValueError:
                                print("请输入有效的数字")
                        break
                    elif choice in ['n', 'no', '']:
                        break
                    else:
                        print("请输入 y 或 n")
                except KeyboardInterrupt:
                    print("\n使用默认设置")
                    break
    
    return selected_model, max_tokens


def call_openrouter_for_structure(prompt, model=None, max_tokens=None, retry_count=0):
    """Call OpenRouter API to get content structure suggestions with retry mechanism."""
    import time
    
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
            models = get_openrouter_models()
            if not models:
                return None, {"error": "No useable models available"}
            model = models[0]
        
        print(f"🤖 使用模型: {model}", file=sys.stderr)
        if max_tokens:
            print(f"🔢 最大tokens: {max_tokens}", file=sys.stderr)
        print("⏳ 这可能需要一会，请耐心等待...", file=sys.stderr)
        
        # 构建命令 - 使用RUN --show调用OPENROUTER工具
        cmd = [sys.executable, str(run_path), "--show", "OPENROUTER", prompt]
        
        if model:
            cmd.extend(["--model", model])
        
        # 传入max-tokens参数（OPENROUTER工具会自动处理动态调整）
        if max_tokens:
            cmd.extend(["--max-tokens", str(max_tokens)])
        
        # 记录开始时间
        start_time = time.time()
        
        # 使用RUN --show模式调用OPENROUTER工具，避免响应被截断
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                stdout, stderr = process.communicate(timeout=60)
                
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
                import json
                import re
                
                # 清理ANSI转义序列
                clean_output = re.sub(r'\x1b\[[0-9;]*[mJKH]', '', result.stdout)
                
                response_data = json.loads(clean_output)
                
                if response_data.get('success'):
                    # 检查是否是RUN --show的包装格式
                    if 'output' in response_data:
                        # 尝试解析output字段中的JSON
                        try:
                            output_content = response_data['output']
                            if output_content.strip().startswith('{'):
                                # output是JSON格式
                                inner_data = json.loads(output_content)
                                if inner_data.get('success'):
                                    response_content = inner_data.get('content', '')
                                    usage = inner_data.get('usage', {})
                                    prompt_tokens = usage.get('input_tokens', 0)
                                    completion_tokens = usage.get('output_tokens', 0)
                                    total_tokens = usage.get('total_tokens', 0)
                                    cost = inner_data.get('cost', 0)
                                else:
                                    response_content = output_content
                                    prompt_tokens = completion_tokens = total_tokens = cost = 0
                            else:
                                # output是纯文本，但检查是否有RUN_DATA_FILE
                                response_content = output_content
                                prompt_tokens = completion_tokens = total_tokens = cost = 0
                                # 尝试从RUN_DATA_FILE中读取token信息
                                if '_RUN_DATA_file' in response_data:
                                    try:
                                        with open(response_data['_RUN_DATA_file'], 'r', encoding='utf-8') as f:
                                            run_data = json.load(f)
                                            if 'usage' in run_data:
                                                usage = run_data['usage']
                                                prompt_tokens = usage.get('input_tokens', 0)
                                                completion_tokens = usage.get('output_tokens', 0)
                                                total_tokens = usage.get('total_tokens', 0)
                                            # 读取cost信息
                                            cost = run_data.get('cost', 0)
                                    except (FileNotFoundError, json.JSONDecodeError, KeyError):
                                        pass
                        except json.JSONDecodeError:
                            # 如果解析失败，直接使用output内容
                            response_content = response_data['output']
                            prompt_tokens = completion_tokens = total_tokens = cost = 0
                    else:
                        # 直接从response_data中提取
                        response_content = response_data.get('content', response_data.get('response', response_data.get('message', '')))
                        usage = response_data.get('usage', {})
                        prompt_tokens = usage.get('input_tokens', 0)
                        completion_tokens = usage.get('output_tokens', 0)
                        total_tokens = usage.get('total_tokens', 0)
                        cost = response_data.get('cost', 0)
                    
                    # 检查响应是否为空或只包含空白字符
                    if not response_content or response_content.strip() == '':
                        print(f"⚠️  OpenRouter API返回空内容 (耗时: {api_duration:.2f}秒)", file=sys.stderr)
                        return None, None
                    
                    # 处理可能的markdown代码块包装
                    if '```markdown' in response_content:
                        # 使用```markdown分割内容
                        parts = response_content.split('```markdown')
                        if len(parts) >= 2:
                            # 取第二部分（```markdown之后的内容）
                            markdown_content = parts[1]
                            # 移除最后的```（如果存在）
                            if '```' in markdown_content:
                                markdown_content = markdown_content.split('```')[0]
                            response_content = markdown_content.strip()
                    
                    # 返回响应内容和token信息
                    token_info = {
                        'prompt_tokens': prompt_tokens,
                        'completion_tokens': completion_tokens,
                        'total_tokens': total_tokens,
                        'cost': cost,
                        'api_duration': api_duration,
                        'model': model  # 添加模型信息
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
        api_duration = end_time - start_time
        print(f"❌ 调用OpenRouter API时出错: {e} (耗时: {api_duration:.2f}秒)", file=sys.stderr)
        return None, None


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


def generate_file_creation_prompt(params, structure_response):
    """Generate prompt for file creation instructions."""
    topic = params['topic']
    mode = params['mode']
    style = params['style']
    
    prompt = f"""根据以下学习内容结构建议，请提供具体的文件创建指令和内容：

学习主题：{topic}
学习模式：{mode}
解释风格：{style}

结构建议：
{structure_response}

请提供：
1. tutorial.md 的完整内容（使用markdown格式）
2. question.md 的完整内容（包含练习题和答案）
3. 如果需要，提供其他相关文件的内容

请确保内容适合{mode}水平的学习者，并采用{style}的解释风格。
每个文件的内容应该用明确的标记分隔，格式如下：

===== tutorial.md =====
[tutorial.md的完整内容]
===== END tutorial.md =====

===== question.md =====
[question.md的完整内容]
===== END question.md =====

如果有其他文件，请使用相同的格式。"""
    
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


def create_learning_files(params, creation_response):
    """Create learning files based on AI response."""
    try:
        output_dir = Path(params['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 解析AI响应中的文件内容
        files_content = parse_file_content(creation_response)
        
        if not files_content:
            print("❌ 无法从AI响应中解析文件内容")
            return False
        
        # 创建文件
        created_files = []
        for filename, content in files_content.items():
            file_path = output_dir / filename
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                created_files.append(str(file_path))
                print(f"✅ 创建文件: {file_path}")
            except Exception as e:
                print(f"❌ 创建文件 {filename} 失败: {e}")
                return False
        
        print(f"\n📁 创建了 {len(created_files)} 个文件:")
        for file_path in created_files:
            print(f"  - {file_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建文件时出错: {e}")
        return False


def parse_file_content(response):
    """Parse file content from AI response."""
    import re
    
    files_content = {}
    
    # 首先尝试匹配标准格式
    pattern = r'===== (.+?) =====\n(.*?)\n===== END \1 ====='
    matches = re.findall(pattern, response, re.DOTALL)
    
    if matches:
        for filename, content in matches:
            files_content[filename] = content.strip()
    else:
        # 如果标准格式不匹配，尝试从响应中提取内容并创建默认文件
        print("⚠️  AI响应格式不符合预期，尝试从响应中提取内容...")
        
        # 清理响应内容
        clean_response = re.sub(r'\x1b\[[0-9;]*[mJHK]', '', response)
        
        # 如果响应包含教程内容，创建默认文件
        if len(clean_response.strip()) > 100:  # 确保有足够的内容
            # 创建 tutorial.md
            tutorial_content = f"""# Python基础教程

## 基于AI生成的学习内容

{clean_response}

## 注意
这是基于AI响应自动生成的内容，建议进一步整理和完善。
"""
            files_content['tutorial.md'] = tutorial_content
            
            # 创建 question.md
            question_content = f"""# Python基础练习题

## 基础练习

### 问题1：什么是Python？
<details>
<summary>点击查看答案</summary>

Python是一种高级编程语言，以其简洁的语法和强大的功能而闻名。

</details>

### 问题2：Python的主要特点是什么？
<details>
<summary>点击查看答案</summary>

Python的主要特点包括：
- 简洁易读的语法
- 强大的标准库
- 跨平台兼容性
- 面向对象编程支持

</details>

### 问题3：如何在Python中创建一个列表？
<details>
<summary>点击查看答案</summary>

```python
my_list = [1, 2, 3, 4, 5]
```

</details>

## 注意
这是基于AI响应自动生成的练习题，建议根据实际教程内容进行调整。
"""
            files_content['question.md'] = question_content
    
    return files_content


def create_files_from_brainstorming(params, brainstorming_response):
    """Create tutorial and question files based on brainstorming response."""
    try:
        output_dir = Path(params['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        topic = params['topic']
        mode = params['mode']
        style = params['style']
        
        # 清理brainstorming响应
        import re
        clean_response = re.sub(r'\x1b\[[0-9;]*[mJHK]', '', brainstorming_response)
        
        # 创建tutorial.md
        tutorial_content = create_tutorial_content(topic, mode, style, clean_response)
        tutorial_path = output_dir / "tutorial.md"
        with open(tutorial_path, 'w', encoding='utf-8') as f:
            f.write(tutorial_content)
        print(f"✅ 创建文件: {tutorial_path}")
        
        # 创建question.md
        question_content = create_question_content(topic, mode, style, clean_response)
        question_path = output_dir / "question.md"
        with open(question_path, 'w', encoding='utf-8') as f:
            f.write(question_content)
        print(f"✅ 创建文件: {question_path}")
        
        print(f"\n📁 创建了 2 个文件:")
        print(f"  - {tutorial_path}")
        print(f"  - {question_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建文件时出错: {e}")
        return False


def create_tutorial_content(topic, mode, style, brainstorming_response):
    """Create tutorial.md content based on brainstorming."""
    content = f"""# {topic} 教程

**学习模式**: {mode}  
**解释风格**: {style}

## 简介

欢迎学习{topic}！这个教程将为您提供系统的学习路径和实践指导。

## 目录

1. [基础概念](#基础概念)
2. [核心知识点](#核心知识点)
3. [实践练习](#实践练习)
4. [进阶应用](#进阶应用)
5. [常见问题](#常见问题)
6. [资源推荐](#资源推荐)

## 基础概念

### 什么是{topic}？

{topic}是一个重要的学习主题。根据AI的建议，学习{topic}对于{mode}水平的学习者来说具有重要意义。

### 核心概念

基于brainstorming的结果，以下是{topic}的核心概念：

"""

    # 尝试从brainstorming响应中提取有用信息
    if "核心概念" in brainstorming_response or "概念" in brainstorming_response:
        content += f"""
**从AI建议中提取的核心概念：**

{brainstorming_response[:1000]}...

*（完整的AI建议请参考原始响应）*

"""

    content += f"""
## 核心知识点

### 必须掌握的知识点

针对{mode}水平的学习者，以下是必须掌握的知识点：

1. **基础理论** - 理解{topic}的基本原理
2. **实践技能** - 掌握基本的操作和应用
3. **问题解决** - 能够分析和解决常见问题

### 学习路径

建议按照以下顺序学习：

1. 基础概念理解
2. 核心技能练习
3. 实际项目应用
4. 高级特性探索

## 实践练习

### 基础练习

1. **入门练习** - 熟悉基本概念
2. **技能练习** - 掌握核心技能
3. **综合练习** - 整合所学知识

### 项目实践

建议完成以下项目来巩固学习：

1. **基础项目** - 应用基本概念
2. **进阶项目** - 结合多个知识点
3. **实战项目** - 解决实际问题

## 进阶应用

### 高级特性

当您掌握了基础知识后，可以探索：

1. **高级技术** - 深入理解原理
2. **最佳实践** - 学习行业标准
3. **创新应用** - 探索新的可能性

## 常见问题

### 学习难点

基于经验，学习者通常在以下方面遇到困难：

1. **概念理解** - 抽象概念的理解
2. **实践应用** - 理论到实践的转换
3. **问题调试** - 遇到问题时的解决方法

### 解决方案

针对这些难点，建议：

1. **多练习** - 通过大量练习加深理解
2. **寻求帮助** - 及时向老师或同学求助
3. **持续学习** - 保持学习的连续性

## 资源推荐

### 学习资源

1. **官方文档** - 最权威的学习资料
2. **在线教程** - 丰富的学习内容
3. **实践项目** - 动手练习的机会

### 工具推荐

根据学习需要，推荐使用以下工具：

1. **开发环境** - 提供良好的学习环境
2. **调试工具** - 帮助解决问题
3. **参考资料** - 随时查阅的手册

## 总结

{topic}是一个值得深入学习的主题。通过系统的学习和大量的实践，您将能够：

1. 掌握核心概念和技能
2. 解决实际问题
3. 为进一步学习打下坚实基础

祝您学习愉快！

---

**注意**: 这份教程基于AI助手的brainstorming结果创建，建议结合其他学习资源一起使用。
"""

    return content


def create_question_content(topic, mode, style, brainstorming_response):
    """Create question.md content based on brainstorming."""
    content = f"""# {topic} 练习题

**学习模式**: {mode}  
**解释风格**: {style}

## 基础知识题

### 问题1：什么是{topic}？
<details>
<summary>点击查看答案</summary>

{topic}是一个重要的学习领域，涉及多个核心概念和实践技能。对于{mode}水平的学习者来说，理解{topic}的基本原理和应用是必要的。

</details>

### 问题2：学习{topic}需要什么前置知识？
<details>
<summary>点击查看答案</summary>

学习{topic}通常需要：
- 基础的理论知识
- 一定的逻辑思维能力
- 动手实践的意愿
- 持续学习的态度

</details>

### 问题3：{topic}的核心概念有哪些？
<details>
<summary>点击查看答案</summary>

基于AI的brainstorming建议，{topic}的核心概念包括多个方面。具体内容请参考tutorial.md中的详细介绍。

</details>

## 理解题

### 问题4：请解释{topic}的基本原理
<details>
<summary>点击查看答案</summary>

{topic}的基本原理涉及多个层面的理解。建议从基础概念开始，逐步深入理解其工作机制和应用场景。

</details>

### 问题5：{topic}有哪些实际应用？
<details>
<summary>点击查看答案</summary>

{topic}在实际中有广泛的应用，包括：
- 理论研究
- 实际项目
- 问题解决
- 创新应用

</details>

## 实践题

### 问题6：设计一个{topic}的入门练习
<details>
<summary>点击查看答案</summary>

建议的入门练习应该：
1. 从最基础的概念开始
2. 提供明确的步骤指导
3. 包含实践操作
4. 有明确的预期结果

</details>

### 问题7：如何解决{topic}学习中的常见问题？
<details>
<summary>点击查看答案</summary>

解决学习问题的方法：
1. 仔细阅读教程和文档
2. 寻求老师或同学的帮助
3. 在线搜索相关资源
4. 通过实践验证理解

</details>

## 应用题

### 问题8：设计一个{topic}的实际项目
<details>
<summary>点击查看答案</summary>

实际项目应该：
- 有明确的目标
- 体现{topic}的核心概念
- 适合{mode}水平的学习者
- 提供学习和实践的机会

</details>

### 问题9：如何评估{topic}的学习效果？
<details>
<summary>点击查看答案</summary>

评估学习效果可以通过：
1. 理论知识测试
2. 实践技能展示
3. 项目完成情况
4. 问题解决能力

</details>

## 思考题

### 问题10：{topic}的未来发展趋势是什么？
<details>
<summary>点击查看答案</summary>

{topic}的发展趋势可能包括：
- 技术进步带来的新机会
- 应用领域的扩展
- 学习方法的改进
- 工具和资源的丰富

这需要学习者保持持续学习和关注行业动态。

</details>

---

**答题说明**:
- 每个问题都对应tutorial.md中的相关知识点
- 使用HTML的`<details>`和`<summary>`标签实现答案的显示/隐藏
- 建议先独立思考再查看答案
- 可以结合实践来验证理解

**学习建议**:
1. 按顺序完成练习题
2. 每完成一组题目后回顾相关教程内容
3. 遇到不理解的地方及时查阅资料
4. 通过实践项目巩固所学知识

---

**注意**: 这份练习题基于AI助手的brainstorming结果创建，建议结合实际学习进度调整难度和内容。
"""

    return content


def call_openrouter_with_retry(prompt, model, max_tokens, step_name, max_retries=3, params=None):
    """Call OpenRouter API with retry mechanism and model switching."""
    current_model = model
    
    for attempt in range(max_retries):
        response, token_info = call_openrouter_for_structure(prompt, current_model, max_tokens, attempt)
        
        # 检查是否成功（不是None且不是错误）
        if response is not None and not (isinstance(response, str) and response.startswith("ERROR:")):
            return response, token_info, current_model
        
        print(f"❌ {step_name}失败 (第{attempt + 1}次尝试)", file=sys.stderr)
        
        # 检查是否是429错误（速率限制）
        if response and isinstance(response, str) and ("429" in response or "rate-limited" in response):
            print("⚠️  检测到速率限制错误，立即切换模型", file=sys.stderr)
            # 立即切换到下一个模型
            if attempt == 0:  # 只在第一次失败时切换
                # 获取所有可用模型
                all_models = get_openrouter_models()
                if not all_models:
                    print("❌ 无法获取模型列表", file=sys.stderr)
                    break
                
                # 移除当前失败的模型
                available_models = [m for m in all_models if m != current_model]
                
                if not available_models:
                    print("❌ 没有其他可用模型", file=sys.stderr)
                    break
                
                # 分类模型
                free_models = [m for m in available_models if ":free" in m]
                paid_models = [m for m in available_models if ":free" not in m]
                
                # 如果使用了--not-default，让用户选择
                if params and not params.get('not_default', False):
                    # 默认模式：如果当前是免费模型，尝试下一个免费模型
                    if current_model and ":free" in current_model and free_models:
                        current_model = free_models[0]
                        print(f"🔄 自动切换到下一个免费模型: {current_model}", file=sys.stderr)
                        continue
                    elif paid_models:
                        current_model = paid_models[0]
                        print(f"🔄 自动切换到付费模型: {current_model}", file=sys.stderr)
                        continue
                else:
                    # 交互模式：显示所有可用模型让用户选择
                    print(f"\n⚠️  模型 '{current_model}' 调用失败", file=sys.stderr)
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
                                current_model = all_available[choice_idx]
                                print(f"✅ 切换到模型: {current_model}", file=sys.stderr)
                                # 重新尝试一次
                                response, token_info = call_openrouter_for_structure(prompt, current_model, max_tokens, 0)
                                if response is not None and not (isinstance(response, str) and response.startswith("ERROR:")):
                                    return response, token_info, current_model
                    except (KeyboardInterrupt, EOFError):
                        print("\n用户取消操作", file=sys.stderr)
                        break
            
            # 如果到这里说明429错误处理失败
            break
        
        # 对于其他错误，在最后一次重试后才进行模型切换
        if attempt == max_retries - 1:
            # 获取所有可用模型
            all_models = get_openrouter_models()
            if not all_models:
                print("❌ 无法获取模型列表", file=sys.stderr)
                break
            
            # 移除当前失败的模型
            available_models = [m for m in all_models if m != current_model]
            
            if not available_models:
                print("❌ 没有其他可用模型", file=sys.stderr)
                break
            
            # 分类模型
            free_models = [m for m in available_models if ":free" in m]
            paid_models = [m for m in available_models if ":free" not in m]
            
            # 如果使用了--not-default，让用户选择
            if params and not params.get('not_default', False):
                # 默认模式：如果当前是免费模型，尝试下一个免费模型
                if current_model and ":free" in current_model and free_models:
                    current_model = free_models[0]
                    print(f"🔄 自动切换到下一个免费模型: {current_model}", file=sys.stderr)
                    # 重新尝试一次
                    response, token_info = call_openrouter_for_structure(prompt, current_model, max_tokens, 0)
                    if response is not None and not (isinstance(response, str) and response.startswith("ERROR:")):
                        return response, token_info, current_model
                elif paid_models:
                    current_model = paid_models[0]
                    print(f"🔄 自动切换到付费模型: {current_model}", file=sys.stderr)
                    # 重新尝试一次
                    response, token_info = call_openrouter_for_structure(prompt, current_model, max_tokens, 0)
                    if response is not None and not (isinstance(response, str) and response.startswith("ERROR:")):
                        return response, token_info, current_model
            else:
                # 交互模式：显示所有可用模型让用户选择
                print(f"\n⚠️  模型 '{current_model}' 调用失败", file=sys.stderr)
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
                            current_model = all_available[choice_idx]
                            print(f"✅ 切换到模型: {current_model}", file=sys.stderr)
                            # 重新尝试一次
                            response, token_info = call_openrouter_for_structure(prompt, current_model, max_tokens, 0)
                            if response is not None and not (isinstance(response, str) and response.startswith("ERROR:")):
                                return response, token_info, current_model
                except (KeyboardInterrupt, EOFError):
                    print("\n用户取消操作", file=sys.stderr)
                    break
            
            # 如果到这里说明模型切换也失败了
            break
    
    return None, None, current_model


def get_non_free_models():
    """Get list of non-free models from OpenRouter."""
    try:
        models = get_openrouter_models()
        return [model for model in models if ":free" not in model]
    except:
        return []


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
            # Auto-proceed in default mode or with free models
            should_auto_proceed = False
            
            if not params.get('not_default', False):
                # Default mode - auto proceed with automatic creation
                should_auto_proceed = True
                print("🚀 默认模式：自动选择创建模式...")
                # Don't set no_auto_create, proceed with full auto creation
            else:
                # Check if using free model
                if selected_model and max_tokens:
                    models, model_details = get_openrouter_models()
                    if models:
                        details = model_details.get(selected_model, {})
                        is_free_model = details.get('input_cost_per_1m', 0) == 0
                        if is_free_model:
                            should_auto_proceed = True
                            print("🚀 免费模型：自动选择创建模式...")
            
            if not should_auto_proceed:
                # Ask user about creation mode
                print("\n🎯 选择创建模式:")
                creation_choice = interactive_select(
                    "创建模式:", 
                    ["自动创建 (AI生成3次)", "手动创建 (AI生成1次，你来创建文件)"]
                )
                if creation_choice is None:
                    return None
                
                if creation_choice == 1:  # Manual creation
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
        import json
        import re
        
        # Try to find the search results file
        search_data_dir = script_dir / "SEARCH_PAPER_DATA" / "results"
        if search_data_dir.exists():
            # Get the most recent search results file
            result_files = list(search_data_dir.glob("search_results_*.json"))
            if result_files:
                latest_file = max(result_files, key=lambda x: x.stat().st_mtime)
                
                with open(latest_file, 'r', encoding='utf-8') as f:
                    search_results = json.load(f)
                
                # Show papers to user
                if search_results and len(search_results) > 0:
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
                                return None, None
                            
                            choice_idx = int(choice) - 1
                            if 0 <= choice_idx < min(5, len(search_results)):
                                selected_paper = search_results[choice_idx]
                                break
                            else:
                                print(f"请输入 1-{min(5, len(search_results))} 之间的数字")
                        except ValueError:
                            print("请输入有效的数字")
                    
                    # Try to download the paper
                    pdf_url = selected_paper.get('pdf_url')
                    if pdf_url:
                        print(f"\n📥 尝试下载论文: {selected_paper.get('title', 'Unknown')}")
                        return download_paper(pdf_url, selected_paper.get('title', 'paper'))
                    else:
                        print("❌ 未找到PDF下载链接")
                        return None, None
                else:
                    print("❌ 未找到相关论文")
                    return None, None
            else:
                print("❌ 未找到搜索结果文件")
                return None, None
        else:
            print("❌ 搜索结果目录不存在")
            return None, None
            
    except Exception as e:
        print(f"❌ 搜索过程出错: {e}")
        return None, None


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
            
            # Try alternative download methods if available
            # This could include trying different PDF URLs from the paper metadata
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
            return None, None
            
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
            return None, None
    
    if not paper_content:
        print("❌ 无法获取论文内容")
        return None, None
    
    # Count tokens
    token_count = count_tokens(paper_content)
    print(f"\n📊 论文内容统计:")
    print(f"   字符数: {len(paper_content):,}")
    print(f"   预估token数: {token_count:,}")
    
    return paper_content, paper_path, token_count


if __name__ == "__main__":
    sys.exit(main()) 