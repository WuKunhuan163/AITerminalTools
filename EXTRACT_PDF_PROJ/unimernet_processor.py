#!/usr/bin/env python3
"""
Async UnimerNet Processor for Formula and Table Recognition
Processes images in _extract_data folder and updates markdown with descriptions
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add current directory to path for local imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import UnimerNet model components
UNIMERNET_AVAILABLE = False
load_unimernet_model = None
recognize_image = None

try:
    # Try to import from UNIMERNET_PROJ
    sys.path.insert(0, str(current_dir.parent / "UNIMERNET_PROJ"))
    from test_simple_unimernet import load_unimernet_model, recognize_image
    UNIMERNET_AVAILABLE = True
    print("UnimerNet model components loaded successfully")
except ImportError as e:
    try:
        # Fallback: try MinerU's internal UnimerNet
        from test_MinerU_formula.test_simple_unimernet import load_unimernet_model, recognize_image
        UNIMERNET_AVAILABLE = True
        print("UnimerNet model components loaded from MinerU")
    except ImportError:
        UNIMERNET_AVAILABLE = False
        print("⚠️  UnimerNet model not available. Formula/table recognition will be disabled.")

# Import image API
try:
    from image2text_api import get_image_analysis
    IMAGE_API_AVAILABLE = True
except ImportError:
    IMAGE_API_AVAILABLE = False
    print("⚠️  Image API not available. Image analysis will be disabled.")


class AsyncUnimerNetProcessor:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.unimernet_model = None
        self.unimernet_tokenizer = None
        
        # Load UnimerNet model if available
        if UNIMERNET_AVAILABLE:
            try:
                self.unimernet_model, self.unimernet_tokenizer = load_unimernet_model()
                print("UnimerNet model loaded successfully")
            except Exception as e:
                print(f"Error: Failed to load UnimerNet model: {e}")
                self.unimernet_model = None
                self.unimernet_tokenizer = None
    
    def process_markdown_file(self, md_file_path: str, call_image_api: bool = True) -> bool:
        """
        Process markdown file and update image descriptions
        
        Args:
            md_file_path: Path to the markdown file
            call_image_api: Whether to call image analysis API
            
        Returns:
            True if processing was successful
        """
        md_path = Path(md_file_path)
        if not md_path.exists():
            print(f"Error: Markdown file not found: {md_file_path}")
            return False
        
        # Find extract_data directory
        extract_data_dir = md_path.parent / f"{md_path.stem}_extract_data"
        images_dir = extract_data_dir / "images"
        
        if not images_dir.exists():
            print(f"Error: Images directory not found: {images_dir}")
            return False
        
        print(f"🔄 Processing markdown file: {md_file_path}")
        print(f"Images directory: {images_dir}")
        
        # Read current markdown content
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all image references with [DESCRIPTION] placeholder
        image_pattern = r'!\[\]\((images/[^)]+)\)\[DESCRIPTION\]'
        matches = list(re.finditer(image_pattern, content))
        
        if not matches:
            print("ℹ️  No image placeholders found in markdown file")
            return True
        
        print(f"📸 Found {len(matches)} image placeholders to process")
        
        # Process each image
        updated_content = content
        for match in matches:
            image_path = match.group(1)  # e.g., "images/filename.jpg"
            full_image_path = md_path.parent / image_path
            
            if not full_image_path.exists():
                print(f"Warning:  Image not found: {full_image_path}")
                # Replace with error message
                updated_content = updated_content.replace(
                    match.group(0),
                    f"![](images/{Path(image_path).name})[DESCRIPTION: Image file not found]"
                )
                continue
            
            # Process the image
            description = self._process_single_image(full_image_path, call_image_api)
            
            # Update content
            if description.startswith("[DESCRIPTION: "):
                # Keep the placeholder format for errors
                replacement = f"![](images/{Path(image_path).name}){description}"
            else:
                # Replace with actual content for successful recognition
                replacement = f"![](images/{Path(image_path).name})\n\n{description}"
            
            updated_content = updated_content.replace(match.group(0), replacement)
        
        # Write updated content back to file
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print(f"Markdown file updated successfully")
        return True
    
    def _process_single_image(self, image_path: Path, call_image_api: bool) -> str:
        """
        Process a single image for formula/table recognition or general analysis
        
        Args:
            image_path: Path to the image file
            call_image_api: Whether to call image analysis API
            
        Returns:
            Description text or placeholder
        """
        print(f"   🔍 Processing image: {image_path.name}")
        
        # First try UnimerNet for formula/table recognition
        if UNIMERNET_AVAILABLE and self.unimernet_model is not None:
            try:
                recognition_result = recognize_image(
                    str(image_path), 
                    self.unimernet_model, 
                    self.unimernet_tokenizer
                )
                
                if recognition_result and recognition_result.strip():
                    # Check if it's a formula or table based on content
                    if self._is_formula_or_table(recognition_result):
                        print(f"   ✅ UnimerNet recognition successful: {recognition_result[:50]}...")
                        return recognition_result
                    else:
                        print(f"   ⚠️  UnimerNet result doesn't seem to be formula/table")
                
            except Exception as e:
                print(f"   ❌ UnimerNet recognition failed: {e}")
        
        # If UnimerNet failed or not available, try image API
        if call_image_api and IMAGE_API_AVAILABLE:
            try:
                api_result = get_image_analysis(str(image_path), "academic")
                if api_result and api_result.strip():
                    print(f"   ✅ Image API successful: {api_result[:50]}...")
                    return f"[DESCRIPTION: {api_result}]"
                else:
                    print(f"   ⚠️  Image API returned empty result")
            except Exception as e:
                print(f"   ❌ Image API failed: {e}")
        
        # Return appropriate error message
        if not call_image_api:
            return "[DESCRIPTION: Image API not called]"
        else:
            return "[DESCRIPTION: UnimerNet recognition failed]"
    
    def _is_formula_or_table(self, text: str) -> bool:
        """
        Check if the recognized text is likely a formula or table
        
        Args:
            text: Recognized text
            
        Returns:
            True if it's likely a formula or table
        """
        # Check for LaTeX math indicators
        latex_indicators = [
            r'\begin{', r'\end{', r'\frac{', r'\sum', r'\int', r'\alpha', r'\beta', 
            r'\gamma', r'\delta', r'\epsilon', r'\theta', r'\lambda', r'\mu', r'\pi', 
            r'\sigma', r'\phi', r'\psi', r'\omega', r'\\', r'&', r'\hline'
        ]
        
        # Check for table indicators
        table_indicators = [
            r'\begin{array}', r'\begin{tabular}', r'\begin{table}', 
            r'&', r'\\', r'\hline', r'\cline'
        ]
        
        # Check for mathematical symbols
        math_symbols = ['=', '+', '-', '*', '/', '^', '_', '(', ')', '[', ']', '{', '}']
        
        text_lower = text.lower()
        
        # Count indicators
        latex_count = sum(1 for indicator in latex_indicators if indicator in text)
        table_count = sum(1 for indicator in table_indicators if indicator in text)
        math_count = sum(1 for symbol in math_symbols if symbol in text)
        
        # Decision logic
        if latex_count > 0 or table_count > 0:
            return True
        
        if math_count > 3 and len(text) > 10:
            return True
        
        # Check for repetitive patterns (common in failed recognition)
        if len(set(text.replace(' ', ''))) < len(text) * 0.3:
            return False
        
        return False
    
    def batch_process_directory(self, directory: str, call_image_api: bool = True) -> List[str]:
        """
        Process all markdown files in a directory
        
        Args:
            directory: Directory containing markdown files
            call_image_api: Whether to call image analysis API
            
        Returns:
            List of processed file paths
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"Error: Directory not found: {directory}")
            return []
        
        # Find all markdown files
        md_files = list(dir_path.glob("*.md"))
        
        if not md_files:
            print(f"ℹ️  No markdown files found in {directory}")
            return []
        
        processed_files = []
        
        for md_file in md_files:
            print(f"\n📄 Processing: {md_file}")
            try:
                if self.process_markdown_file(str(md_file), call_image_api):
                    processed_files.append(str(md_file))
                    print(f"Successfully processed: {md_file}")
                else:
                    print(f"Error: Failed to process: {md_file}")
            except Exception as e:
                print(f"Error: Error processing {md_file}: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
        
        return processed_files


def main():
    parser = argparse.ArgumentParser(description="Async UnimerNet Processor for Formula and Table Recognition")
    parser.add_argument("target", help="Path to markdown file or directory")
    parser.add_argument("--no-image-api", dest="call_image_api", action="store_false", default=True,
                        help="Disable image API calls")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = AsyncUnimerNetProcessor(debug=args.debug)
    
    target_path = Path(args.target)
    
    try:
        if target_path.is_file() and target_path.suffix == '.md':
            # Process single file
            success = processor.process_markdown_file(str(target_path), args.call_image_api)
            if success:
                print(f"\n🎉 Successfully processed: {target_path}")
            else:
                print(f"\nError: Failed to process: {target_path}")
                sys.exit(1)
        
        elif target_path.is_dir():
            # Process directory
            processed_files = processor.batch_process_directory(str(target_path), args.call_image_api)
            
            if processed_files:
                print(f"\n🎉 Successfully processed {len(processed_files)} files:")
                for file in processed_files:
                    print(f"{file}")
            else:
                print(f"\nError: No files were processed successfully")
                sys.exit(1)
        
        else:
            print(f"Error: Invalid target: {target_path}")
            print("Target must be a markdown file (.md) or directory")
            sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 