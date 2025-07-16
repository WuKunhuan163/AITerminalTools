#!/usr/bin/env python3
"""
EXTRACT_PDF.py - Enhanced PDF extraction using MinerU without image API analysis
Python version with RUN environment detection
"""

import os
import sys
import json
import subprocess
import argparse
import hashlib
from pathlib import Path

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

def validate_pdf_extract_cli():
    """验证pdf_extract_cli.py是否存在"""
    pdf_extract_cli = "/Users/wukunhuan/.local/project/pdf_extractor/pdf_extract_cli.py"
    
    if not Path(pdf_extract_cli).exists():
        return False, pdf_extract_cli
    
    return True, pdf_extract_cli

def extract_pdf(pdf_file, page_spec=None, output_dir=None, use_mineru=True, no_image_api=True, run_context=None):
    """执行PDF提取"""
    
    # 验证PDF文件
    pdf_path = Path(pdf_file).resolve()
    if not pdf_path.exists():
        error_data = {
            "success": False,
            "error": f"PDF file not found: {pdf_file}",
            "file": str(pdf_path)
        }
        
        if run_context['in_run_context']:
            write_to_json_output(error_data, run_context)
        else:
            print(f"❌ Error: PDF file not found: {pdf_file}")
        return 1
    
    # 验证pdf_extract_cli.py
    cli_exists, cli_path = validate_pdf_extract_cli()
    if not cli_exists:
        error_data = {
            "success": False,
            "error": f"pdf_extract_cli.py not found at {cli_path}",
            "file": str(pdf_path)
        }
        
        if run_context['in_run_context']:
            write_to_json_output(error_data, run_context)
        else:
            print(f"❌ Error: pdf_extract_cli.py not found at {cli_path}")
        return 1
    
    # 构建命令
    cmd = ["/usr/bin/python3", cli_path, str(pdf_path)]
    
    # 添加选项
    if use_mineru:
        cmd.append("--use-mineru")
    
    if no_image_api:
        cmd.append("--no-image-api")
    
    if page_spec:
        cmd.extend(["--page", page_spec])
    
    if output_dir:
        cmd.extend(["--output", output_dir])
    
    # 显示执行的命令
    cmd_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in cmd)
    
    if not run_context['in_run_context']:
        print(f"🚀 Executing: {cmd_str}")
    
    try:
        # 执行命令
        if run_context['in_run_context']:
            # 在RUN环境中，捕获输出
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                success_data = {
                    "success": True,
                    "message": "PDF extraction completed successfully",
                    "file": str(pdf_path),
                    "command": cmd_str,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
                write_to_json_output(success_data, run_context)
                return 0
            else:
                error_data = {
                    "success": False,
                    "error": "PDF extraction failed",
                    "file": str(pdf_path),
                    "command": cmd_str,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
                write_to_json_output(error_data, run_context)
                return result.returncode
        else:
            # 直接调用时，让输出直接显示到终端
            result = subprocess.run(cmd)
            
            if result.returncode == 0:
                print("✅ PDF extraction completed successfully")
                return 0
            else:
                print("❌ PDF extraction failed")
                return result.returncode
    
    except Exception as e:
        error_data = {
            "success": False,
            "error": f"Execution error: {str(e)}",
            "file": str(pdf_path),
            "command": cmd_str
        }
        
        if run_context['in_run_context']:
            write_to_json_output(error_data, run_context)
        else:
            print(f"❌ Error during execution: {e}")
        return 1

def show_help():
    """显示帮助信息"""
    help_text = """EXTRACT_PDF - Enhanced PDF extraction using MinerU

Usage: EXTRACT_PDF <pdf_file> [options]

Options:
  --page <spec>        Extract specific page(s) (e.g., 3, 1-5, 1,3,5)
  --output <dir>       Output directory (default: same as PDF)
  --use-original       Use original extractor instead of MinerU
  --with-image-api     Enable image API analysis (disabled by default)
  --help, -h           Show this help message

Examples:
  EXTRACT_PDF document.pdf --page 3
  EXTRACT_PDF paper.pdf --page 1-5 --output /path/to/output"""
    
    print(help_text)

def select_pdf_file():
    """使用GUI选择PDF文件"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        
        # 设置文件选择对话框
        file_path = filedialog.askopenfilename(
            title='选择PDF文件',
            initialdir=os.getcwd(),
            filetypes=[('PDF files', '*.pdf'), ('All files', '*.*')]
        )
        
        if file_path:
            return file_path
        else:
            return None
    except ImportError:
        print("Error: tkinter is not available. Please provide a PDF file path as argument.")
        return None

def main():
    """主函数"""
    # 获取执行上下文
    run_context = get_run_context()
    
    # 解析命令行参数
    if len(sys.argv) == 1:
        # 没有参数时，打开文件选择器
        selected_file = select_pdf_file()
        if selected_file:
            # 使用选中的文件，默认参数
            return extract_pdf(selected_file, None, None, True, True, run_context)
        else:
            if run_context['in_run_context']:
                error_data = {
                    "success": False,
                    "error": "No PDF file selected",
                    "file": None
                }
                write_to_json_output(error_data, run_context)
            else:
                print("❌ Error: No PDF file selected")
            return 1
    
    # 手动解析参数以保持与原脚本的兼容性
    args = sys.argv[1:]
    pdf_file = None
    page_spec = None
    output_dir = None
    use_mineru = True
    no_image_api = True
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg in ['--help', '-h']:
            if run_context['in_run_context']:
                help_data = {
                    "success": True,
                    "message": "Help information",
                    "help": show_help.__doc__
                }
                write_to_json_output(help_data, run_context)
            else:
                show_help()
            return 0
        elif arg == '--page':
            if i + 1 < len(args):
                page_spec = args[i + 1]
                i += 2
            else:
                error_msg = "❌ Error: --page requires a value"
                if run_context['in_run_context']:
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, run_context)
                else:
                    print(error_msg)
                return 1
        elif arg == '--output':
            if i + 1 < len(args):
                output_dir = args[i + 1]
                i += 2
            else:
                error_msg = "❌ Error: --output requires a value"
                if run_context['in_run_context']:
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, run_context)
                else:
                    print(error_msg)
                return 1
        elif arg == '--use-original':
            use_mineru = False
            i += 1
        elif arg == '--with-image-api':
            no_image_api = False
            i += 1
        elif arg.startswith('-'):
            error_msg = f"❌ Unknown option: {arg}"
            if run_context['in_run_context']:
                error_data = {"success": False, "error": error_msg}
                write_to_json_output(error_data, run_context)
            else:
                print(error_msg)
                print("Use --help for usage information")
            return 1
        else:
            if pdf_file is None:
                pdf_file = arg
            else:
                error_msg = "❌ Multiple PDF files specified. Only one file is supported."
                if run_context['in_run_context']:
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, run_context)
                else:
                    print(error_msg)
                return 1
            i += 1
    
    # 检查是否提供了PDF文件
    if pdf_file is None:
        error_msg = "❌ Error: No PDF file specified"
        if run_context['in_run_context']:
            error_data = {"success": False, "error": error_msg}
            write_to_json_output(error_data, run_context)
        else:
            print(error_msg)
            print("Use --help for usage information")
        return 1
    
    # 执行PDF提取
    return extract_pdf(pdf_file, page_spec, output_dir, use_mineru, no_image_api, run_context)

if __name__ == "__main__":
    sys.exit(main()) 