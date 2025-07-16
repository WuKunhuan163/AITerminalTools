#!/usr/bin/env python3
"""
Test script for MinerU with image API enabled
"""

import sys
import os
from pathlib import Path

# Add the pdf_extractor directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from mineru_wrapper import extract_and_analyze_pdf_with_mineru

def test_mineru_with_api():
    """Test MinerU with image API enabled"""
    print("Testing MinerU with image API enabled...")
    
    # Test with a simple PDF
    test_pdf = "/Users/wukunhuan/Desktop/GaussianObject/paper/GaussianObject High-Quality 3D Object Reconstruction from Four Views with Gaussian Splatting.pdf"
    
    if not os.path.exists(test_pdf):
        print(f"Test PDF not found: {test_pdf}")
        return
    
    try:
        print("🔄 Testing with image API enabled...")
        result = extract_and_analyze_pdf_with_mineru(
            pdf_path=test_pdf,
            layout_mode="arxiv",
            mode="academic",
            call_api=True,  # Enable image analysis
            call_api_force=False,
            page_range="4-5",  # Test with pages 4-5
            debug=True
        )
        
        print(f"✅ MinerU with API test successful!")
        print(f"📄 Output file: {result}")
        
        # Check if the file exists and has content
        if os.path.exists(result):
            with open(result, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"📝 File size: {len(content)} characters")
                print(f"📝 First 200 characters:\n{content[:200]}...")
        else:
            print("❌ Output file not found")
            
    except Exception as e:
        print(f"❌ MinerU with API test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mineru_with_api() 