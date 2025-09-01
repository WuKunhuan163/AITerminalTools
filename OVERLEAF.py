#!/usr/bin/env python3
"""
OVERLEAF.py - LaTeX文件编译工具
支持GUI文件选择、JSON返回值、模板复制功能，能够检测RUN环境
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def is_run_environment(command_identifier=None):
    """Check if running in RUN environment by checking environment variables"""
    if command_identifier:
        return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
    return False

def copy_to_clipboard(text):
    """Copy text to clipboard using pbcopy on macOS"""
    try:
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, text=True)
        process.communicate(input=text)
        return process.returncode == 0
    except Exception:
        return False

def extract_latex_errors(log_content):
    """Extract meaningful error messages from LaTeX log"""
    lines = log_content.split('\n')
    errors = []
    
    for i, line in enumerate(lines):
        # Look for error indicators
        if line.startswith('!') or 'Error:' in line:
            error_context = []
            # Get some context around the error
            start = max(0, i-2)
            end = min(len(lines), i+3)
            for j in range(start, end):
                if lines[j].strip():
                    error_context.append(lines[j])
            errors.append('\n'.join(error_context))
    
    return errors

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
        print(f"Error: tkinter is not available. Please provide a file path as argument.")
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

def get_templates_dir():
    """获取模板目录路径"""
    # 获取脚本所在目录
    script_dir = Path(__file__).parent
    templates_dir = script_dir / "OVERLEAF_PROJ" / "templates"
    return templates_dir

def list_available_templates():
    """列出可用的模板"""
    templates_dir = get_templates_dir()
    if not templates_dir.exists():
        return []
    
    templates = []
    for item in templates_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            templates.append(item.name)
    return templates

def copy_template(template_name, target_dir, command_identifier=None):
    """复制模板到目标目录"""
    templates_dir = get_templates_dir()
    template_path = templates_dir / template_name
    target_path = Path(target_dir).resolve()
    
    # 检查模板是否存在
    if not template_path.exists() or not template_path.is_dir():
        available_templates = list_available_templates()
        error_msg = f"Template '{template_name}' not found. Available templates: {', '.join(available_templates)}"
        error_data = {
            "success": False,
            "error": error_msg,
            "available_templates": available_templates
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(f"Error: {error_msg}")
        return 1
    
    # 检查目标目录
    if target_path.exists():
        # 检查目录是否为空
        if target_path.is_dir():
            if any(target_path.iterdir()):
                error_msg = f"Target directory '{target_dir}' is not empty"
                error_data = {
                    "success": False,
                    "error": error_msg,
                    "target_dir": str(target_path)
                }
                
                if is_run_environment(command_identifier):
                    write_to_json_output(error_data, command_identifier)
                else:
                    print(f"Error: {error_msg}")
                return 1
        else:
            error_msg = f"Target path '{target_dir}' exists but is not a directory"
            error_data = {
                "success": False,
                "error": error_msg,
                "target_dir": str(target_path)
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(error_data, command_identifier)
            else:
                print(f"Error: {error_msg}")
            return 1
    else:
        # 创建目标目录
        try:
            target_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            error_msg = f"Failed to create target directory '{target_dir}': {str(e)}"
            error_data = {
                "success": False,
                "error": error_msg,
                "target_dir": str(target_path)
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(error_data, command_identifier)
            else:
                print(f"Error: {error_msg}")
            return 1
    
    # 复制模板内容
    try:
        for item in template_path.iterdir():
            if item.name.startswith('.'):
                continue  # 跳过隐藏文件
            
            target_item = target_path / item.name
            if item.is_dir():
                shutil.copytree(item, target_item)
            else:
                shutil.copy2(item, target_item)
        
        success_data = {
            "success": True,
            "message": f"Template '{template_name}' copied successfully",
            "template": template_name,
            "target_dir": str(target_path),
            "files_copied": [item.name for item in template_path.iterdir() if not item.name.startswith('.')]
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(success_data, command_identifier)
        else:
            print(f"Template '{template_name}' copied successfully to '{target_path}'")
            print(f"Files copied: {', '.join(success_data['files_copied'])}")
        return 0
        
    except Exception as e:
        error_msg = f"Failed to copy template: {str(e)}"
        error_data = {
            "success": False,
            "error": error_msg,
            "template": template_name,
            "target_dir": str(target_path)
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(f"Error: {error_msg}")
        return 1

def compile_latex(tex_file, command_identifier=None, output_dir=None, latex_options=None, no_shell_escape=False):
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
    
    # 显示编译开始信息
    if not is_run_environment(command_identifier):
        print(f"Starting LaTeX compilation for: {tex_path.name}")
        print(f"Compiling...")
    
    # 在RUN环境下，使用/tmp目录作为工作目录
    if is_run_environment(command_identifier):
        # 创建临时工作目录
        work_dir = Path(tempfile.mkdtemp(prefix=f"overleaf_{filename}_"))
        # 复制tex文件到临时目录
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
        
        # 构建编译命令，默认添加-shell-escape选项
        default_options = ['-interaction=nonstopmode']
        if not no_shell_escape:
            default_options.append('-shell-escape')
        
        if latex_options:
            # 合并用户提供的选项和默认选项
            all_options = default_options + latex_options
        else:
            all_options = default_options
        
        pdflatex_cmd = 'pdflatex ' + ' '.join(all_options)
        
        # 执行编译
        cmd = [
            'latexmk', '-pdf', 
            f'-pdflatex={pdflatex_cmd}',
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
            
            # 手动删除额外的临时文件
            temp_files = [
                f"{filename}.fdb_latexmk",
                f"{filename}.bbl",
                f"{filename}.blg",
                f"{filename}.run.xml",
                f"{filename}.bcf"
            ]
            
            for temp_file in temp_files:
                temp_path = directory / temp_file
                if temp_path.exists():
                    temp_path.unlink()
            
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
                    print(f"✓ LaTeX compilation successful!")
                    print(f"✓ Generated PDF: {final_pdf_path}")
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
                    print(f"Error: PDF not generated")
                    print(f"Input file: {tex_path}")
                    print(f"\n=== Compilation Log ===")
                    print(log_content)
                return 1
        else:
            # 编译失败
            # 提取关键错误信息
            errors = extract_latex_errors(log_content)
            
            if is_run_environment(command_identifier):
                error_summary = '\n'.join(errors) if errors else log_content[-2000:]
                error_data = {
                    "success": False, 
                    "error": f"Compilation failed: {error_summary}", 
                    "file": str(tex_path),
                    "exit_code": result.returncode
                }
                write_to_json_output(error_data, command_identifier)
            else:
                print(f"Error: LaTeX compilation failed! (Exit code: {result.returncode})")
                print(f"Error: Input file: {tex_path.name}")
                
                if errors:
                    print(f"\n=== Key Error Messages ===")
                    for i, error in enumerate(errors[:5], 1):  # Show up to 5 errors
                        print(f"Error {i}:")
                        print(error)
                        print(f"-" * 50)
                else:
                    print(f"\n=== No specific errors found, showing last part of log ===")
                    log_lines = log_content.split('\n')
                    print('\n'.join(log_lines[-20:]))
                
                # 复制完整日志到剪切板
                if copy_to_clipboard(log_content):
                    print(f"\n✓ Full compilation log copied to clipboard")
                else:
                    print(f"\n✗ Failed to copy log to clipboard")
                    
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
    parser = argparse.ArgumentParser(description='OVERLEAF - LaTeX文件编译工具，支持模板复制')
    parser.add_argument('tex_file', nargs='?', help='LaTeX文件路径')
    parser.add_argument('--output-dir', help='输出目录，编译完成后将PDF移动到此目录')
    parser.add_argument('--template', nargs=2, metavar=('TEMPLATE_NAME', 'TARGET_DIR'), 
                       help='复制模板到指定目录：--template TEMPLATE_NAME TARGET_DIR')
    parser.add_argument('--list-templates', action='store_true', 
                       help='列出所有可用的模板')
    parser.add_argument('--latex-options', action='append', default=[], 
                       help='传递给pdflatex的额外选项 (默认已包含-shell-escape)，可多次使用：--latex-options=-synctex=1 --latex-options=-file-line-error')
    parser.add_argument('--no-shell-escape', action='store_true',
                       help='禁用默认的-shell-escape选项')
    
    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        # argparse的--help会导致SystemExit，我们需要正常处理
        return 0
    
    # 处理列出模板选项
    if parsed_args.list_templates:
        templates = list_available_templates()
        if templates:
            list_data = {
                "success": True,
                "available_templates": templates,
                "message": f"Available templates: {', '.join(templates)}"
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(list_data, command_identifier)
            else:
                print(f"Available templates:")
                for template in templates:
                    print(f"  - {template}")
        else:
            error_data = {
                "success": False,
                "error": "No templates found",
                "available_templates": []
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(error_data, command_identifier)
            else:
                print(f"No templates found")
        return 0
    
    # 处理模板复制选项
    if parsed_args.template:
        template_name, target_dir = parsed_args.template
        return copy_template(template_name, target_dir, command_identifier)
    
    if not parsed_args.tex_file:
        # 没有文件参数时，打开文件选择器
        selected_file = select_tex_file()
        if selected_file:
            return compile_latex(selected_file, command_identifier, parsed_args.output_dir, 
                               parsed_args.latex_options, parsed_args.no_shell_escape)
        else:
            error_data = {
                "success": False, 
                "error": "No file selected", 
                "file": None
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(error_data, command_identifier)
            else:
                print(f"Error: No file selected")
            return 1
    else:
        # 有参数时，直接编译指定文件
        return compile_latex(parsed_args.tex_file, command_identifier, parsed_args.output_dir,
                           parsed_args.latex_options, parsed_args.no_shell_escape)

if __name__ == "__main__":
    sys.exit(main()) 