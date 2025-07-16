#!/usr/bin/env python3
"""
Command line script to extract PDF using MinerU and output to terminal
"""

import sys
import os
import argparse
from pathlib import Path

# Add the pdf_extractor directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from mineru_wrapper import extract_and_analyze_pdf_with_mineru

def main():
    parser = argparse.ArgumentParser(description='Extract PDF using MinerU and output to terminal')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--pages', '-p', default='1-10', help='Page range (e.g., "1-10", "1,3,5")')
    parser.add_argument('--no-image-api', action='store_true', help='Disable image analysis API')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Check if PDF file exists
    if not os.path.exists(args.pdf_path):
        print(f"❌ Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)
    
    print(f"🔄 Processing PDF: {args.pdf_path}")
    print(f"📄 Page range: {args.pages}")
    print(f"🚫 Image API disabled: {args.no_image_api}")
    print("-" * 50)
    
    try:
        # Extract PDF using MinerU
        result_path = extract_and_analyze_pdf_with_mineru(
            pdf_path=args.pdf_path,
            layout_mode="arxiv",
            mode="academic",
            call_api=not args.no_image_api,
            call_api_force=False,
            page_range=args.pages,
            debug=args.debug
        )
        
        print(f"✅ Extraction successful!")
        print(f"📁 Output file: {result_path}")
        print("-" * 50)
        print("📝 MARKDOWN CONTENT:")
        print("=" * 50)
        
        # Read and output the markdown content
        with open(result_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
        
        print("=" * 50)
        print(f"📊 Total characters: {len(content)}")
        
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 