#!/usr/bin/env python3
"""
Analyze PDF content to categorize images, tables, and formulas using MinerU middle.json
"""

import sys
import os
import time
import json
import re
from pathlib import Path

# Add the pdf_extractor directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from mineru_wrapper import MinerUWrapper

def find_middle_file(temp_dir):
    """Find the middle.json file in MinerU output directory"""
    temp_path = Path(temp_dir)
    
    # Search for middle.json files recursively
    for middle_file in temp_path.rglob("*middle.json"):
        return str(middle_file)
    
    return None

def analyze_middle_file(middle_file_path):
    """Analyze the middle.json file to categorize content types"""
    
    try:
        with open(middle_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading middle file: {e}")
        return None
    
    # Initialize counters
    content_stats = {
        'images': [],
        'tables': [],
        'interline_equations': [],
        'inline_equations': [],
        'total_blocks': 0
    }
    
    # Extract pdf_info
    pdf_info = data.get('pdf_info', [])
    
    for page_idx, page_data in enumerate(pdf_info):
        page_num = page_idx + 1
        preproc_blocks = page_data.get('preproc_blocks', [])
        
        print(f"📄 Analyzing page {page_num}: {len(preproc_blocks)} blocks")
        
        for block_idx, block in enumerate(preproc_blocks):
            content_stats['total_blocks'] += 1
            block_type = block.get('type', 'unknown')
            
            if block_type == 'image':
                content_stats['images'].append({
                    'page': page_num,
                    'block_idx': block_idx,
                    'bbox': block.get('bbox', []),
                    'type': 'image'
                })
            elif block_type == 'table':
                content_stats['tables'].append({
                    'page': page_num,
                    'block_idx': block_idx,
                    'bbox': block.get('bbox', []),
                    'type': 'table'
                })
            elif block_type == 'interline_equation':
                content_stats['interline_equations'].append({
                    'page': page_num,
                    'block_idx': block_idx,
                    'bbox': block.get('bbox', []),
                    'type': 'interline_equation'
                })
            elif block_type == 'inline_equation':
                content_stats['inline_equations'].append({
                    'page': page_num,
                    'block_idx': block_idx,
                    'bbox': block.get('bbox', []),
                    'type': 'inline_equation'
                })
    
    return content_stats

def main():
    """Main function to analyze PDF content"""
    
    # Test PDF path
    test_pdf = "/Users/wukunhuan/Desktop/GaussianObject/paper/GaussianObject High-Quality 3D Object Reconstruction from Four Views with Gaussian Splatting.pdf"
    
    if not os.path.exists(test_pdf):
        print(f"❌ Test PDF not found: {test_pdf}")
        return
    
    print(f"🔍 Analyzing PDF: {test_pdf}")
    print(f"📄 Page range: 4-5")
    print("-" * 50)
    
    # Initialize MinerU wrapper
    wrapper = MinerUWrapper()
    
    print("🔄 Extracting PDF content with MinerU...")
    start_time = time.time()
    
    try:
        # Extract using MinerU
        result = wrapper.extract_and_analyze_pdf(
            pdf_path=test_pdf,
            layout_mode="arxiv",
            mode="academic",
            call_api=False,
            call_api_force=False,
            page_range="4-5",
            debug=True
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"✅ Extraction completed in {processing_time:.2f} seconds")
        print(f"📁 Output file: {result}")
        
        # Find the middle file
        middle_file = find_middle_file(wrapper.temp_dir)
        
        if middle_file:
            print(f"📋 Found middle file: {middle_file}")
            
            # Analyze the middle file
            content_stats = analyze_middle_file(middle_file)
            
            if content_stats:
                print("-" * 50)
                print("📊 CONTENT ANALYSIS FROM MIDDLE FILE")
                print("=" * 50)
                
                print(f"\n🖼️  ACTUAL IMAGES: {len(content_stats['images'])} found")
                for i, img in enumerate(content_stats['images'], 1):
                    print(f"  {i}. Page {img['page']}, Block {img['block_idx']}")
                
                print(f"\n📋 TABLES: {len(content_stats['tables'])} found")
                for i, table in enumerate(content_stats['tables'], 1):
                    print(f"  {i}. Page {table['page']}, Block {table['block_idx']}")
                
                print(f"\n🔢 INTERLINE EQUATIONS: {len(content_stats['interline_equations'])} found")
                for i, eq in enumerate(content_stats['interline_equations'], 1):
                    print(f"  {i}. Page {eq['page']}, Block {eq['block_idx']}")
                
                print(f"\n🔢 INLINE EQUATIONS: {len(content_stats['inline_equations'])} found")
                for i, eq in enumerate(content_stats['inline_equations'], 1):
                    print(f"  {i}. Page {eq['page']}, Block {eq['block_idx']}")
                
                print(f"\n📊 TOTAL BLOCKS ANALYZED: {content_stats['total_blocks']}")
                
                # Save detailed analysis
                analysis_file = result.replace('.md', '_detailed_analysis.json')
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    json.dump(content_stats, f, indent=2, ensure_ascii=False)
                
                print("=" * 50)
                print("📈 SUMMARY")
                print("=" * 50)
                print(f"📄 Pages analyzed: 4-5")
                print(f"🖼️  Actual images: {len(content_stats['images'])}")
                print(f"📋 Tables: {len(content_stats['tables'])}")
                print(f"🔢 Interline equations: {len(content_stats['interline_equations'])}")
                print(f"🔢 Inline equations: {len(content_stats['inline_equations'])}")
                print(f"⏱️  Processing time: {processing_time:.2f} seconds")
                print(f"💾 Detailed analysis saved to: {analysis_file}")
                
            else:
                print("❌ Failed to analyze middle file")
        else:
            print("❌ Middle file not found in MinerU output")
            
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Analysis completed successfully!")

if __name__ == "__main__":
    main() 