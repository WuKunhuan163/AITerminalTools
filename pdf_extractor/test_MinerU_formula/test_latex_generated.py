#!/usr/bin/env python3
"""
测试LaTeX生成的PDF图像使用UnimerNet识别
"""
import sys
import os
import subprocess
from pathlib import Path
from PIL import Image
import json
import torch

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
mineru_path = project_root / "pdf_extractor/pdf_extractor_MinerU"
sys.path.insert(0, str(mineru_path))

def pdf_to_image(pdf_path, output_path, dpi=300):
    """将PDF转换为图像"""
    try:
        # 使用pdftoppm转换PDF为图像
        cmd = [
            'pdftoppm',
            '-png',
            '-r', str(dpi),
            '-singlefile',
            str(pdf_path),
            str(output_path.with_suffix(''))
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # pdftoppm会自动添加.png后缀
            actual_output = output_path.with_suffix('.png')
            if actual_output.exists():
                print(f"✅ PDF转换成功: {actual_output}")
                return actual_output
            else:
                print(f"❌ 转换后的图像文件不存在: {actual_output}")
                return None
        else:
            print(f"❌ PDF转换失败: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ PDF转换出错: {e}")
        return None

def load_unimernet_model():
    """加载UnimerNet模型"""
    try:
        from mineru.model.mfr.unimernet.unimernet_hf.modeling_unimernet import UnimernetModel
        
        # 使用本地的 models 目录
        model_path = Path(__file__).parent / "models" / "unimernet_base"
        
        print(f"加载模型从: {model_path}")
        
        # 使用from_checkpoint方法加载模型（这会自动处理tokenizer）
        model = UnimernetModel.from_checkpoint(str(model_path), "pytorch_model.pth")
        print(f"✅ 模型加载成功: {type(model)}")
        print(f"✅ Tokenizer类型: {type(model.tokenizer)}")
        
        return model
        
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def recognize_image(model, image_path):
    """使用UnimerNet识别图像"""
    try:
        # 打开图像
        image = Image.open(image_path)
        print(f"图像尺寸: {image.size}")
        
        # 预处理图像
        transform = model.transform
        processed_image = transform(image)
        
        # 添加batch维度
        if len(processed_image.shape) == 3:
            processed_image = processed_image.unsqueeze(0)
            
        sample = {"image": processed_image}
        
        # 使用模型进行推理
        print("开始识别...")
        with torch.no_grad():
            result = model.generate(sample)
            
        # 提取识别结果
        if isinstance(result, dict) and 'fixed_str' in result:
            formulas = result['fixed_str']
            if isinstance(formulas, list) and len(formulas) > 0:
                return formulas[0]  # 返回第一个结果
            else:
                return str(formulas)
        else:
            return str(result)
        
    except Exception as e:
        print(f"❌ 图像识别失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_latex_pdfs():
    """测试LaTeX生成的PDF"""
    print("=== 测试LaTeX生成的PDF ===")
    print(f"MinerU路径: {mineru_path}")
    print(f"项目根路径: {project_root}")
    
    # 加载模型
    model = load_unimernet_model()
    if model is None:
        print("❌ 无法加载模型，退出测试")
        return
    
    # 待测试的PDF文件
    pdf_files = ['table.pdf', 'formula.pdf', 'matrix.pdf']
    
    results = {}
    
    for pdf_file in pdf_files:
        pdf_path = Path(pdf_file)
        if not pdf_path.exists():
            print(f"❌ PDF文件不存在: {pdf_path}")
            continue
            
        print(f"\n--- 处理 {pdf_file} ---")
        
        # 转换PDF为图像
        image_path = Path(f"{pdf_path.stem}.png")
        image_file = pdf_to_image(pdf_path, image_path)
        
        if image_file is None:
            continue
            
        # 识别图像
        print(f"使用UnimerNet识别图像...")
        result = recognize_image(model, image_file)
        
        if result:
            print(f"✅ 识别结果: {result}")
            results[pdf_file] = {
                'image_path': str(image_file),
                'recognition_result': result
            }
        else:
            print(f"❌ 识别失败")
            results[pdf_file] = {
                'image_path': str(image_file),
                'recognition_result': None
            }
    
    # 保存结果
    with open('latex_recognition_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== 测试完成 ===")
    print(f"结果已保存到: latex_recognition_results.json")
    
    # 显示总结
    print("\n=== 识别结果总结 ===")
    for pdf_file, result in results.items():
        if result['recognition_result']:
            print(f"✅ {pdf_file}: {result['recognition_result']}")
        else:
            print(f"❌ {pdf_file}: 识别失败")

if __name__ == "__main__":
    test_latex_pdfs() 