#!/usr/bin/env python3
"""
Enhanced PDF Extractor with improved output interface
Creates same-name .md file and _extract_data folder for intermediate files
"""

import argparse
import os
import sys
import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

# Add current directory to path for local imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from mineru_wrapper_enhanced import EnhancedMinerUWrapper

class EnhancedPDFExtractor:
    def __init__(self):
        self.mineru_wrapper = EnhancedMinerUWrapper()
    
    def extract_pdf(
        self,
        pdf_path: str,
        layout_mode: str = "arxiv",
        mode: str = "academic",
        call_api: bool = True,
        call_api_force: bool = False,
        page_range: Optional[str] = None,
        debug: bool = False,
        overwrite: bool = True
    ) -> str:
        """
        Extract PDF with enhanced output interface
        
        Args:
            pdf_path: Path to the PDF file
            layout_mode: Layout detection mode
            mode: Analysis mode
            call_api: Whether to call image analysis API
            call_api_force: Whether to force API call
            page_range: Page range to process
            debug: Enable debug mode
            overwrite: Whether to overwrite existing files
            
        Returns:
            Path to the output markdown file
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Create output paths
        pdf_stem = pdf_path.stem
        pdf_dir = pdf_path.parent
        
        # Target markdown file (same name as PDF)
        target_md_file = pdf_dir / f"{pdf_stem}.md"
        
        # Extract data directory
        extract_data_dir = pdf_dir / f"{pdf_stem}_extract_data"
        
        # Check if files exist and handle overwrite
        if target_md_file.exists() and not overwrite:
            response = input(f"File {target_md_file} already exists. Overwrite? (y/N): ")
            if response.lower() != 'y':
                print("Operation cancelled.")
                return str(target_md_file)
        
        # Create extract data directory
        extract_data_dir.mkdir(exist_ok=True)
        images_dir = extract_data_dir / "images"
        images_dir.mkdir(exist_ok=True)
        
        print(f"🔄 Processing PDF: {pdf_path}")
        print(f"📁 Output markdown: {target_md_file}")
        print(f"📁 Extract data directory: {extract_data_dir}")
        
        # Use enhanced MinerU wrapper to process the PDF
        try:
            # Process with enhanced MinerU - it handles the output structure automatically
            result_md_file = self.mineru_wrapper.extract_and_analyze_pdf(
                str(pdf_path),
                output_dir=str(pdf_dir),
                layout_mode=layout_mode,
                mode=mode,
                call_api=call_api,
                call_api_force=call_api_force,
                page_range=page_range,
                debug=debug
            )
            
            print(f"✅ PDF extraction completed!")
            print(f"📄 Markdown file: {result_md_file}")
            print(f"📁 Extract data: {extract_data_dir}")
            
            return result_md_file
                
        except Exception as e:
            print(f"❌ Error during PDF extraction: {e}")
            if debug:
                import traceback
                traceback.print_exc()
            raise
    



def main():
    parser = argparse.ArgumentParser(description="Enhanced PDF Extractor with improved output interface")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--mode", default="academic", help="Analysis mode")
    parser.add_argument("--layout-mode", default="arxiv", help="Layout detection strategy")
    parser.add_argument("--page", help="Page range to process, e.g., '1-5,8'")
    parser.add_argument('--no-image-api', dest='call_api', action='store_false', default=True)
    parser.add_argument('--image-api-force', dest='call_api_force', action='store_true')
    parser.add_argument('--debug', action='store_true', help="Enable debug mode")
    parser.add_argument('--no-overwrite', dest='overwrite', action='store_false', default=True)
    
    args = parser.parse_args()
    
    try:
        extractor = EnhancedPDFExtractor()
        result = extractor.extract_pdf(
            pdf_path=args.pdf_path,
            layout_mode=args.layout_mode,
            mode=args.mode,
            call_api=args.call_api,
            call_api_force=args.call_api_force,
            page_range=args.page,
            debug=args.debug,
            overwrite=args.overwrite
        )
        
        print(f"\n🎉 Extraction completed successfully!")
        print(f"📄 Output: {result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 