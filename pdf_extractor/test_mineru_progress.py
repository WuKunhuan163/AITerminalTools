#!/usr/bin/env python3
"""
Test script for improved MinerU processing with progress display
"""

import sys
import os
import time
from pathlib import Path

# Add the pdf_extractor directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from mineru_wrapper import extract_and_analyze_pdf_with_mineru

def test_mineru_progress():
    """Test improved MinerU processing with progress display"""
    print("Testing improved MinerU processing...")
    
    # Test with the same PDF
    test_pdf = "/Users/wukunhuan/Desktop/GaussianObject/paper/GaussianObject High-Quality 3D Object Reconstruction from Four Views with Gaussian Splatting.pdf"
    
    if not os.path.exists(test_pdf):
        print(f"Test PDF not found: {test_pdf}")
        return
    
    print("🧪 Testing with 3 pages (should be fast)...")
    start_time = time.time()
    try:
        result = extract_and_analyze_pdf_with_mineru(
            pdf_path=test_pdf,
            layout_mode="arxiv",
            mode="academic",
            call_api=False,
            call_api_force=False,
            page_range="1-3",  # Test with 3 pages
            debug=True
        )
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"✅ 3-page test successful!")
        print(f"📄 Output file: {result}")
        print(f"⏱️  Processing time: {elapsed_time:.2f} seconds")
        
        # Check file content
        if os.path.exists(result):
            with open(result, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"📝 File size: {len(content)} characters")
        
    except Exception as e:
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"❌ 3-page test failed after {elapsed_time:.2f} seconds: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*50)
    print("🧪 Testing with 10 pages (no timeout - use Ctrl+C to interrupt)...")
    start_time = time.time()
    try:
        result = extract_and_analyze_pdf_with_mineru(
            pdf_path=test_pdf,
            layout_mode="arxiv",
            mode="academic",
            call_api=False,
            call_api_force=False,
            page_range="1-10",  # Test with 10 pages
            debug=True
        )
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"✅ 10-page test successful!")
        print(f"📄 Output file: {result}")
        print(f"⏱️  Processing time: {elapsed_time:.2f} seconds")
        
        # Check file content
        if os.path.exists(result):
            with open(result, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"📝 File size: {len(content)} characters")
        
    except Exception as e:
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"❌ 10-page test failed after {elapsed_time:.2f} seconds: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mineru_progress() 