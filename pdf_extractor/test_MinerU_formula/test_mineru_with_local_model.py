#!/usr/bin/env python3
"""
使用本地模型进行实际的公式识别测试
"""
import os
import sys
import traceback
from pathlib import Path
from PIL import Image
import torch

# 设置环境变量使用本地模型
os.environ['MINERU_MODEL_SOURCE'] = 'local'

# 添加 MinerU 路径
project_root = Path(__file__).parent.parent.parent
mineru_path = project_root / "pdf_extractor/pdf_extractor_MinerU"
sys.path.insert(0, str(mineru_path))

def test_formula_recognition_with_local_model():
    """使用本地模型进行公式识别测试"""
    print("=== 使用本地模型进行公式识别测试 ===")
    
    try:
        from mineru.model.mfr.unimernet.Unimernet import UnimernetModel
        
        # 使用我们设置的本地模型路径
        model_path = "/Users/wukunhuan/.local/bin/pdf_extractor/models/MFR/unimernet_hf_small_2503"
        
        print(f"加载模型从: {model_path}")
        
        # 初始化模型
        model = UnimernetModel(model_path, _device_="cpu")
        print(f"✅ 模型加载成功")
        
        # 测试图像路径
        test_images = [
            Path("formula.png"),
            Path("matrix.png"),
            Path("table.png")
        ]
        
        results = {}
        
        for img_path in test_images:
            if not img_path.exists():
                print(f"⚠️ 图像文件不存在: {img_path}")
                continue
                
            print(f"\n--- 测试图像: {img_path} ---")
            
            try:
                # 加载图像
                image = Image.open(img_path)
                print(f"图像尺寸: {image.size}")
                
                # 预处理图像
                transform = model.model.transform
                processed_image = transform(image)
                
                # 添加batch维度
                if len(processed_image.shape) == 3:
                    processed_image = processed_image.unsqueeze(0)
                    
                sample = {"image": processed_image}
                
                # 进行推理
                print("开始识别...")
                with torch.no_grad():
                    result = model.model.generate(sample)
                    
                # 提取结果
                if isinstance(result, dict) and 'fixed_str' in result:
                    formulas = result['fixed_str']
                    if isinstance(formulas, list) and len(formulas) > 0:
                        formula_result = formulas[0]
                    else:
                        formula_result = str(formulas)
                else:
                    formula_result = str(result)
                
                print(f"✅ 识别结果: {formula_result}")
                results[str(img_path)] = formula_result
                
            except Exception as e:
                print(f"❌ 图像 {img_path} 识别失败: {e}")
                traceback.print_exc()
                results[str(img_path)] = None
        
        # 保存结果
        import json
        with open('local_model_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n=== 测试完成 ===")
        print(f"结果已保存到: local_model_test_results.json")
        
        # 显示总结
        print("\n=== 识别结果总结 ===")
        success_count = 0
        for img_path, result in results.items():
            if result:
                success_count += 1
                print(f"✅ {img_path}: {result[:100]}...")
            else:
                print(f"❌ {img_path}: 识别失败")
        
        print(f"\n成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("MinerU 本地模型公式识别测试")
    print("=" * 50)
    
    success = test_formula_recognition_with_local_model()
    
    if success:
        print("\n🎉 本地模型配置成功！MinerU 可以正确使用本地 UnimerNet 模型进行公式识别。")
    else:
        print("\n❌ 测试失败，需要进一步调试。")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 