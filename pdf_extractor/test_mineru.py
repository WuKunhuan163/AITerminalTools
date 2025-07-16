#!/usr/bin/env python3
"""
Test script for MinerU integration
"""

import sys
import os
from pathlib import Path

# Add the pdf_extractor directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from mineru_wrapper import extract_and_analyze_pdf_with_mineru

def test_mineru():
    """Test MinerU integration with a simple call"""
    print("Testing MinerU integration...")
    
    # Test with a simple PDF (you can modify this path)
    test_pdf = "/Users/wukunhuan/Desktop/GaussianObject/paper/GaussianObject High-Quality 3D Object Reconstruction from Four Views with Gaussian Splatting.pdf"
    
    if not os.path.exists(test_pdf):
        print(f"Test PDF not found: {test_pdf}")
        print("Please update the test_pdf path in the script")
        return
    
    try:
        result = extract_and_analyze_pdf_with_mineru(
            pdf_path=test_pdf,
            layout_mode="arxiv",
            mode="academic",
            call_api=False,  # Disable image analysis for faster processing
            call_api_force=False,
            page_range="1",  # Only process first page
            debug=True
        )
        
        print(f"✅ MinerU test successful!")
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
        print(f"❌ MinerU test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mineru() 