#!/usr/bin/env python3
"""
使用UnimerNet识别的结果重新编译LaTeX，验证识别准确性
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

def load_recognition_results():
    """加载识别结果"""
    results_file = Path("latex_recognition_results.json")
    if not results_file.exists():
        print("❌ 识别结果文件不存在")
        return None
        
    with open(results_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_latex_from_recognition(recognition_result, content_type):
    """根据识别结果创建LaTeX文档"""
    
    # 基础LaTeX模板 - 使用简单的字符串拼接
    latex_content = r"""
\documentclass[12pt]{article}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{array}
\usepackage{booktabs}
\begin{document}
\pagestyle{empty}

\[
""" + recognition_result + r"""
\]

\end{document}
"""
    
    return latex_content

def compile_latex_from_recognition(latex_content, output_name):
    """编译识别结果生成的LaTeX"""
    current_dir = Path.cwd()
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        tex_file = temp_path / f"{output_name}.tex"
        
        # 写入LaTeX文件
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        
        print(f"创建LaTeX文件: {tex_file}")
        
        # 编译LaTeX
        try:
            pdflatex_path = "/Library/TeX/texbin/pdflatex"
            
            # 设置环境变量
            env = os.environ.copy()
            env['PATH'] = '/Library/TeX/texbin:' + env.get('PATH', '')
            
            # 编译命令
            cmd = [pdflatex_path, '-interaction=nonstopmode', str(tex_file)]
            
            print(f"执行编译命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=temp_path,
                capture_output=True,
                text=True,
                env=env
            )
            
            print(f"编译返回码: {result.returncode}")
            
            if result.returncode == 0:
                # 编译成功
                pdf_file = temp_path / f"{output_name}.pdf"
                if pdf_file.exists():
                    # 复制PDF到当前目录
                    output_pdf = current_dir / f"{output_name}_unimernet.pdf"
                    import shutil
                    shutil.copy2(pdf_file, output_pdf)
                    print(f"✅ 编译成功: {output_pdf}")
                    return True, output_pdf, None
                else:
                    print(f"❌ PDF文件未生成")
                    return False, None, "PDF文件未生成"
            else:
                # 编译失败
                print(f"❌ 编译失败")
                print(f"标准输出: {result.stdout}")
                print(f"标准错误: {result.stderr}")
                return False, None, result.stderr
                
        except Exception as e:
            print(f"❌ 编译出错: {e}")
            return False, None, str(e)

def test_reverse_compilation():
    """测试反向编译"""
    print("=== 使用UnimerNet识别结果重新编译LaTeX ===")
    
    # 加载识别结果
    results = load_recognition_results()
    if not results:
        return
    
    compilation_results = {}
    
    for pdf_file, result_data in results.items():
        if not result_data['recognition_result']:
            print(f"❌ {pdf_file}: 无识别结果，跳过")
            continue
            
        # 提取内容类型
        content_type = pdf_file.replace('.pdf', '')
        recognition_result = result_data['recognition_result']
        
        print(f"\n--- 处理 {pdf_file} ---")
        print(f"内容类型: {content_type}")
        print(f"识别结果: {recognition_result[:100]}...")
        
        # 创建LaTeX内容
        latex_content = create_latex_from_recognition(recognition_result, content_type)
        
        # 编译LaTeX
        success, output_path, error = compile_latex_from_recognition(latex_content, content_type)
        
        compilation_results[pdf_file] = {
            'success': success,
            'output_path': str(output_path) if output_path else None,
            'error': error,
            'recognition_result': recognition_result
        }
        
        if success:
            print(f"✅ {pdf_file} 重新编译成功")
        else:
            print(f"❌ {pdf_file} 重新编译失败: {error}")
    
    # 保存编译结果
    with open('reverse_compilation_results.json', 'w', encoding='utf-8') as f:
        json.dump(compilation_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== 反向编译测试完成 ===")
    print(f"结果已保存到: reverse_compilation_results.json")
    
    # 显示总结
    print("\n=== 编译结果总结 ===")
    success_count = 0
    total_count = 0
    
    for pdf_file, result in compilation_results.items():
        total_count += 1
        if result['success']:
            success_count += 1
            print(f"✅ {pdf_file}: 编译成功 → {result['output_path']}")
        else:
            print(f"❌ {pdf_file}: 编译失败 → {result['error']}")
    
    print(f"\n成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")

if __name__ == "__main__":
    test_reverse_compilation() 