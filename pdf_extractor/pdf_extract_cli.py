#!/usr/bin/env python3
"""
PDF_EXTRACT Command Line Interface
Usage: python pdf_extract_cli.py [PDF_PATH] [OPTIONS]
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from pdf_extractor import extract_and_analyze_pdf
from mineru_wrapper import extract_and_analyze_pdf_with_mineru, MinerUWrapper
import json
import time


def get_pdf_path_interactive():
    """Get PDF path using tkinter file dialog."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # Create root window and hide it
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        # Open file dialog
        pdf_path = filedialog.askopenfilename(
            title="Choose the PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        root.destroy()
        return pdf_path
        
    except ImportError:
        print("❌ tkinter not available. Please provide PDF path as argument.")
        return None


def get_interactive_options():
    """Get processing options interactively."""
    print("\n" + "="*50)
    print("PDF EXTRACTION OPTIONS")
    print("="*50)
    
    # Get page range
    page_range = input("Enter page range (e.g., '1-5', '1,3,5', or press Enter for all pages): ").strip()
    if not page_range:
        page_range = None
    
    # Get image API option
    print("\nImage Analysis Options:")
    print("1. Enable image analysis (default)")
    print("2. Disable image analysis (faster)")
    print("3. Force image analysis (ignore cache)")
    
    api_choice = input("Choose image analysis option (1-3, default: 1): ").strip()
    
    if api_choice == "2":
        call_api = False
        call_api_force = False
    elif api_choice == "3":
        call_api = True
        call_api_force = True
    else:
        call_api = True
        call_api_force = False
    
    # Get debug option
    debug = input("Enable debug mode? (y/n, default: n): ").strip().lower() == 'y'
    
    # Get MinerU option
    print("\nPDF Extraction Engine:")
    print("1. Original PDF extractor (default)")
    print("2. MinerU (experimental)")
    engine_choice = input("Choose extraction engine (1-2, default: 1): ").strip()
    use_mineru = engine_choice == "2"
    
    return page_range, call_api, call_api_force, debug, use_mineru


def find_middle_file(temp_dir):
    """Find the middle.json file in MinerU output directory"""
    temp_path = Path(temp_dir)
    
    # Search for middle.json files recursively
    for middle_file in temp_path.rglob("*middle.json"):
        return str(middle_file)
    
    return None


def analyze_content_types(middle_file_path):
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


def print_content_analysis(content_stats):
    """Print formatted content analysis results"""
    if not content_stats:
        return
    
    print("\n" + "="*50)
    print("📊 CONTENT ANALYSIS RESULTS")
    print("="*50)
    
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
    print("="*50)


def main():
    """Main CLI entry point for PDF_EXTRACT command."""
    
    # Check if PDF path is provided
    if len(sys.argv) < 2:
        print("🔍 No PDF path provided. Opening file selector...")
        pdf_path = get_pdf_path_interactive()
        
        if not pdf_path:
            print("❌ No PDF selected. Exiting.")
            sys.exit(1)
        
        print(f"📄 Selected PDF: {pdf_path}")
        
        # Get options interactively
        page_range, call_api, call_api_force, debug, use_mineru = get_interactive_options()
        
        # Set defaults for other options
        layout_mode = "arxiv"
        mode = "academic"
        
    else:
        # Get PDF path from command line
        pdf_path = sys.argv[1]
        
        # Parse command line options
        page_range = None
        call_api = True
        call_api_force = False
        debug = False
        layout_mode = "arxiv"
        mode = "academic"
        use_mineru = False
        
        # Process command line arguments
        i = 2
        while i < len(sys.argv):
            arg = sys.argv[i]
            
            if arg == "--no-image-api":
                call_api = False
            elif arg == "--image-api":
                call_api = True
            elif arg == "--image-api-force":
                call_api_force = True
            elif arg == "--page" and i + 1 < len(sys.argv):
                page_range = sys.argv[i + 1]
                i += 1
            elif arg == "--debug":
                debug = True
            elif arg == "--layout-mode" and i + 1 < len(sys.argv):
                layout_mode = sys.argv[i + 1]
                i += 1
            elif arg == "--mode" and i + 1 < len(sys.argv):
                mode = sys.argv[i + 1]
                i += 1
            elif arg == "--use-mineru":
                use_mineru = True
            
            i += 1

    
    # Execute PDF extraction
    try:
        start_time = time.time()
        
        if use_mineru:
            print("🔄 Using MinerU for PDF extraction...")
            
            # Use the wrapper function with proper error handling
            result_path = extract_and_analyze_pdf_with_mineru(
                pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug
            )
            
            # Try to perform content analysis if MinerU was used successfully
            # Check if the result came from MinerU (not fallback) by looking for temp directories
            mineru_temp_dirs = [d for d in os.listdir('/var/folders/w0/m02j_xv925sg34708rb2xgzr0000gn/T/') 
                              if d.startswith('mineru_output_')]
            
            if mineru_temp_dirs:
                # Use the most recent temp directory
                latest_temp = max(mineru_temp_dirs, key=lambda x: os.path.getctime(f'/var/folders/w0/m02j_xv925sg34708rb2xgzr0000gn/T/{x}'))
                temp_dir = f'/var/folders/w0/m02j_xv925sg34708rb2xgzr0000gn/T/{latest_temp}'
                
                middle_file = find_middle_file(temp_dir)
                if middle_file:
                    print(f"📋 Analyzing content types from: {middle_file}")
                    content_stats = analyze_content_types(middle_file)
                    if content_stats:
                        print_content_analysis(content_stats)
                        
                        # Save analysis results
                        analysis_file = result_path.replace('.md', '_content_analysis.json')
                        with open(analysis_file, 'w', encoding='utf-8') as f:
                            json.dump(content_stats, f, indent=2, ensure_ascii=False)
                        print(f"💾 Content analysis saved to: {analysis_file}")
                else:
                    print("⚠️  Could not find middle.json file for content analysis")
            else:
                print("ℹ️  MinerU likely fell back to original extractor, no content analysis available")
        else:
            print("🔄 Using original PDF extractor...")
            result_path = extract_and_analyze_pdf(
                pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug
            )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"\n✅ SUCCESS: PDF extracted to {result_path}")
        print(f"⏱️  Total processing time: {processing_time:.2f} seconds")
        return 0
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 