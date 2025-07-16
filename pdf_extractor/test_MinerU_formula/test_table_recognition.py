#!/usr/bin/env python3
"""
测试UnimerNet对表格的识别能力
"""
import sys
import os
import traceback
import torch
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json

# 添加MinerU路径
sys.path.insert(0, str(Path(__file__).parent.parent / "pdf_extractor_MinerU"))

def create_simple_table_image():
    """创建一个简单的表格图像"""
    width, height = 400, 200
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # 绘制表格框架
    # 外框
    draw.rectangle([20, 20, 380, 180], outline='black', width=2)
    
    # 内部线条
    draw.line([20, 70, 380, 70], fill='black', width=1)  # 水平线
    draw.line([20, 120, 380, 120], fill='black', width=1)  # 水平线
    draw.line([150, 20, 150, 180], fill='black', width=1)  # 垂直线
    draw.line([280, 20, 280, 180], fill='black', width=1)  # 垂直线
    
    # 添加文本（简单的数字和字母）
    try:
        font = ImageFont.load_default()
        draw.text((30, 35), "A", fill='black', font=font)
        draw.text((160, 35), "B", fill='black', font=font)
        draw.text((290, 35), "C", fill='black', font=font)
        
        draw.text((30, 85), "1", fill='black', font=font)
        draw.text((160, 85), "2", fill='black', font=font)
        draw.text((290, 85), "3", fill='black', font=font)
        
        draw.text((30, 135), "x", fill='black', font=font)
        draw.text((160, 135), "y", fill='black', font=font)
        draw.text((290, 135), "z", fill='black', font=font)
    except:
        pass
    
    return image

def create_formula_image():
    """创建一个包含数学公式的图像"""
    width, height = 300, 100
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # 绘制简单的数学公式 (手工绘制，模拟 x^2 + y^2 = z^2)
    try:
        font = ImageFont.load_default()
        draw.text((50, 40), "x² + y² = z²", fill='black', font=font)
    except:
        draw.text((50, 40), "x^2 + y^2 = z^2", fill='black')
    
    return image

def test_table_recognition():
    """测试表格识别"""
    print("=== 测试表格识别 ===")
    
    # 使用本地模型路径
    model_path = str(Path(__file__).parent.parent / "math_formula_test" / "models" / "unimernet_base")
    
    try:
        from mineru.model.mfr.unimernet.unimernet_hf.modeling_unimernet import UnimernetModel
        
        print("加载UnimerNet模型...")
        model = UnimernetModel.from_checkpoint(model_path, "pytorch_model.pth")
        print("✅ 模型加载成功!")
        
        # 创建表格图像
        table_image = create_simple_table_image()
        print(f"创建表格图像: {table_image.size}")
        
        # 保存图像以供检查
        table_path = Path(__file__).parent / "test_table.png"
        table_image.save(table_path)
        print(f"表格图像已保存到: {table_path}")
        
        # 预处理和识别
        transform = model.transform
        processed_image = transform(table_image)
        
        if len(processed_image.shape) == 3:
            processed_image = processed_image.unsqueeze(0)
            
        sample = {"image": processed_image}
        
        print("开始表格识别...")
        with torch.no_grad():
            result = model.generate(sample)
            
        print("✅ 表格识别完成!")
        
        if isinstance(result, dict) and 'fixed_str' in result:
            table_results = result['fixed_str']
            print(f"表格识别结果: {table_results}")
            
            # 分析结果
            if table_results and len(table_results) > 0:
                result_str = table_results[0]
                print(f"结果分析:")
                has_array = '\\begin{array}' in result_str
                has_tabular = '\\begin{tabular}' in result_str
                has_matrix = '\\begin{matrix}' in result_str
                print(f"  - 是否包含表格标记: {has_array or has_tabular}")
                print(f"  - 是否包含矩阵标记: {has_matrix}")
                print(f"  - 结果长度: {len(result_str)}")
        else:
            print(f"结果格式: {result}")
            
        return True
        
    except Exception as e:
        print(f"❌ 表格识别失败: {e}")
        traceback.print_exc()
        return False

def test_formula_vs_table():
    """对比公式和表格的识别结果"""
    print("\n=== 对比公式和表格识别 ===")
    
    model_path = str(Path(__file__).parent.parent / "math_formula_test" / "models" / "unimernet_base")
    
    try:
        from mineru.model.mfr.unimernet.unimernet_hf.modeling_unimernet import UnimernetModel
        
        print("加载UnimerNet模型...")
        model = UnimernetModel.from_checkpoint(model_path, "pytorch_model.pth")
        
        # 测试公式
        print("\n--- 测试公式识别 ---")
        formula_image = create_formula_image()
        formula_path = Path(__file__).parent / "test_formula.png"
        formula_image.save(formula_path)
        print(f"公式图像已保存到: {formula_path}")
        
        transform = model.transform
        processed_formula = transform(formula_image)
        if len(processed_formula.shape) == 3:
            processed_formula = processed_formula.unsqueeze(0)
        
        with torch.no_grad():
            formula_result = model.generate({"image": processed_formula})
        
        if isinstance(formula_result, dict) and 'fixed_str' in formula_result:
            print(f"公式识别结果: {formula_result['fixed_str']}")
        
        # 测试表格
        print("\n--- 测试表格识别 ---")
        table_image = create_simple_table_image()
        processed_table = transform(table_image)
        if len(processed_table.shape) == 3:
            processed_table = processed_table.unsqueeze(0)
        
        with torch.no_grad():
            table_result = model.generate({"image": processed_table})
        
        if isinstance(table_result, dict) and 'fixed_str' in table_result:
            print(f"表格识别结果: {table_result['fixed_str']}")
        
        # 对比分析
        print("\n--- 结果对比 ---")
        if (isinstance(formula_result, dict) and 'fixed_str' in formula_result and 
            isinstance(table_result, dict) and 'fixed_str' in table_result):
            
            formula_str = formula_result['fixed_str'][0] if formula_result['fixed_str'] else ""
            table_str = table_result['fixed_str'][0] if table_result['fixed_str'] else ""
            
            print(f"公式结果特征:")
            has_math_symbols = any(sym in formula_str for sym in ['^', '_', '\\frac', '\\sqrt'])
            print(f"  - 包含数学符号: {has_math_symbols}")
            print(f"  - 结果长度: {len(formula_str)}")
            
            print(f"表格结果特征:")
            has_table_marks = any(mark in table_str for mark in ['\\begin{array}', '\\begin{tabular}', '\\begin{matrix}'])
            has_separators = '&' in table_str
            print(f"  - 包含表格/矩阵标记: {has_table_marks}")
            print(f"  - 包含分隔符: {has_separators}")
            print(f"  - 结果长度: {len(table_str)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 对比测试失败: {e}")
        traceback.print_exc()
        return False

def test_real_pdf_table_images():
    """测试真实PDF中的表格图像"""
    print("\n=== 测试真实PDF表格图像 ===")
    
    # 查找PDF提取的图像，寻找可能的表格
    images_dir = Path(__file__).parent.parent / "pdf_extractor_data" / "images"
    
    if not images_dir.exists():
        print(f"❌ 图像目录不存在: {images_dir}")
        return False
    
    image_files = list(images_dir.glob("*.png"))
    
    if not image_files:
        print("❌ 没有找到图像文件")
        return False
    
    model_path = str(Path(__file__).parent.parent / "math_formula_test" / "models" / "unimernet_base")
    
    try:
        from mineru.model.mfr.unimernet.unimernet_hf.modeling_unimernet import UnimernetModel
        
        print("加载UnimerNet模型...")
        model = UnimernetModel.from_checkpoint(model_path, "pytorch_model.pth")
        
        # 测试前几个图像，寻找表格特征
        for i, image_file in enumerate(image_files[:5]):
            print(f"\n--- 测试图像 {i+1}: {image_file.name} ---")
            
            try:
                image = Image.open(image_file)
                print(f"图像大小: {image.size}")
                
                # 预处理
                transform = model.transform
                processed_image = transform(image)
                if len(processed_image.shape) == 3:
                    processed_image = processed_image.unsqueeze(0)
                
                # 识别
                with torch.no_grad():
                    result = model.generate({"image": processed_image})
                
                if isinstance(result, dict) and 'fixed_str' in result:
                    result_str = result['fixed_str'][0] if result['fixed_str'] else ""
                    
                    # 分析是否为表格
                    is_table = any(mark in result_str for mark in ['\\begin{array}', '\\begin{tabular}', '\\begin{matrix}'])
                    has_separators = '&' in result_str
                    has_newlines = '\\\\' in result_str
                    
                    print(f"识别结果分析:")
                    print(f"  - 可能是表格: {is_table}")
                    print(f"  - 包含分隔符: {has_separators}")
                    print(f"  - 包含换行符: {has_newlines}")
                    print(f"  - 结果长度: {len(result_str)}")
                    
                    if is_table or (has_separators and has_newlines):
                        print(f"  - 🔍 疑似表格内容: {result_str[:200]}...")
                
            except Exception as e:
                print(f"❌ 图像处理失败: {e}")
                continue
        
        return True
        
    except Exception as e:
        print(f"❌ 真实图像测试失败: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("UnimerNet 表格识别测试工具")
    print("=" * 60)
    
    # 基本表格识别测试
    test_table_recognition()
    
    # 公式与表格对比测试
    test_formula_vs_table()
    
    # 真实PDF图像测试
    test_real_pdf_table_images()
    
    print("\n测试完成！") 