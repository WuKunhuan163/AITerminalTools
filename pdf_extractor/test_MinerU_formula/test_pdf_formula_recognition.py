#!/usr/bin/env python3
"""
完整的PDF公式识别测试脚本
"""
import sys
import os
import traceback
import torch
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF
import json

# 添加MinerU路径
sys.path.insert(0, str(Path(__file__).parent.parent / "pdf_extractor_MinerU"))

def extract_pdf_pages(pdf_path, start_page=0, end_page=None):
    """从PDF提取页面图像"""
    doc = fitz.open(pdf_path)
    pages = []
    
    if end_page is None:
        end_page = len(doc)
    
    for page_num in range(start_page, min(end_page, len(doc))):
        page = doc[page_num]
        # 获取页面的图像
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x缩放以提高质量
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append((page_num, img))
    
    doc.close()
    return pages

def detect_formula_regions(image, model):
    """检测图像中的公式区域（简化版）"""
    # 这里我们简化处理，直接使用整个图像
    # 在实际应用中，应该使用MFD模型来检测公式区域
    regions = [(0, 0, image.width, image.height)]
    return regions

def recognize_formulas_in_image(image, model):
    """识别图像中的公式"""
    try:
        # 预处理图像
        transform = model.transform
        processed_image = transform(image)
        
        if len(processed_image.shape) == 3:
            processed_image = processed_image.unsqueeze(0)
            
        sample = {"image": processed_image}
        
        # 识别公式
        with torch.no_grad():
            result = model.generate(sample)
            
        if isinstance(result, dict) and 'fixed_str' in result:
            return result['fixed_str']
        else:
            return []
            
    except Exception as e:
        print(f"识别公式时出错: {e}")
        return []

def test_pdf_formula_recognition(pdf_path, output_path=None):
    """测试PDF公式识别"""
    print(f"=== 测试PDF公式识别: {pdf_path} ===")
    
    # 使用本地模型路径
    model_path = str(Path(__file__).parent.parent / "math_formula_test" / "models" / "unimernet_base")
    
    try:
        from mineru.model.mfr.unimernet.unimernet_hf.modeling_unimernet import UnimernetModel
        
        print("加载UnimerNet模型...")
        model = UnimernetModel.from_checkpoint(model_path, "pytorch_model.pth")
        print("✅ 模型加载成功!")
        
        # 提取PDF页面
        print("提取PDF页面...")
        pages = extract_pdf_pages(pdf_path, start_page=0, end_page=3)  # 只测试前3页
        print(f"提取了 {len(pages)} 个页面")
        
        results = []
        
        for page_num, page_image in pages:
            print(f"\n--- 处理第 {page_num + 1} 页 ---")
            print(f"页面大小: {page_image.size}")
            
            # 识别公式
            formulas = recognize_formulas_in_image(page_image, model)
            
            page_result = {
                "page": page_num + 1,
                "formulas": formulas,
                "formula_count": len(formulas)
            }
            
            results.append(page_result)
            
            print(f"识别到 {len(formulas)} 个公式:")
            for i, formula in enumerate(formulas):
                print(f"  公式 {i+1}: {formula}")
        
        # 保存结果
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {output_path}")
        
        # 统计信息
        total_formulas = sum(result["formula_count"] for result in results)
        print(f"\n=== 统计信息 ===")
        print(f"总页数: {len(pages)}")
        print(f"总公式数: {total_formulas}")
        print(f"平均每页公式数: {total_formulas / len(pages):.1f}")
        
        return results
        
    except Exception as e:
        print(f"❌ PDF公式识别失败: {e}")
        traceback.print_exc()
        return None

def test_with_demo_pdfs():
    """使用demo PDF进行测试"""
    print("\n=== 使用Demo PDF测试 ===")
    
    # 查找demo PDF文件
    demo_dir = Path(__file__).parent.parent / "pdf_extractor_MinerU" / "demo" / "pdfs"
    
    if not demo_dir.exists():
        print(f"❌ Demo目录不存在: {demo_dir}")
        return
        
    pdf_files = list(demo_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ 没有找到PDF文件")
        return
        
    print(f"找到 {len(pdf_files)} 个PDF文件")
    
    for pdf_file in pdf_files[:2]:  # 只测试前2个PDF
        print(f"\n{'='*60}")
        output_path = Path(__file__).parent / f"{pdf_file.stem}_formula_results.json"
        test_pdf_formula_recognition(str(pdf_file), str(output_path))

if __name__ == "__main__":
    print("PDF公式识别测试工具")
    print("=" * 60)
    
    # 测试demo PDF
    test_with_demo_pdfs()
    
    print("\n测试完成！") 