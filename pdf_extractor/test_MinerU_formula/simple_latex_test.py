#!/usr/bin/env python3
"""
简单的LaTeX编译测试 - 直接使用pdflatex
"""
import os
import subprocess
import tempfile
from pathlib import Path

def create_simple_latex_files():
    """创建简单的LaTeX测试文件"""
    
    # 表格LaTeX
    table_latex = r"""
\documentclass[12pt]{article}
\usepackage{amsmath}
\usepackage{array}
\usepackage{booktabs}
\begin{document}
\pagestyle{empty}

\begin{table}[h]
\centering
\begin{tabular}{|c|c|c|}
\hline
$x$ & $y$ & $z$ \\
\hline
1 & 2 & 3 \\
\hline
4 & 5 & 6 \\
\hline
$\alpha$ & $\beta$ & $\gamma$ \\
\hline
\end{tabular}
\end{table}

\end{document}
"""

    # 公式LaTeX
    formula_latex = r"""
\documentclass[12pt]{article}
\usepackage{amsmath}
\usepackage{amssymb}
\begin{document}
\pagestyle{empty}

\begin{align}
f(x) &= \int_{-\infty}^{\infty} e^{-x^2} dx \\
&= \sqrt{\pi} \\
\nabla \cdot \vec{F} &= \frac{\partial F_x}{\partial x} + \frac{\partial F_y}{\partial y} + \frac{\partial F_z}{\partial z}
\end{align}

\end{document}
"""

    # 矩阵LaTeX
    matrix_latex = r"""
\documentclass[12pt]{article}
\usepackage{amsmath}
\usepackage{amssymb}
\begin{document}
\pagestyle{empty}

\[
\begin{pmatrix}
a & b & c \\
d & e & f \\
g & h & i
\end{pmatrix}
\begin{pmatrix}
x \\
y \\
z
\end{pmatrix}
=
\begin{pmatrix}
ax + by + cz \\
dx + ey + fz \\
gx + hy + iz
\end{pmatrix}
\]

\end{document}
"""

    return {
        'table': table_latex,
        'formula': formula_latex,
        'matrix': matrix_latex
    }

def compile_latex_to_pdf(latex_content, output_name):
    """编译LaTeX到PDF"""
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
            # 使用绝对路径
            pdflatex_path = "/Library/TeX/texbin/pdflatex"
            
            # 检查pdflatex是否存在
            if not os.path.exists(pdflatex_path):
                print(f"pdflatex不存在于: {pdflatex_path}")
                # 尝试使用系统PATH中的pdflatex
                result = subprocess.run(['which', 'pdflatex'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    pdflatex_path = result.stdout.strip()
                    print(f"找到pdflatex: {pdflatex_path}")
                else:
                    print("未找到pdflatex命令")
                    return None
            
            # 设置环境变量
            env = os.environ.copy()
            env['PATH'] = '/Library/TeX/texbin:' + env.get('PATH', '')
            
            # 编译命令
            cmd = [pdflatex_path, '-interaction=nonstopmode', str(tex_file)]
            
            print(f"执行命令: {' '.join(cmd)}")
            print(f"工作目录: {temp_path}")
            
            result = subprocess.run(
                cmd,
                cwd=temp_path,
                capture_output=True,
                text=True,
                env=env
            )
            
            print(f"返回码: {result.returncode}")
            if result.stdout:
                print(f"标准输出: {result.stdout}")
            if result.stderr:
                print(f"标准错误: {result.stderr}")
            
            pdf_file = temp_path / f"{output_name}.pdf"
            if pdf_file.exists():
                # 复制PDF到当前目录
                output_pdf = current_dir / f"{output_name}.pdf"
                import shutil
                shutil.copy2(pdf_file, output_pdf)
                print(f"PDF生成成功: {output_pdf}")
                return output_pdf
            else:
                print(f"PDF文件未生成: {pdf_file}")
                return None
                
        except Exception as e:
            print(f"编译LaTeX时出错: {e}")
            return None

def main():
    """主函数"""
    print("=== 简单LaTeX编译测试 ===")
    
    # 创建LaTeX内容
    latex_files = create_simple_latex_files()
    
    # 编译每个文件
    for name, content in latex_files.items():
        print(f"\n--- 编译 {name} ---")
        pdf_path = compile_latex_to_pdf(content, name)
        if pdf_path:
            print(f"✅ {name} 编译成功: {pdf_path}")
        else:
            print(f"❌ {name} 编译失败")

if __name__ == "__main__":
    main() 