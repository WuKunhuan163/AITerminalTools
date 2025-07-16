#!/usr/bin/env python3
"""
FILE_SELECT.py - File Selection Tool
Opens a tkinter file selection dialog to let users specify certain types of files
Python version with RUN environment detection
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from typing import Optional, List, Tuple

def generate_run_identifier():
    """生成一个基于时间和随机数的唯一标识符"""
    import time
    import random
    
    timestamp = str(time.time())
    random_num = str(random.randint(100000, 999999))
    combined = f"{timestamp}_{random_num}_{os.getpid()}"
    
    return hashlib.sha256(combined.encode()).hexdigest()[:16]

def get_run_context():
    """获取 RUN 执行上下文信息"""
    run_identifier = os.environ.get('RUN_IDENTIFIER')
    output_file = os.environ.get('RUN_OUTPUT_FILE')
    
    if run_identifier:
        if not output_file:
            output_file = f"RUN_output/run_{run_identifier}.json"
        return {
            'in_run_context': True,
            'identifier': run_identifier,
            'output_file': output_file
        }
    elif output_file:
        try:
            filename = Path(output_file).stem
            if filename.startswith('run_'):
                identifier = filename[4:]
            else:
                identifier = generate_run_identifier()
        except:
            identifier = generate_run_identifier()
        
        return {
            'in_run_context': True,
            'identifier': identifier,
            'output_file': output_file
        }
    else:
        return {
            'in_run_context': False,
            'identifier': None,
            'output_file': None
        }

def write_to_json_output(data, run_context):
    """将结果写入到指定的 JSON 输出文件中"""
    if not run_context['in_run_context'] or not run_context['output_file']:
        return False
    
    try:
        # 确保输出目录存在
        output_path = Path(run_context['output_file'])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 添加RUN相关信息
        data['run_identifier'] = run_context['identifier']
        
        with open(run_context['output_file'], 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing to JSON output file: {e}")
        return False

def parse_file_types(file_types_str: str) -> List[Tuple[str, str]]:
    """解析文件类型字符串，返回文件类型列表"""
    if not file_types_str:
        return [('All files', '*.*')]
    
    file_types = []
    
    # 预定义的文件类型
    predefined_types = {
        'pdf': ('PDF files', '*.pdf'),
        'txt': ('Text files', '*.txt'),
        'doc': ('Word documents', '*.doc *.docx'),
        'docx': ('Word documents', '*.docx'),
        'image': ('Image files', '*.png *.jpg *.jpeg *.gif *.bmp *.tiff'),
        'png': ('PNG images', '*.png'),
        'jpg': ('JPEG images', '*.jpg *.jpeg'),
        'jpeg': ('JPEG images', '*.jpeg'),
        'gif': ('GIF images', '*.gif'),
        'tex': ('LaTeX files', '*.tex'),
        'py': ('Python files', '*.py'),
        'js': ('JavaScript files', '*.js'),
        'html': ('HTML files', '*.html *.htm'),
        'css': ('CSS files', '*.css'),
        'json': ('JSON files', '*.json'),
        'xml': ('XML files', '*.xml'),
        'csv': ('CSV files', '*.csv'),
        'xlsx': ('Excel files', '*.xlsx *.xls'),
        'ppt': ('PowerPoint files', '*.ppt *.pptx'),
        'zip': ('Archive files', '*.zip *.rar *.7z *.tar *.gz'),
        'mp3': ('Audio files', '*.mp3 *.wav *.flac *.aac'),
        'mp4': ('Video files', '*.mp4 *.avi *.mov *.mkv'),
        'all': ('All files', '*.*')
    }
    
    # 解析输入的文件类型
    types_list = [t.strip().lower() for t in file_types_str.split(',')]
    
    for file_type in types_list:
        if file_type in predefined_types:
            file_types.append(predefined_types[file_type])
        elif file_type.startswith('*.'):
            # 直接的文件扩展名模式
            file_types.append((f'{file_type.upper()} files', file_type))
        else:
            # 作为扩展名处理
            file_types.append((f'{file_type.upper()} files', f'*.{file_type}'))
    
    # 如果没有找到任何有效类型，返回所有文件
    if not file_types:
        file_types = [('All files', '*.*')]
    
    # 总是在最后添加"所有文件"选项
    if ('All files', '*.*') not in file_types:
        file_types.append(('All files', '*.*'))
    
    return file_types

def select_file(file_types: List[Tuple[str, str]], title: str = "Select File", 
                initial_dir: str = None, multiple: bool = False) -> Optional[str]:
    """使用GUI选择文件"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        
        # 设置初始目录
        if initial_dir is None:
            initial_dir = os.getcwd()
        
        # 设置文件选择对话框
        if multiple:
            file_paths = filedialog.askopenfilenames(
                title=title,
                initialdir=initial_dir,
                filetypes=file_types
            )
            root.destroy()
            return list(file_paths) if file_paths else None
        else:
            file_path = filedialog.askopenfilename(
                title=title,
                initialdir=initial_dir,
                filetypes=file_types
            )
            root.destroy()
            return file_path if file_path else None
            
    except ImportError:
        return None
    except Exception as e:
        print(f"Error opening file dialog: {e}")
        return None

def show_help():
    """显示帮助信息"""
    help_text = """FILE_SELECT - File Selection Tool

Usage: FILE_SELECT [options]

Options:
  --types <types>     Comma-separated list of file types (default: all)
  --title <title>     Dialog title (default: "Select File")
  --dir <directory>   Initial directory (default: current directory)
  --multiple          Allow multiple file selection
  --help, -h          Show this help message

File Types:
  Predefined types: pdf, txt, doc, docx, image, png, jpg, jpeg, gif, tex, py, js, 
                   html, css, json, xml, csv, xlsx, ppt, zip, mp3, mp4, all
  
  Custom extensions: Use format like "*.ext" or just "ext"

Examples:
  FILE_SELECT                                    # Select any file
  FILE_SELECT --types pdf                        # Select PDF files only
  FILE_SELECT --types pdf,txt,doc               # Select PDF, text, or Word files
  FILE_SELECT --types image --title "Select Image"  # Select image files with custom title
  FILE_SELECT --types "*.log" --dir /var/log    # Select log files from specific directory
  FILE_SELECT --multiple --types pdf            # Select multiple PDF files
  FILE_SELECT --help                            # Show help

This tool will:
1. Open a file selection dialog with the specified file types
2. Allow user to browse and select file(s)
3. Return the selected file path(s) or null if cancelled
4. Support both single and multiple file selection modes"""
    
    print(help_text)

def main():
    """主函数"""
    # 获取执行上下文
    run_context = get_run_context()
    
    # 解析命令行参数
    args = sys.argv[1:]
    
    # 默认参数
    file_types_str = "all"
    title = "Select File"
    initial_dir = None
    multiple = False
    
    # 解析参数
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg in ['--help', '-h']:
            if run_context['in_run_context']:
                help_data = {
                    "success": True,
                    "message": "Help information",
                    "help": "FILE_SELECT - File Selection Tool"
                }
                write_to_json_output(help_data, run_context)
            else:
                show_help()
            return 0
            
        elif arg == '--types':
            if i + 1 < len(args):
                file_types_str = args[i + 1]
                i += 2
            else:
                error_msg = "Error: --types requires a value"
                if run_context['in_run_context']:
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, run_context)
                else:
                    print(f"❌ {error_msg}")
                return 1
                
        elif arg == '--title':
            if i + 1 < len(args):
                title = args[i + 1]
                i += 2
            else:
                error_msg = "Error: --title requires a value"
                if run_context['in_run_context']:
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, run_context)
                else:
                    print(f"❌ {error_msg}")
                return 1
                
        elif arg == '--dir':
            if i + 1 < len(args):
                initial_dir = args[i + 1]
                i += 2
            else:
                error_msg = "Error: --dir requires a value"
                if run_context['in_run_context']:
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, run_context)
                else:
                    print(f"❌ {error_msg}")
                return 1
                
        elif arg == '--multiple':
            multiple = True
            i += 1
            
        else:
            error_msg = f"Error: Unknown argument '{arg}'"
            if run_context['in_run_context']:
                error_data = {"success": False, "error": error_msg}
                write_to_json_output(error_data, run_context)
            else:
                print(f"❌ {error_msg}")
                print("Use --help for usage information")
            return 1
    
    # 验证初始目录
    if initial_dir and not os.path.exists(initial_dir):
        error_msg = f"Error: Directory '{initial_dir}' does not exist"
        if run_context['in_run_context']:
            error_data = {"success": False, "error": error_msg}
            write_to_json_output(error_data, run_context)
        else:
            print(f"❌ {error_msg}")
        return 1
    
    # 解析文件类型
    file_types = parse_file_types(file_types_str)
    
    # 选择文件
    try:
        selected = select_file(file_types, title, initial_dir, multiple)
        
        if selected is None:
            # 用户取消了选择
            if run_context['in_run_context']:
                result_data = {
                    "success": False,
                    "message": "File selection cancelled by user",
                    "selected_files": None
                }
                write_to_json_output(result_data, run_context)
            else:
                print("❌ File selection cancelled")
            return 1
        
        # 处理选择结果
        if multiple:
            if not selected:
                # 没有选择任何文件
                if run_context['in_run_context']:
                    result_data = {
                        "success": False,
                        "message": "No files selected",
                        "selected_files": []
                    }
                    write_to_json_output(result_data, run_context)
                else:
                    print("❌ No files selected")
                return 1
            else:
                # 选择了多个文件
                if run_context['in_run_context']:
                    result_data = {
                        "success": True,
                        "message": f"Selected {len(selected)} file(s)",
                        "selected_files": selected,
                        "file_count": len(selected)
                    }
                    write_to_json_output(result_data, run_context)
                else:
                    print(f"✅ Selected {len(selected)} file(s):")
                    for i, file_path in enumerate(selected, 1):
                        print(f"  {i}. {file_path}")
        else:
            # 单个文件选择
            if run_context['in_run_context']:
                result_data = {
                    "success": True,
                    "message": "File selected successfully",
                    "selected_file": selected,
                    "file_name": os.path.basename(selected),
                    "file_size": os.path.getsize(selected) if os.path.exists(selected) else 0
                }
                write_to_json_output(result_data, run_context)
            else:
                print(f"✅ Selected file: {selected}")
                if os.path.exists(selected):
                    file_size = os.path.getsize(selected)
                    print(f"   File size: {file_size} bytes")
        
        return 0
        
    except Exception as e:
        error_msg = f"Error during file selection: {str(e)}"
        if run_context['in_run_context']:
            error_data = {"success": False, "error": error_msg}
            write_to_json_output(error_data, run_context)
        else:
            print(f"❌ {error_msg}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 