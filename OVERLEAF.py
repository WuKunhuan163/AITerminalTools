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

def compile_latex(tex_file, run_context):
    """编译LaTeX文件"""
    tex_path = Path(tex_file).resolve()
    
    if not tex_path.exists():
        error_data = {
            "success": False, 
            "error": f"File not found: {tex_file}", 
            "file": str(tex_path)
        }
        
        if run_context['in_run_context']:
            write_to_json_output(error_data, run_context)
        else:
            print(f"Error: File not found: {tex_file}")
        return 1
    
    filename = tex_path.stem
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
                success_data = {
                    "success": True, 
                    "message": "Compilation successful", 
                    "file": str(tex_path), 
                    "output": str(pdf_file)
                }
                
                if run_context['in_run_context']:
                    write_to_json_output(success_data, run_context)
                else:
                    print("LaTeX compilation successful!")
                    print(f"Input file: {tex_path}")
                    print(f"Output PDF: {pdf_file}")
                    print("\n=== Compilation Log ===")
                    print(log_content)
                return 0
            else:
                error_data = {
                    "success": False, 
                    "error": "PDF not generated", 
                    "file": str(tex_path)
                }
                
                if run_context['in_run_context']:
                    write_to_json_output(error_data, run_context)
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
            
            if run_context['in_run_context']:
                write_to_json_output(error_data, run_context)
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
        
        if run_context['in_run_context']:
            write_to_json_output(error_data, run_context)
        else:
            print(f"Error during compilation: {e}")
        return 1
    
    finally:
        # 清理临时日志文件
        try:
            os.unlink(log_file_path)
        except:
            pass

def main():
    """主函数"""
    # 获取执行上下文
    run_context = get_run_context()
    
    if len(sys.argv) == 1:
        # 没有参数时，打开文件选择器
        selected_file = select_tex_file()
        if selected_file:
            return compile_latex(selected_file, run_context)
        else:
            error_data = {
                "success": False, 
                "error": "No file selected", 
                "file": None
            }
            
            if run_context['in_run_context']:
                write_to_json_output(error_data, run_context)
            else:
                print("Error: No file selected")
            return 1
    else:
        # 有参数时，直接编译指定文件
        tex_file = sys.argv[1]
        return compile_latex(tex_file, run_context)

if __name__ == "__main__":
    sys.exit(main()) 