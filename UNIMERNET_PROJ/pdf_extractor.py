#!/usr/bin/env python3
import argparse
import os
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path

# Local imports
try:
    # Add current directory to path for local imports
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    from extract_paper_layouts import get_layout_processor, rejoin_paragraphs
    from image2text_api import get_image_analysis
    
    # Add parent directory to path for centralized cache system
    parent_dir = current_dir.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    # Import centralized cache system from EXTRACT_IMG_DATA
    try:
        from EXTRACT_IMG_DATA.cache_system import ImageCacheSystem
    except ImportError:
        # Fallback import path
        import sys
        from pathlib import Path
        extract_img_proj = parent_dir / "EXTRACT_IMG_DATA"
        if str(extract_img_proj) not in sys.path:
            sys.path.insert(0, str(extract_img_proj))
        from cache_system import ImageCacheSystem
except ImportError as e:
    print(f"错误: 无法导入必要的本地模块. {e}", file=sys.stderr)
    sys.exit(1)
    
# External library imports
try:
    import tkinter as tk
    from tkinter import filedialog
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
try:
    import fitz
except ImportError:
    print("错误: PyMuPDF 库未安装。", file=sys.stderr); sys.exit(1)

# --- Configuration using Absolute Paths ---
SCRIPT_DIR = Path(__file__).parent.resolve()
# 使用UNIMERNET_DATA目录（数据与代码分离）
DATA_DIR = SCRIPT_DIR.parent / "UNIMERNET_DATA" / "pdf_extractor_data"
if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "images").mkdir(exist_ok=True)
    (DATA_DIR / "markdown").mkdir(exist_ok=True)
MARKDOWN_DIR = DATA_DIR / "markdown"
IMAGE_DIR = DATA_DIR / "images"

# Initialize centralized cache system
cache_system = ImageCacheSystem(base_dir=SCRIPT_DIR.parent)

# --- Helper Functions ---
def calculate_hash(data: bytes) -> str: return hashlib.sha256(data).hexdigest()

# Legacy cache functions for backward compatibility
def load_cache() -> dict:
    """Legacy function - now uses centralized cache system"""
    return cache_system.cache

def save_cache(cache: dict):
    """Legacy function - now uses centralized cache system"""
    cache_system.cache = cache
    cache_system._save_cache()
def find_next_numeric_filename(directory: Path, suffix: str = ".md") -> Path:
    directory.mkdir(exist_ok=True); counter = 0
    while True:
        path = directory / f"{counter}{suffix}";
        if not path.exists(): return path
        counter += 1
def parse_page_ranges(page_str: str, total_pages: int) -> set[int]:
    if not page_str: return set()
    pages = set()
    try:
        for part in page_str.split(','):
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-')); pages.update(range(start - 1, end))
            else: pages.add(int(part) - 1)
    except ValueError: return set()
    return {p for p in pages if 0 <= p < total_pages}

# --- Main Orchestration Function ---
def extract_and_analyze_pdf(path_str: str, layout_mode: str, mode: str, call_api: bool, call_api_force: bool, page_range, debug: bool):
    path = Path(path_str)
    if not path.exists(): print(f"❌ PDF not found: '{path}'", file=sys.stderr); return
    
    cache, doc = load_cache(), fitz.open(path)
    IMAGE_DIR.mkdir(exist_ok=True) 
    
    layout_processor = get_layout_processor(layout_mode)
    
    page_indices = list(range(len(doc))) if not page_range else sorted(list(parse_page_ranges(page_range, len(doc))))
    metadata = doc.metadata; title = metadata.get('title', path.stem) or path.stem; author = metadata.get('author', 'N/A')
    processed_pages_str = page_range if page_range else f"All (1-{len(doc)})"
    
    markdown_content = [f"# Analysis Report for: {title}\n", "```yaml", f"Source PDF: {path.name}", f"Author(s): {author}", f"Analysis Mode: {mode}", f"Layout Mode: {layout_mode}", f"API Called: {call_api}", "```", "\n---\n"]
    print(f"ℹ️ Starting semantic analysis...", file=sys.stderr)

    for page_num in page_indices:
        page = doc[page_num]
        print(f"   - Processing page {page_num + 1}/{len(doc)}...", file=sys.stderr)
        
        semantic_blocks = layout_processor.process_page(page, IMAGE_DIR, debug)
        
        markdown_content.append(f"\n## 📄 Page {page_num + 1}\n")
        
        for i, block in enumerate(semantic_blocks):
            if i > 0: markdown_content.append("")
            block_type = block["type"]
            
            if block_type == "Figure":
                content = f"Screenshot Path: {block['screenshot_path']}\n"
                associated_text = " ".join([t[4] for t in block.get("associated_texts", [])])
                rejoined_associated_text = rejoin_paragraphs(associated_text)
                content += f"Associated Text: {rejoined_associated_text}\n"
                # Use centralized cache system for improved hash collision avoidance
                description = ""
                
                # Check cache first (unless force API call is requested)
                if not call_api_force:
                    cached_description = cache_system.get_cached_description(block['bytes_data'])
                    if cached_description:
                        description = cached_description
                        print(f"   - Using cached analysis for image...", file=sys.stderr)
                
                # If not in cache and API is enabled, call API
                if not description and call_api:
                    print(f"   - Analyzing image via API...", file=sys.stderr)
                    description = get_image_analysis(str(block['screenshot_path']), mode)
                    
                    # Store in centralized cache system
                    if description and description.strip():
                        cache_system.store_image_and_description(
                            block['bytes_data'], 
                            description, 
                            str(block['screenshot_path'])
                        )
                
                # If API is disabled and not in cache
                if not description:
                    description = "Analysis not performed (API not called)."
                content += f"Analysis: \n== Description Starts Here ==\n{description}\n=== Description Ends Here ===\n"
            else:
                content = block["content"]

            markdown_content.append(f"[{block_type}]\n{content}")

    doc.close()
    # Cache is automatically saved by the centralized cache system
    print("ℹ️ Cache updated.", file=sys.stderr)

    final_markdown_string = "\n".join(markdown_content)
    output_path = find_next_numeric_filename(MARKDOWN_DIR) 
    with open(output_path, 'w', encoding='utf-8') as f: f.write(final_markdown_string)
    
    print(f"✅ Report saved to: {output_path}", file=sys.stderr)
    # print(final_markdown_string)
    return output_path

# --- Main Entry Point ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extracts and semantically structures PDF content.")
    parser.add_argument("path", nargs='?', default=None, help="Optional: Path to PDF.")
    parser.add_argument("--mode", default="academic", help="Analysis mode")
    parser.add_argument("--layout-mode", default="arxiv", help="Layout detection strategy: arxiv")
    parser.add_argument("--page", help="Page range to process, e.g., '1-5,8'.")
    parser.add_argument('--image-api', dest='call_api', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument('--image-api-force', dest='call_api_force', action='store_true')
    parser.add_argument('--debug', action='store_true', help="Enable detailed debug logging for text merging.")
    parser.add_argument('--clean', action='store_true', help="Clean UNIMERNET_DATA folder before processing.")
    args = parser.parse_args()

    pdf_path = args.path
    
    # Clean data folder if requested
    if args.clean:
        import shutil
        if DATA_DIR.exists():
            print(f"🗑️ Cleaning {DATA_DIR}...", file=sys.stderr)
            print(f"📁 Deleting folder: {DATA_DIR.absolute()}", file=sys.stderr)
            shutil.rmtree(DATA_DIR)
            print(f"✅ Folder deleted successfully", file=sys.stderr)
        else:
            print(f"ℹ️ Folder {DATA_DIR.absolute()} does not exist, nothing to clean", file=sys.stderr)
        
        # If no PDF path provided with --clean, just clean and exit
        if not pdf_path:
            print("🎯 Clean-only mode: folder cleaned, exiting.", file=sys.stderr)
            sys.exit(0)
    
    if not pdf_path:
        if not TKINTER_AVAILABLE: print("Error: No path provided...", file=sys.stderr); sys.exit(1)
        print("ℹ️ Opening file dialog...", file=sys.stderr)
        root = tk.Tk(); root.withdraw()
        pdf_path = filedialog.askopenfilename(title="Select a PDF to analyze", filetypes=[("PDF", "*.pdf")])
        if not pdf_path: print("❌ Operation cancelled.", file=sys.stderr); sys.exit(0)
        
    # Try to use MinerU wrapper first, fallback to original if it fails
    try:
        from mineru_wrapper import extract_and_analyze_pdf_with_mineru
        extract_and_analyze_pdf_with_mineru(pdf_path, args.layout_mode, args.mode, args.call_api, args.call_api_force, args.page, args.debug)
    except Exception as e:
        print(f"⚠️  MinerU wrapper failed: {e}", file=sys.stderr)
        print("🔄 Falling back to original PDF extractor...", file=sys.stderr)
        extract_and_analyze_pdf(pdf_path, args.layout_mode, args.mode, args.call_api, args.call_api_force, args.page, args.debug)