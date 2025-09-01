#!/usr/bin/env python3
"""
PDF Extractor CLI - Command Line Interface for PDF extraction and analysis
"""

import os
import sys
import argparse
import json
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from pdf_extractor import extract_and_analyze_pdf
from mineru_wrapper import extract_and_analyze_pdf_with_mineru, MinerUWrapper
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
        print(f"Error:  tkinter not available. Please provide PDF path as argument.")
        return None


def get_interactive_options():
    """Get processing options interactively."""
    print(f"\n" + "="*22)
    print(f"PDF EXTRACTION OPTIONS")
    print(f"="*22)
    
    # Get page range
    page_range = input("Enter page range (e.g., '1-5', '1,3,5', or press Enter for all pages): ").strip()
    if not page_range:
        page_range = None
    
    # Unified PDF Extraction Engine options
    print(f"\nPDF Extraction Engine:")
    print(f"1. MinerU-async (no image/formula/table analysis)")
    print(f"2. MinerU (with image/formula/table analysis)")
    print(f"3. Basic-async (no image analysis)")
    print(f"4. Basic (with image analysis)")
    
    engine_choice = input("Choose extraction engine (1-4, default: 1): ").strip()
    
    # Set parameters based on choice
    if engine_choice == "1" or engine_choice == "":
        # MinerU-async (no image/formula/table analysis) - DEFAULT
        use_mineru = True
        async_mode = True
        call_api = False
        call_api_force = False
    elif engine_choice == "2":
        # MinerU with full analysis
        use_mineru = True
        async_mode = False
        call_api = True
        call_api_force = False
    elif engine_choice == "3":
        # Basic-async (no image analysis)
        use_mineru = False
        async_mode = False
        call_api = False
        call_api_force = False
    elif engine_choice == "4":
        # Basic with image analysis
        use_mineru = False
        async_mode = False
        call_api = True
        call_api_force = False
    else:
        # Default: MinerU-async
        use_mineru = True
        async_mode = True
        call_api = False
        call_api_force = False
    
    # Set debug to False (removed from interactive options)
    debug = False
    
    return page_range, call_api, call_api_force, debug, use_mineru, async_mode


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
        print(f"Error: Error reading middle file: {e}")
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
    
    print(f"\n" + "="*24)
    print(f"CONTENT ANALYSIS RESULTS")
    print(f"="*24)
    
    print(f"\n  ACTUAL IMAGES: {len(content_stats['images'])} found")
    for i, img in enumerate(content_stats['images'], 1):
        print(f"  {i}. Page {img['page']}, Block {img['block_idx']}")
    
    print(f"\nTABLES: {len(content_stats['tables'])} found")
    for i, table in enumerate(content_stats['tables'], 1):
        print(f"  {i}. Page {table['page']}, Block {table['block_idx']}")
    
    print(f"\nINTERLINE EQUATIONS: {len(content_stats['interline_equations'])} found")
    for i, eq in enumerate(content_stats['interline_equations'], 1):
        print(f"  {i}. Page {eq['page']}, Block {eq['block_idx']}")
    
    print(f"\nINLINE EQUATIONS: {len(content_stats['inline_equations'])} found")
    for i, eq in enumerate(content_stats['inline_equations'], 1):
        print(f"  {i}. Page {eq['page']}, Block {eq['block_idx']}")
    
    print(f"\nTOTAL BLOCKS ANALYZED: {content_stats['total_blocks']}")


def clean_data_directory():
    """Clean the UNIMERNET_DATA directory."""
    data_dir = Path(__file__).parent.parent / "UNIMERNET_DATA" / "pdf_extractor_data"
    
    if data_dir.exists():
        import shutil
        shutil.rmtree(data_dir)
        print(f"Cleaned data directory: {data_dir}")
    else:
        print(f"Data directory doesn't exist: {data_dir}")


def check_and_show_post_processing_status(result_path: str):
    """Check if post-processing is needed and show status from JSON file"""
    try:
        # Determine the PDF path and status file path
        result_path_obj = Path(result_path)
        
        # Try to find the PDF file and status file
        pdf_file = None
        status_file = None
        
        if result_path.endswith('.pdf'):
            # Input is PDF file
            pdf_file = result_path_obj
            status_file = result_path_obj.parent / f"{result_path_obj.stem}_postprocess.json"
        elif result_path.endswith('.md'):
            # Input is markdown file, try to find corresponding PDF
            md_stem = result_path_obj.stem
            # Remove page range suffix if present (e.g., "paper_p1-3" -> "paper")
            if '_p' in md_stem:
                pdf_stem = md_stem.split('_p')[0]
            else:
                pdf_stem = md_stem
            
            pdf_file = result_path_obj.parent / f"{pdf_stem}.pdf"
            status_file = result_path_obj.parent / f"{pdf_stem}_postprocess.json"
            
            # If PDF doesn't exist, try with the full stem
            if not pdf_file.exists():
                pdf_file = result_path_obj.parent / f"{md_stem}.pdf"
                status_file = result_path_obj.parent / f"{md_stem}_postprocess.json"
        
        # Check if status file exists
        if not status_file or not status_file.exists():
            # Try to regenerate status file from markdown if possible
            if result_path.endswith('.md') and result_path_obj.exists():
                print(f"Status file not exists, trying to regenerate from Markdown...")
                
                # Import MinerU wrapper to use regeneration function
                from mineru_wrapper import mineru_wrapper
                
                if pdf_file and pdf_file.exists():
                    regenerated_status = mineru_wrapper._regenerate_status_from_markdown(str(pdf_file), str(result_path_obj))
                    if regenerated_status:
                        status_file = Path(regenerated_status)
                    else:
                        print(f"No post-processing needed, no valid placeholder found")
                        return
                else:
                    print(f"No corresponding PDF file found, cannot regenerate status")
                    return
            else:
                print(f"No post-processing needed, no status file found")
                return
        
        # Read and display status from JSON file
        with open(status_file, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
        
        print(f"\n" + "="*50)
        print(f"Async processing status")
        print(f"="*50)
        
        # Display basic info
        print(f"PDF file: {status_data.get('pdf_file', 'Unknown')}")
        print(f"Created time: {status_data.get('created_at', 'Unknown')}")
        print(f"Total items: {status_data.get('total_items', 0)} items need post-processing")
        
        # Display counts
        counts = status_data.get('counts', {})
        if counts.get('images', 0) > 0:
            print(f"- Images: {counts['images']} items [need Google API processing]")
        if counts.get('formulas', 0) > 0:
            print(f"- Formulas: {counts['formulas']} items [need UnimerNet processing]")
        if counts.get('tables', 0) > 0:
            print(f"- Tables: {counts['tables']} items [need UnimerNet processing]")
        
        # Display processing commands
        commands = status_data.get('processing_commands', {})
        if commands:
            print(f"\n**Post-processing commands:**")
            if counts.get('images', 0) > 0:
                print(f"- Image analysis: `{commands.get('image_analysis', 'N/A')}`")
            if counts.get('formulas', 0) > 0:
                print(f"- Formula recognition: `{commands.get('formula_recognition', 'N/A')}`")
            if counts.get('tables', 0) > 0:
                print(f"- Table recognition: `{commands.get('table_recognition', 'N/A')}`")
            print(f"- All processing: `{commands.get('process_all', 'N/A')}`")
        
        # Display detailed item information if requested
        items = status_data.get('items', [])
        if items:
            print(f"\nStatus file location: {status_file}")
            print(f"Suggestion: You can edit the placeholder marker in the Markdown file to control the processing of this item")
            print(f"   - Remove [placeholder: type] marker to skip processing of this item")
            print(f"   - Run the command again after adding the marker to regenerate the status file")
        
    except json.JSONDecodeError as e:
        print(f"Error: Status file format error: {e}")
    except Exception as e:
        print(f"Warning: Error checking post-processing status: {e}")
        
        # Fallback to old method if JSON method fails
        try:
            if result_path.endswith('.md'):
                with open(result_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if "## 📋 Async processing status" in content:
                    print(f"\n" + "="*50)
                    print(f"Async processing status detection (from Markdown)")
                    print(f"="*50)
                    
                    # Extract the async processing section
                    lines = content.split('\n')
                    in_async_section = False
                    status_lines = []
                    
                    for line in lines:
                        if "## 📋 Async processing status" in line:
                            in_async_section = True
                            continue
                        elif in_async_section and line.startswith("## "):
                            break
                        elif in_async_section:
                            status_lines.append(line)
                    
                    # Display the status
                    for line in status_lines:
                        if line.strip():
                            print(line)
                    
                    print(f"\nSuggestion: After running the processing command, the JSON status file will be automatically created")
        except Exception as fallback_error:
            print(f"Warning:  Fallback processing also failed: {fallback_error}")


def list_processing_items(pdf_path: str, item_type: str = 'all', show_processed: bool = False):
    """List items available for processing with their hash IDs."""
    try:
        pdf_path_obj = Path(pdf_path)
        pdf_directory = pdf_path_obj.parent
        pdf_stem = pdf_path_obj.stem
        
        # Find status file
        status_file = pdf_directory / f"{pdf_stem}_postprocess.json"
        if not status_file.exists():
            print(f"Error: Status file not exists: {status_file}")
            return False
        
        with open(status_file, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
        
        items = status_data.get('items', [])
        
        # Filter by type and processing status
        filtered_items = []
        for item in items:
            # Filter by type
            if item_type != 'all':
                if item_type == 'image' and item['type'] != 'image':
                    continue
                elif item_type == 'formula' and item['type'] not in ['formula', 'interline_equation']:
                    continue
                elif item_type == 'table' and item['type'] != 'table':
                    continue
            
            # Filter by processing status
            if not show_processed and item.get('processed', False):
                continue
            
            filtered_items.append(item)
        
        if not filtered_items:
            print(f"No items found (type: {item_type}, show processed: {show_processed})")
            return True
        
        print(f"\n{item_type.upper() if item_type != 'all' else 'ALL'} items list:")
        print(f"=" * 40)
        
        for i, item in enumerate(filtered_items, 1):
            status_icon = "✅" if item.get('processed', False) else "⏳"
            processed_at = item.get('processed_at', '')
            processed_info = f" (Processed time: {processed_at})" if processed_at else ""
            
            print(f"{i:2d}. {status_icon} [{item['type'].upper()}] ID: {item['id'][:16]}...")
            print(f"Processor: {item['processor']} | Page: {item['page']} | Status: {'Processed' if item.get('processed', False) else 'Unprocessed'}{processed_info}")
        
        print(f"\nTotal: {len(filtered_items)} items")
        return True
        
    except Exception as e:
        print(f"Error: List items failed: {e}")
        return False


def process_by_hash_ids(pdf_path: str, hash_ids: list, processing_type: str = 'all'):
    """Process specific items by their hash IDs."""
    try:
        from mineru_wrapper import mineru_wrapper
        
        result = mineru_wrapper.process_items_by_hash_ids(pdf_path, hash_ids, processing_type)
        
        if result:
            print(f"\nBatch processing completed!")
            print(f"Updated status:")
            check_and_show_post_processing_status(pdf_path)
        
        return result
        
    except Exception as e:
        print(f"Error: Batch processing failed: {e}")
        return False


def main():
    """Main CLI entry point for PDF_EXTRACT command."""
    
    # Check for clean command
    if len(sys.argv) >= 2 and (sys.argv[1] == "clean" or sys.argv[1] == "--clean"):
        clean_data_directory()
        return 0
    
    # Check if PDF path is provided
    if len(sys.argv) < 2:
        print(f"No PDF path provided. Opening file selector...")
        pdf_path = get_pdf_path_interactive()
        
        if not pdf_path:
            print(f"Error:  No PDF selected. Exiting.")
            sys.exit(1)
        
        print(f"Selected PDF: {pdf_path}")
        
        # Check if same-name markdown file exists in PDF directory
        pdf_path_obj = Path(pdf_path)
        pdf_directory = pdf_path_obj.parent
        pdf_stem = pdf_path_obj.stem
        same_name_md_file = pdf_directory / f"{pdf_stem}.md"
        
        if same_name_md_file.exists():
            print(f"\nWarning:  File {same_name_md_file} already exists.")
            overwrite = input("Do you want to overwrite it? (y/N): ").strip().lower()
            if overwrite != 'y':
                print(f"Operation cancelled.")
                sys.exit(0)
        
        # Get options interactively
        page_range, call_api, call_api_force, debug, use_mineru, async_mode = get_interactive_options()
        
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
        async_mode = False
        
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
            elif arg == "--async-mode":
                async_mode = True
                use_mineru = True  # Async mode requires MinerU
            
            i += 1

    
    # Execute PDF extraction
    try:
        start_time = time.time()
        
        if use_mineru or async_mode:
            if async_mode:
                print(f"Using MinerU-async for PDF extraction...")
            else:
                print(f"Using MinerU for PDF extraction...")
            
            # Use the wrapper function with proper error handling
            result_path = extract_and_analyze_pdf_with_mineru(
                pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug, async_mode
            )
            
            # Try to perform content analysis if MinerU was used successfully
            # Check if the result came from MinerU (not fallback) by looking for temp directories
            mineru_temp_dirs = [d for d in os.listdir('/var/folders/w0/m02j_xv925sg34708rb2xgzr0000gn/T/') 
                              if d.startswith('mineru_output_')]
            
            if mineru_temp_dirs:
                # Use the most recent temp directory
                latest_temp = max(mineru_temp_dirs, key=lambda x: os.path.getctime(f'/var/folders/w0/m02j_xv925sg34708rb2xgzr0000gn/T/{x}'))
                temp_dir = f'/var/folders/w0/m02j_xv925sg34708rb2xgzr0000gn/T/{latest_temp}'
                
                # Content analysis removed per user request
            else:
                print(f"MinerU likely fell back to original extractor, no content analysis available")
        else:
            if call_api:
                print(f"Using Basic PDF extractor with image analysis...")
            else:
                print(f"Using Basic-async PDF extractor (no image analysis)...")
            result_path = extract_and_analyze_pdf(
                pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug
            )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"\nSUCCESS: PDF extracted to {result_path}")
        print(f" Total processing time: {processing_time:.2f} seconds")
        
        # Check if post-processing is needed
        if async_mode:
            check_and_show_post_processing_status(result_path)
        
        return 0
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 