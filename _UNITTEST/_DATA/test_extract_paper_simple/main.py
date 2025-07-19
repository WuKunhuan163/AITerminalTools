#!/usr/bin/env python3
"""
Enhanced PDF Formula Testing Pipeline
Tests UnimerNet model loading and processes 5 test PDFs to generate markdown output.
Combines functionality from test_unimernet_direct.py and test_content_extraction.py.
"""

import os
import json
import sys
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add MinerU path for UnimerNet import
sys.path.insert(0, str(Path(__file__).parent.parent / "pdf_extractor_MinerU"))

def test_unimernet_model_loading():
    """Test UnimerNet model loading (from test_unimernet_direct.py)"""
    print("🧪 Testing UnimerNet model loading...")
    
    try:
        from mineru.model.mfr.unimernet.Unimernet import UnimernetModel
        print("  ✅ Successfully imported UnimernetModel")
        
        # Try to load the model
        model_path = Path(__file__).parent.parent / "models" / "MFR" / "unimernet_hf_small_2503"
        if model_path.exists():
            print(f"  ✅ Model path exists: {model_path}")
            
            # Try to create model instance
            model = UnimernetModel(str(model_path), "cpu")
            print("  ✅ UnimerNet model loaded successfully!")
            
            # Test with an image
            test_image_path = "test1_data/images/405b819b14936c78a5cec55aafd90a4d01bfec70a20669c243f018728cb4c1a4.jpg"
            if Path(test_image_path).exists():
                print(f"  ✅ Test image exists: {test_image_path}")
                print("  📝 Model loaded successfully, ready for formula extraction")
                return True
            else:
                print(f"  ❌ Test image not found: {test_image_path}")
                return False
        else:
            print(f"  ❌ Model path not found: {model_path}")
            return False
            
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def run_pdf_extract_on_pdf(pdf_path: str, output_name: str) -> bool:
    """Run PDF extraction on a single PDF file"""
    try:
        print(f"  🔄 Processing {pdf_path} → {output_name}")
        
        # Change to parent directory to run the extraction
        parent_dir = Path(__file__).parent.parent
        cmd = [
            '/usr/bin/python3',
            'pdf_extract_cli.py',
            f'test_unimernet_formula/{pdf_path}',
            '--engine', '1',  # Use MinerU-async
            '--no-image-api'
        ]
        
        result = subprocess.run(cmd, cwd=parent_dir, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✅ PDF extraction successful for {pdf_path}")
            return True
        else:
            print(f"  ❌ PDF extraction failed for {pdf_path}")
            print(f"  Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ❌ Exception during PDF extraction: {e}")
        return False

def find_generated_markdown(pdf_name: str) -> Optional[str]:
    """Find the generated markdown file for a PDF"""
    base_name = os.path.splitext(pdf_name)[0]
    
    # Look in the data directory
    data_dir = f"{base_name}_data"
    if os.path.exists(data_dir):
        # Check for markdown files directly in data directory
        for file in os.listdir(data_dir):
            if file.endswith('.md'):
                return os.path.join(data_dir, file)
        
        # Check for markdown subdirectory
        markdown_dir = os.path.join(data_dir, "markdown")
        if os.path.exists(markdown_dir):
            # Look for markdown files
            for file in os.listdir(markdown_dir):
                if file.endswith('.md'):
                    return os.path.join(markdown_dir, file)
    
    return None

def find_generated_markdown_after_time(pdf_name: str, start_time: float) -> Optional[str]:
    """Find the generated markdown file for a PDF created after start_time"""
    # First try the standard location
    markdown_path = find_generated_markdown(pdf_name)
    if markdown_path:
        return markdown_path
    
    # Also check the parent directory's markdown folder for recently created files
    parent_markdown_dir = "../pdf_extractor_data/markdown"
    if os.path.exists(parent_markdown_dir):
        # Get all markdown files created after start_time
        recent_md_files = []
        for file in os.listdir(parent_markdown_dir):
            if file.endswith('.md'):
                full_path = os.path.join(parent_markdown_dir, file)
                file_mtime = os.path.getmtime(full_path)
                if file_mtime > start_time:
                    recent_md_files.append((full_path, file_mtime))
        
        if recent_md_files:
            # Return the most recently created markdown file
            recent_md_files.sort(key=lambda x: x[1], reverse=True)
            return recent_md_files[0][0]
    
    return None

def copy_and_rename_markdown(src_path: str, dst_name: str) -> bool:
    """Copy and rename markdown file to current directory"""
    try:
        import shutil
        shutil.copy2(src_path, dst_name)
        print(f"  📄 Markdown saved as: {dst_name}")
        return True
    except Exception as e:
        print(f"  ❌ Error copying markdown: {e}")
        return False

def find_middle_json_for_pdf(pdf_name: str) -> Optional[str]:
    """Find the middle.json file for a given PDF"""
    base_name = os.path.splitext(pdf_name)[0]
    
    # Look in the data directory
    data_dir = f"{base_name}_data"
    if os.path.exists(data_dir):
        middle_json_path = os.path.join(data_dir, f"{base_name}_middle.json")
        if os.path.exists(middle_json_path):
            return middle_json_path
    
    return None

def analyze_middle_json(middle_json_path: str) -> Dict:
    """Analyze middle.json file to extract content information"""
    try:
        with open(middle_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        analysis = {
            'tables': 0,
            'formulas': 0,
            'images': 0,
            'total_pages': 0,
            'details': []
        }
        
        pdf_info = data.get('pdf_info', [])
        analysis['total_pages'] = len(pdf_info)
        
        for page_idx, page_data in enumerate(pdf_info):
            preproc_blocks = page_data.get('preproc_blocks', [])
            page_content = {
                'page': page_idx,
                'tables': 0,
                'formulas': 0,
                'images': 0
            }
            
            for block in preproc_blocks:
                block_type = block.get('type', '')
                
                if block_type == 'table':
                    page_content['tables'] += 1
                    analysis['tables'] += 1
                elif block_type == 'interline_equation':
                    page_content['formulas'] += 1
                    analysis['formulas'] += 1
                elif block_type == 'image':
                    page_content['images'] += 1
                    analysis['images'] += 1
            
            analysis['details'].append(page_content)
        
        return analysis
        
    except Exception as e:
        print(f"  ❌ Error analyzing middle.json: {e}")
        return {'error': str(e)}

def process_single_pdf(pdf_path: str) -> Dict:
    """Process a single PDF file and generate markdown output"""
    base_name = os.path.splitext(pdf_path)[0]
    result = {
        'pdf': pdf_path,
        'base_name': base_name,
        'extraction_success': False,
        'markdown_path': None,
        'analysis': None
    }
    
    print(f"\n📄 Processing {pdf_path}")
    
    # Step 1: Record current time to find newly generated files
    import time
    start_time = time.time()
    
    # Step 2: Run PDF extraction
    extraction_success = run_pdf_extract_on_pdf(pdf_path, base_name)
    result['extraction_success'] = extraction_success
    
    if not extraction_success:
        result['error'] = 'PDF extraction failed'
        return result
    
    # Step 3: Find generated markdown (look for files created after start_time)
    markdown_path = find_generated_markdown_after_time(pdf_path, start_time)
    if markdown_path:
        # Copy to current directory with new name
        new_markdown_name = f"{base_name}_test.md"
        if copy_and_rename_markdown(markdown_path, new_markdown_name):
            result['markdown_path'] = new_markdown_name
    
    # Step 4: Analyze middle.json if available
    middle_json_path = find_middle_json_for_pdf(pdf_path)
    if middle_json_path:
        print(f"  📁 Found middle.json: {middle_json_path}")
        analysis = analyze_middle_json(middle_json_path)
        result['analysis'] = analysis
    
    return result

def main():
    """Main function to test UnimerNet and process all test PDFs"""
    print("🚀 Starting Enhanced PDF Formula Testing Pipeline...")
    
    # Step 1: Test UnimerNet model loading
    model_test_success = test_unimernet_model_loading()
    
    # Step 2: Find all test PDF files
    test_pdfs = []
    for i in range(1, 6):  # test1.pdf to test5.pdf
        pdf_name = f"test{i}.pdf"
        if os.path.exists(pdf_name):
            test_pdfs.append(pdf_name)
    
    if not test_pdfs:
        print("❌ No test PDF files found!")
        return
    
    test_pdfs.sort()
    print(f"📁 Found {len(test_pdfs)} test PDF files: {test_pdfs}")
    
    # Step 3: Process each PDF
    all_results = []
    
    for pdf_file in test_pdfs:
        result = process_single_pdf(pdf_file)
        all_results.append(result)
    
    # Step 4: Print comprehensive summary
    print("\n" + "="*60)
    print("📊 PROCESSING SUMMARY")
    print("="*60)
    
    print(f"🧪 UnimerNet Model Test: {'✅ PASSED' if model_test_success else '❌ FAILED'}")
    print(f"📄 Total PDFs processed: {len(all_results)}")
    
    successful_extractions = 0
    generated_markdowns = 0
    
    for result in all_results:
        print(f"\n📄 {result['pdf']}:")
        
        if result['extraction_success']:
            print(f"  ✅ Extraction: SUCCESS")
            successful_extractions += 1
            
            if result['markdown_path']:
                print(f"  📝 Markdown: {result['markdown_path']}")
                generated_markdowns += 1
            else:
                print(f"  ❌ Markdown: Not found")
            
            if result['analysis'] and 'error' not in result['analysis']:
                analysis = result['analysis']
                print(f"  📊 Content Analysis:")
                print(f"    - Pages: {analysis['total_pages']}")
                print(f"    - Tables: {analysis['tables']}")
                print(f"    - Formulas: {analysis['formulas']}")
                print(f"    - Images: {analysis['images']}")
                
                # Show page-by-page breakdown
                for page_info in analysis['details']:
                    if page_info['tables'] > 0 or page_info['formulas'] > 0 or page_info['images'] > 0:
                        print(f"      Page {page_info['page']}: T:{page_info['tables']} F:{page_info['formulas']} I:{page_info['images']}")
            else:
                print(f"  ❌ Analysis: Failed")
        else:
            print(f"  ❌ Extraction: FAILED")
            if 'error' in result:
                print(f"    Error: {result['error']}")
    
    print(f"\n🎉 Processing Complete!")
    print(f"✅ Successful extractions: {successful_extractions}/{len(all_results)}")
    print(f"📝 Generated markdowns: {generated_markdowns}/{len(all_results)}")
    
    if model_test_success:
        print(f"🧪 UnimerNet model is ready for formula extraction!")
    else:
        print(f"❌ UnimerNet model test failed - check model installation")
    
    print(f"\n📁 Generated files in current directory:")
    for result in all_results:
        if result['markdown_path']:
            print(f"  - {result['markdown_path']}")

if __name__ == "__main__":
    main() 