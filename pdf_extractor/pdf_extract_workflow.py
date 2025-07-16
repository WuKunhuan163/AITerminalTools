#!/usr/bin/env python3
"""
Complete PDF Extraction Workflow
Integrates enhanced PDF extractor with async UnimerNet processor
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Optional

# Add current directory to path for local imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from pdf_extractor_enhanced import EnhancedPDFExtractor
from async_unimernet_processor import AsyncUnimerNetProcessor


def main():
    parser = argparse.ArgumentParser(
        description="Complete PDF Extraction Workflow with Enhanced Output Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic extraction
  python pdf_extract_workflow.py document.pdf
  
  # Extract specific pages with async processing
  python pdf_extract_workflow.py document.pdf --page 1-5 --async-process
  
  # Extract without image API, then process with UnimerNet
  python pdf_extract_workflow.py document.pdf --no-image-api --async-process
  
  # Debug mode with verbose output
  python pdf_extract_workflow.py document.pdf --debug --async-process
        """
    )
    
    # Main arguments
    parser.add_argument("pdf_path", help="Path to the PDF file")
    
    # PDF extraction options
    parser.add_argument("--mode", default="academic", help="Analysis mode")
    parser.add_argument("--layout-mode", default="arxiv", help="Layout detection strategy")
    parser.add_argument("--page", help="Page range to process, e.g., '1-5,8'")
    parser.add_argument('--no-image-api', dest='call_api', action='store_false', default=True,
                        help="Disable image API calls during extraction")
    parser.add_argument('--image-api-force', dest='call_api_force', action='store_true',
                        help="Force image API calls even if cached")
    parser.add_argument('--no-overwrite', dest='overwrite', action='store_false', default=True,
                        help="Don't overwrite existing files")
    
    # Async processing options
    parser.add_argument('--async-process', action='store_true',
                        help="Run async UnimerNet processing after extraction")
    parser.add_argument('--no-async-image-api', dest='async_call_api', action='store_false', default=True,
                        help="Disable image API calls during async processing")
    
    # General options
    parser.add_argument('--debug', action='store_true', help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Validate PDF path
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"❌ Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    if not pdf_path.suffix.lower() == '.pdf':
        print(f"❌ Error: File is not a PDF: {pdf_path}")
        sys.exit(1)
    
    print(f"🚀 Starting PDF extraction workflow for: {pdf_path}")
    print("=" * 60)
    
    # Step 1: Extract PDF with enhanced interface
    print("\n📋 Step 1: PDF Extraction with Enhanced Interface")
    print("-" * 40)
    
    try:
        extractor = EnhancedPDFExtractor()
        
        extraction_start = time.time()
        
        result_md_file = extractor.extract_pdf(
            pdf_path=str(pdf_path),
            layout_mode=args.layout_mode,
            mode=args.mode,
            call_api=args.call_api,
            call_api_force=args.call_api_force,
            page_range=args.page,
            debug=args.debug,
            overwrite=args.overwrite
        )
        
        extraction_time = time.time() - extraction_start
        
        print(f"\n✅ Step 1 completed in {extraction_time:.2f} seconds")
        print(f"📄 Markdown file: {result_md_file}")
        
        # Verify extract_data directory exists
        extract_data_dir = Path(result_md_file).parent / f"{Path(result_md_file).stem}_extract_data"
        if extract_data_dir.exists():
            print(f"📁 Extract data directory: {extract_data_dir}")
            
            # Show contents
            images_dir = extract_data_dir / "images"
            if images_dir.exists():
                image_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))
                print(f"🖼️  Found {len(image_files)} image files")
            
            # Show intermediate files
            intermediate_files = [f for f in extract_data_dir.glob("*") if f.is_file()]
            if intermediate_files:
                print(f"📋 Intermediate files: {len(intermediate_files)}")
                for f in intermediate_files:
                    print(f"   - {f.name}")
        
    except Exception as e:
        print(f"❌ Error in Step 1: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    # Step 2: Async UnimerNet processing (if requested)
    if args.async_process:
        print("\n🔬 Step 2: Async UnimerNet Processing")
        print("-" * 40)
        
        try:
            processor = AsyncUnimerNetProcessor(debug=args.debug)
            
            processing_start = time.time()
            
            success = processor.process_markdown_file(
                result_md_file,
                call_image_api=args.async_call_api
            )
            
            processing_time = time.time() - processing_start
            
            if success:
                print(f"\n✅ Step 2 completed in {processing_time:.2f} seconds")
                print(f"📄 Updated markdown file: {result_md_file}")
            else:
                print(f"\n⚠️  Step 2 completed with warnings in {processing_time:.2f} seconds")
                print(f"📄 Markdown file: {result_md_file}")
                
        except Exception as e:
            print(f"❌ Error in Step 2: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
            print("⚠️  Continuing without async processing...")
    
    # Final summary
    print("\n" + "=" * 60)
    print("🎉 PDF Extraction Workflow Completed!")
    print("=" * 60)
    
    print(f"\n📄 Final output: {result_md_file}")
    
    # Show file sizes
    md_path = Path(result_md_file)
    if md_path.exists():
        md_size = md_path.stat().st_size
        print(f"📊 Markdown file size: {md_size:,} bytes")
        
        # Count lines
        with open(md_path, 'r', encoding='utf-8') as f:
            lines = len(f.readlines())
        print(f"📊 Markdown file lines: {lines:,}")
    
    # Show extract_data directory info
    extract_data_dir = md_path.parent / f"{md_path.stem}_extract_data"
    if extract_data_dir.exists():
        print(f"📁 Extract data directory: {extract_data_dir}")
        
        # Calculate total size
        total_size = sum(f.stat().st_size for f in extract_data_dir.rglob('*') if f.is_file())
        print(f"📊 Total extract data size: {total_size:,} bytes")
        
        # Count files
        total_files = len([f for f in extract_data_dir.rglob('*') if f.is_file()])
        print(f"📊 Total files in extract data: {total_files}")
    
    print("\n💡 Next steps:")
    if not args.async_process:
        print("   • Run with --async-process to enable formula/table recognition")
    print("   • Check the markdown file for [DESCRIPTION] placeholders")
    print("   • Use the extract_data directory for debugging and analysis")
    
    print(f"\n🏁 Workflow completed successfully!")


if __name__ == "__main__":
    main() 