#!/usr/bin/env python3
"""
使用LaTeX生成表格和公式图像用于测试UnimerNet
"""
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from PIL import Image
import shutil

def create_latex_table():
    """创建LaTeX表格代码"""
    return r"""
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

def create_latex_formula():
    """创建LaTeX公式代码"""
    return r"""
\documentclass[12pt]{article}
\usepackage{amsmath}
\usepackage{amssymb}
\begin{document}
\pagestyle{empty}

\begin{align}
E &= mc^2 \\
\int_{-\infty}^{\infty} e^{-x^2} dx &= \sqrt{\pi} \\
\sum_{n=1}^{\infty} \frac{1}{n^2} &= \frac{\pi^2}{6}
\end{align}

\end{document}
"""

def create_latex_matrix():
    """创建LaTeX矩阵代码"""
    return r"""
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

def compile_latex_to_image(latex_code, output_name):
    """编译LaTeX代码为图像"""
    output_dir = Path(__file__).parent / "latex_images"
    output_dir.mkdir(exist_ok=True)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 写入LaTeX文件
        tex_file = temp_path / "document.tex"
        with open(tex_file, 'w') as f:
            f.write(latex_code)
        
        try:
            # 编译LaTeX
            print(f"编译LaTeX文件: {output_name}")
            # 确保使用完整路径
            pdflatex_path = '/Library/TeX/texbin/pdflatex'
            result = subprocess.run([
                pdflatex_path, '-interaction=nonstopmode', str(tex_file)
            ], cwd=temp_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"LaTeX编译失败: {result.stderr}")
                return None
            
            # 转换PDF为PNG
            pdf_file = temp_path / "document.pdf"
            png_file = output_dir / f"{output_name}.png"
            
            if pdf_file.exists():
                # 使用ImageMagick转换PDF为PNG
                convert_result = subprocess.run([
                    'convert', '-density', '300', str(pdf_file), str(png_file)
                ], capture_output=True, text=True)
                
                if convert_result.returncode != 0:
                    print(f"PDF转PNG失败: {convert_result.stderr}")
                    # 尝试使用pdftoppm
                    try:
                        subprocess.run([
                            'pdftoppm', '-png', '-r', '300', str(pdf_file), str(png_file.with_suffix(''))
                        ], check=True)
                        # pdftoppm会添加-1.png后缀
                        actual_png = png_file.with_name(f"{png_file.stem}-1.png")
                        if actual_png.exists():
                            actual_png.rename(png_file)
                    except subprocess.CalledProcessError:
                        print(f"PDF转换失败，尝试手动处理")
                        return None
                
                if png_file.exists():
                    print(f"✅ 生成图像: {png_file}")
                    return png_file
                else:
                    print(f"❌ 图像生成失败: {png_file}")
                    return None
            else:
                print(f"❌ PDF文件不存在: {pdf_file}")
                return None
                
        except FileNotFoundError:
            print("❌ 未找到pdflatex，请安装LaTeX")
            return None
        except Exception as e:
            print(f"❌ 编译过程出错: {e}")
            return None

def check_latex_dependencies():
    """检查LaTeX依赖"""
    print("检查LaTeX依赖...")
    
    # 检查pdflatex
    try:
        pdflatex_path = '/Library/TeX/texbin/pdflatex'
        result = subprocess.run([pdflatex_path, '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ pdflatex 可用")
        else:
            print("❌ pdflatex 不可用")
            return False
    except FileNotFoundError:
        print("❌ pdflatex 未安装")
        return False
    
    # 检查转换工具
    convert_available = False
    try:
        result = subprocess.run(['convert', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ImageMagick convert 可用")
            convert_available = True
    except FileNotFoundError:
        pass
    
    try:
        result = subprocess.run(['pdftoppm', '-h'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ pdftoppm 可用")
            convert_available = True
    except FileNotFoundError:
        pass
    
    if not convert_available:
        print("❌ 需要安装 ImageMagick 或 poppler-utils")
        return False
    
    return True

def generate_all_test_images():
    """生成所有测试图像"""
    print("=== 生成LaTeX测试图像 ===")
    
    if not check_latex_dependencies():
        print("❌ 缺少必要的依赖，无法生成图像")
        return []
    
    images = []
    
    # 生成表格
    table_latex = create_latex_table()
    table_image = compile_latex_to_image(table_latex, "latex_table")
    if table_image:
        images.append(("表格", table_image))
    
    # 生成公式
    formula_latex = create_latex_formula()
    formula_image = compile_latex_to_image(formula_latex, "latex_formula")
    if formula_image:
        images.append(("公式", formula_image))
    
    # 生成矩阵
    matrix_latex = create_latex_matrix()
    matrix_image = compile_latex_to_image(matrix_latex, "latex_matrix")
    if matrix_image:
        images.append(("矩阵", matrix_image))
    
    return images

if __name__ == "__main__":
    images = generate_all_test_images()
    
    if images:
        print(f"\n✅ 成功生成 {len(images)} 个测试图像:")
        for name, path in images:
            print(f"  - {name}: {path}")
    else:
        print("\n❌ 没有生成任何图像") 