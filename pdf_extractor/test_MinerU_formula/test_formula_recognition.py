#!/usr/bin/env python3
"""
测试UnimerNet公式识别功能
"""
import sys
import os
import traceback
import torch
from pathlib import Path
from PIL import Image
import numpy as np

# 添加MinerU路径
sys.path.insert(0, str(Path(__file__).parent.parent / "pdf_extractor_MinerU"))

def create_sample_formula_image():
    """创建一个简单的公式图像用于测试"""
    # 创建一个简单的白色背景图像
    width, height = 200, 100
    image = Image.new('RGB', (width, height), 'white')
    
    # 这里我们只创建一个简单的白色图像作为占位符
    # 在实际应用中，这应该是包含数学公式的图像
    return image

def test_formula_recognition():
    """测试公式识别功能"""
    print("=== 测试公式识别功能 ===")
    
    # 使用本地模型路径
    model_path = str(Path(__file__).parent.parent / "math_formula_test" / "models" / "unimernet_base")
    
    try:
        from mineru.model.mfr.unimernet.unimernet_hf.modeling_unimernet import UnimernetModel
        
        print("加载UnimerNet模型...")
        model = UnimernetModel.from_checkpoint(model_path, "pytorch_model.pth")
        print("✅ 模型加载成功!")
        
        # 创建测试图像
        test_image = create_sample_formula_image()
        print(f"创建测试图像: {test_image.size}")
        
        # 将PIL图像转换为tensor
        transform = model.transform
        if hasattr(transform, 'preprocess'):
            processed_image = transform.preprocess(test_image)
        else:
            # 如果没有preprocess方法，尝试直接调用transform
            processed_image = transform(test_image)
            
        print(f"图像预处理完成: {processed_image.shape}")
        
        # 准备输入数据
        if len(processed_image.shape) == 3:
            # 添加batch维度
            processed_image = processed_image.unsqueeze(0)
            
        sample = {"image": processed_image}
        
        # 进行推理
        print("开始公式识别...")
        with torch.no_grad():
            result = model.generate(sample)
            
        print("✅ 公式识别完成!")
        print(f"识别结果类型: {type(result)}")
        print(f"结果keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
        
        if isinstance(result, dict) and 'fixed_str' in result:
            formulas = result['fixed_str']
            print(f"识别到的公式: {formulas}")
        
        return True
        
    except Exception as e:
        print(f"❌ 公式识别失败: {e}")
        print(f"错误类型: {type(e)}")
        traceback.print_exc()
        return False

def test_with_pdf_images():
    """使用PDF提取的图像进行测试"""
    print("\n=== 使用PDF图像测试 ===")
    
    # 查找PDF提取的图像
    images_dir = Path(__file__).parent.parent / "pdf_extractor_data" / "images"
    
    if not images_dir.exists():
        print(f"❌ 图像目录不存在: {images_dir}")
        return False
        
    # 获取前几个图像文件
    image_files = list(images_dir.glob("*.png"))[:3]  # 只测试前3个图像
    
    if not image_files:
        print("❌ 没有找到图像文件")
        return False
        
    print(f"找到 {len(image_files)} 个图像文件")
    
    # 使用本地模型路径
    model_path = str(Path(__file__).parent.parent / "math_formula_test" / "models" / "unimernet_base")
    
    try:
        from mineru.model.mfr.unimernet.unimernet_hf.modeling_unimernet import UnimernetModel
        
        print("加载UnimerNet模型...")
        model = UnimernetModel.from_checkpoint(model_path, "pytorch_model.pth")
        print("✅ 模型加载成功!")
        
        for i, image_file in enumerate(image_files):
            print(f"\n--- 测试图像 {i+1}: {image_file.name} ---")
            
            try:
                # 加载图像
                image = Image.open(image_file)
                print(f"图像大小: {image.size}")
                
                # 预处理
                transform = model.transform
                processed_image = transform(image)
                if len(processed_image.shape) == 3:
                    processed_image = processed_image.unsqueeze(0)
                    
                sample = {"image": processed_image}
                
                # 识别
                with torch.no_grad():
                    result = model.generate(sample)
                    
                if isinstance(result, dict) and 'fixed_str' in result:
                    formulas = result['fixed_str']
                    print(f"识别结果: {formulas}")
                else:
                    print(f"结果格式: {result}")
                    
            except Exception as e:
                print(f"❌ 图像 {image_file.name} 处理失败: {e}")
                continue
                
        return True
        
    except Exception as e:
        print(f"❌ 批量测试失败: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("UnimerNet 公式识别测试工具")
    print("=" * 50)
    
    # 基本功能测试
    test_formula_recognition()
    
    # 使用实际PDF图像测试
    test_with_pdf_images() 