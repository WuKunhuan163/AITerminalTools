#!/usr/bin/env python3
"""
OVERLEAF.py - LaTeX文件编译工具
支持GUI文件选择和JSON返回值，能够检测RUN环境
"""

import os
import sys
import json
import subprocess
import tempfile
import hashlib
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def is_run_environment(command_identifier=None):
    """Check if running in RUN environment by checking environment variables"""
    if command_identifier:
        return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
    return False

def select_tex_file():
    """使用GUI选择LaTeX文件"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        
        # 设置文件选择对话框
        file_path = filedialog.askopenfilename(
            title='选择LaTeX文件',
            initialdir=os.getcwd(),
            filetypes=[('LaTeX files', '*.tex'), ('All files', '*.*')]
        )
        
        if file_path:
            return file_path
        else:
            return None
    except ImportError:
        print("Error: tkinter is not available. Please provide a file path as argument.")
        return None

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
        # 确保输出目录存在
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing to JSON output file: {e}")
        return False

def compile_latex(tex_file, command_identifier=None, output_dir=None):
    """编译LaTeX文件"""
    # 简化路径处理：使用绝对路径
    tex_path = Path(tex_file).resolve()
    
    if not tex_path.exists():
        error_data = {
            "success": False, 
            "error": f"File not found: {tex_file}", 
            "file": str(tex_path)
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(f"Error: File not found: {tex_file}")
        return 1
    
    filename = tex_path.stem
    
    # 在RUN环境下，使用/tmp目录作为工作目录
    if is_run_environment(command_identifier):
        # 创建临时工作目录
        work_dir = Path(tempfile.mkdtemp(prefix=f"overleaf_{filename}_"))
        # 复制tex文件到临时目录
        import shutil
        temp_tex = work_dir / f"{filename}.tex"
        shutil.copy2(tex_path, temp_tex)
        directory = work_dir
    else:
        directory = tex_path.parent
    
    # 创建临时日志文件
    log_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.log', delete=False)
    log_file_path = log_file.name
    log_file.close()
    
    try:
        # 切换到文件目录
        original_cwd = os.getcwd()
        os.chdir(directory)
        
        # 执行编译
        cmd = [
            'latexmk', '-pdf', 
            f'-pdflatex=pdflatex -interaction=nonstopmode',
            f'{filename}.tex'
        ]
        
        with open(log_file_path, 'w') as log_f:
            result = subprocess.run(
                cmd,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                text=True
            )
        
        # 读取日志内容
        with open(log_file_path, 'r') as log_f:
            log_content = log_f.read()
        
        # 恢复原工作目录
        os.chdir(original_cwd)
        
        if result.returncode == 0:
            # 编译成功，清理临时文件
            cleanup_cmd = ['latexmk', '-c', '-quiet', f'{filename}.tex']
            subprocess.run(cleanup_cmd, cwd=directory, capture_output=True)
            
            # 删除 .fdb_latexmk 文件
            fdb_file = directory / f"{filename}.fdb_latexmk"
            if fdb_file.exists():
                fdb_file.unlink()
            
            # 检查PDF是否生成
            pdf_file = directory / f"{filename}.pdf"
            if pdf_file.exists():
                final_pdf_path = pdf_file
                
                # 如果指定了output_dir，移动PDF文件
                if output_dir:
                    output_path = Path(output_dir)
                    output_path.mkdir(parents=True, exist_ok=True)
                    final_pdf_path = output_path / f"{filename}.pdf"
                    
                    try:
                        import shutil
                        shutil.move(str(pdf_file), str(final_pdf_path))
                    except Exception as e:
                        error_data = {
                            "success": False, 
                            "error": f"Failed to move PDF to output directory: {str(e)}", 
                            "file": str(tex_path)
                        }
                        
                        if is_run_environment(command_identifier):
                            write_to_json_output(error_data, command_identifier)
                        else:
                            print(f"Error: Failed to move PDF to output directory: {e}")
                        return 1
                
                success_data = {
                    "success": True, 
                    "message": "Compilation successful", 
                    "file": str(tex_path), 
                    "output": str(final_pdf_path)
                }
                
                if is_run_environment(command_identifier):
                    write_to_json_output(success_data, command_identifier)
                else:
                    print("LaTeX compilation successful!")
                    print(f"Input file: {tex_path}")
                    print(f"Output PDF: {final_pdf_path}")
                    if output_dir:
                        print(f"PDF moved to: {output_dir}")
                    print("\n=== Compilation Log ===")
                    print(log_content)
                return 0
            else:
                error_data = {
                    "success": False, 
                    "error": "PDF not generated", 
                    "file": str(tex_path)
                }
                
                if is_run_environment(command_identifier):
                    write_to_json_output(error_data, command_identifier)
                else:
                    print("Error: PDF not generated")
                    print(f"Input file: {tex_path}")
                    print("\n=== Compilation Log ===")
                    print(log_content)
                return 1
        else:
            # 编译失败
            # 获取最后20行的错误信息
            log_lines = log_content.split('\n')
            error_summary = '\n'.join(log_lines[-20:])
            
            error_data = {
                "success": False, 
                "error": f"Compilation failed: {error_summary}", 
                "file": str(tex_path)
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(error_data, command_identifier)
            else:
                print("LaTeX compilation failed!")
                print(f"Input file: {tex_path}")
                print(f"Exit code: {result.returncode}")
                print("\n=== Compilation Log ===")
                print(log_content)
            return result.returncode
    
    except Exception as e:
        error_data = {
            "success": False, 
            "error": f"Compilation error: {str(e)}", 
            "file": str(tex_path)
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(f"Error during compilation: {e}")
        return 1
    
    finally:
        # 清理临时日志文件
        try:
            os.unlink(log_file_path)
        except:
            pass
        
        # 在RUN环境下，清理临时工作目录
        if is_run_environment(command_identifier) and 'work_dir' in locals():
            try:
                import shutil
                shutil.rmtree(work_dir)
            except:
                pass

def resolve_tex_path(tex_file):
    """Resolve LaTeX file path (for test compatibility)"""
    return Path(tex_file).resolve()

def create_json_output(success=True, message="", output_file="", log_content=""):
    """Create JSON output format (for test compatibility)"""
    import datetime
    return {
        'success': success,
        'message': message,
        'output_file': output_file,
        'log_content': log_content,
        'timestamp': datetime.datetime.now().isoformat()
    }

def main():
    """主函数"""
    # 获取执行上下文和command_identifier
    args = sys.argv[1:]
    command_identifier = None
    
    # 检查是否被RUN调用（第一个参数是command_identifier）
    if args and is_run_environment(args[0]):
        command_identifier = args[0]
        args = args[1:]  # 移除command_identifier，保留实际参数
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='OVERLEAF - LaTeX文件编译工具')
    parser.add_argument('tex_file', nargs='?', help='LaTeX文件路径')
    parser.add_argument('--output-dir', help='输出目录，编译完成后将PDF移动到此目录')
    
    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        # argparse的--help会导致SystemExit，我们需要正常处理
        return 0
    
    if not parsed_args.tex_file:
        # 没有文件参数时，打开文件选择器
        selected_file = select_tex_file()
        if selected_file:
            return compile_latex(selected_file, command_identifier, parsed_args.output_dir)
        else:
            error_data = {
                "success": False, 
                "error": "No file selected", 
                "file": None
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(error_data, command_identifier)
            else:
                print("Error: No file selected")
            return 1
    else:
        # 有参数时，直接编译指定文件
        return compile_latex(parsed_args.tex_file, command_identifier, parsed_args.output_dir)

if __name__ == "__main__":
    sys.exit(main()) 