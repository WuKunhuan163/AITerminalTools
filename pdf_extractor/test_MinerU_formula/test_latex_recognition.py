#!/usr/bin/env python3
"""
使用LaTeX生成的图像测试UnimerNet识别能力
"""
import sys
import os
import traceback
import torch
from pathlib import Path
from PIL import Image
import json

# 添加MinerU路径
sys.path.insert(0, str(Path(__file__).parent.parent / "pdf_extractor_MinerU"))

# 导入LaTeX生成器
from generate_latex_test_images import generate_all_test_images

def test_latex_image_recognition():
    """测试LaTeX生成图像的识别"""
    print("=== 测试LaTeX生成图像识别 ===")
    
    # 生成LaTeX图像
    latex_images = generate_all_test_images()
    
    if not latex_images:
        print("❌ 没有生成LaTeX图像，跳过测试")
        return False
    
    # 使用本地模型路径
    model_path = str(Path(__file__).parent.parent / "math_formula_test" / "models" / "unimernet_base")
    
    try:
        from mineru.model.mfr.unimernet.unimernet_hf.modeling_unimernet import UnimernetModel
        
        print("加载UnimerNet模型...")
        model = UnimernetModel.from_checkpoint(model_path, "pytorch_model.pth")
        print("✅ 模型加载成功!")
        
        results = []
        
        for image_type, image_path in latex_images:
            print(f"\n--- 测试 {image_type} ---")
            print(f"图像路径: {image_path}")
            
            try:
                # 加载图像
                image = Image.open(image_path)
                print(f"图像大小: {image.size}")
                
                # 预处理
                transform = model.transform
                processed_image = transform(image)
                if len(processed_image.shape) == 3:
                    processed_image = processed_image.unsqueeze(0)
                
                sample = {"image": processed_image}
                
                # 识别
                print("开始识别...")
                with torch.no_grad():
                    result = model.generate(sample)
                
                if isinstance(result, dict) and 'fixed_str' in result:
                    recognition_result = result['fixed_str'][0] if result['fixed_str'] else ""
                    
                    print(f"✅ 识别完成!")
                    print(f"识别结果: {recognition_result}")
                    
                    # 分析结果
                    analysis = analyze_recognition_result(recognition_result, image_type)
                    print(f"结果分析: {analysis}")
                    
                    results.append({
                        "type": image_type,
                        "image_path": str(image_path),
                        "recognition": recognition_result,
                        "analysis": analysis
                    })
                    
                else:
                    print(f"❌ 识别结果格式异常: {result}")
                    
            except Exception as e:
                print(f"❌ 处理 {image_type} 时出错: {e}")
                continue
        
        # 保存结果
        results_file = Path(__file__).parent / "latex_recognition_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {results_file}")
        
        # 总结
        print(f"\n=== 测试总结 ===")
        print(f"测试图像数: {len(latex_images)}")
        print(f"成功识别数: {len(results)}")
        
        for result in results:
            print(f"\n{result['type']}:")
            print(f"  识别质量: {result['analysis']['quality']}")
            print(f"  结构正确: {result['analysis']['structure_correct']}")
            print(f"  内容准确: {result['analysis']['content_accurate']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()
        return False

def analyze_recognition_result(result, expected_type):
    """分析识别结果的质量"""
    analysis = {
        "quality": "未知",
        "structure_correct": False,
        "content_accurate": False,
        "details": []
    }
    
    if not result:
        analysis["quality"] = "失败"
        analysis["details"].append("识别结果为空")
        return analysis
    
    # 根据预期类型分析
    if expected_type == "表格":
        # 检查表格结构
        has_tabular = any(marker in result for marker in ['\\begin{tabular}', '\\begin{array}'])
        has_separators = '&' in result
        has_rows = '\\\\' in result
        
        analysis["structure_correct"] = has_tabular or (has_separators and has_rows)
        
        # 检查内容
        expected_content = ['x', 'y', 'z', '1', '2', '3', '4', '5', '6', 'alpha', 'beta', 'gamma']
        content_matches = sum(1 for content in expected_content if content.lower() in result.lower())
        analysis["content_accurate"] = content_matches >= len(expected_content) * 0.5
        
        analysis["details"].append(f"表格标记: {has_tabular}")
        analysis["details"].append(f"分隔符: {has_separators}")
        analysis["details"].append(f"行标记: {has_rows}")
        analysis["details"].append(f"内容匹配: {content_matches}/{len(expected_content)}")
        
    elif expected_type == "公式":
        # 检查公式结构
        has_math_env = any(env in result for env in ['\\begin{align}', '\\begin{equation}', '$'])
        has_math_symbols = any(sym in result for sym in ['=', '^', '_', '\\int', '\\sum', '\\frac', '\\sqrt'])
        
        analysis["structure_correct"] = has_math_env or has_math_symbols
        
        # 检查特定公式内容
        expected_formulas = ['E', 'mc', 'int', 'infty', 'sum', 'pi']
        formula_matches = sum(1 for formula in expected_formulas if formula in result)
        analysis["content_accurate"] = formula_matches >= len(expected_formulas) * 0.3
        
        analysis["details"].append(f"数学环境: {has_math_env}")
        analysis["details"].append(f"数学符号: {has_math_symbols}")
        analysis["details"].append(f"公式匹配: {formula_matches}/{len(expected_formulas)}")
        
    elif expected_type == "矩阵":
        # 检查矩阵结构
        has_matrix = any(matrix in result for matrix in ['\\begin{pmatrix}', '\\begin{matrix}', '\\begin{bmatrix}'])
        has_separators = '&' in result
        has_rows = '\\\\' in result
        
        analysis["structure_correct"] = has_matrix or (has_separators and has_rows)
        
        # 检查矩阵内容
        expected_vars = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'x', 'y', 'z']
        var_matches = sum(1 for var in expected_vars if var in result)
        analysis["content_accurate"] = var_matches >= len(expected_vars) * 0.4
        
        analysis["details"].append(f"矩阵标记: {has_matrix}")
        analysis["details"].append(f"分隔符: {has_separators}")
        analysis["details"].append(f"行标记: {has_rows}")
        analysis["details"].append(f"变量匹配: {var_matches}/{len(expected_vars)}")
    
    # 总体质量评估
    if analysis["structure_correct"] and analysis["content_accurate"]:
        analysis["quality"] = "优秀"
    elif analysis["structure_correct"] or analysis["content_accurate"]:
        analysis["quality"] = "良好"
    else:
        analysis["quality"] = "一般"
    
    return analysis

if __name__ == "__main__":
    print("LaTeX图像识别测试工具")
    print("=" * 60)
    
    test_latex_image_recognition()
    
    print("\n测试完成！") 