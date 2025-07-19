#!/usr/bin/env python3
"""
EXTRACT_IMG - Image Analysis Tool with Type Detection and Routing
Intelligent image analysis tool that routes different image types to appropriate processors

TODO: Currently redirected to EXTRACT_PDF for better formula/table recognition.
      The original UNIMERNET integration code is preserved but temporarily bypassed.
      This allows EXTRACT_PDF's MinerU-based processing to handle all image types.
"""

import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add current directory to path for imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import centralized cache system
# Import centralized cache system from EXTRACT_IMG_PROJ
try:
    from EXTRACT_IMG_PROJ.cache_system import ImageCacheSystem
except ImportError:
    # Fallback import path for development
    import sys
    from pathlib import Path
    extract_img_proj = Path(__file__).parent / "EXTRACT_IMG_PROJ"
    if str(extract_img_proj) not in sys.path:
        sys.path.insert(0, str(extract_img_proj))
    from cache_system import ImageCacheSystem

# Import existing tools
try:
    from IMG2TEXT import get_image_analysis
    IMG2TEXT_AVAILABLE = True
except ImportError:
    logger.warning("IMG2TEXT not available")
    IMG2TEXT_AVAILABLE = False

# Try to import UnimerNet functionality
try:
    # Add UNIMERNET_PROJ to path
    unimernet_proj_path = current_dir / "UNIMERNET_PROJ"
    if str(unimernet_proj_path) not in sys.path:
        sys.path.insert(0, str(unimernet_proj_path))
    
    # Add test_MinerU_formula to path
    test_formula_path = unimernet_proj_path / "test_MinerU_formula"
    if str(test_formula_path) not in sys.path:
        sys.path.insert(0, str(test_formula_path))
    
    from test_simple_unimernet import load_unimernet_model, recognize_image
    UNIMERNET_AVAILABLE = True
except ImportError:
    logger.warning("UnimerNet processor not available")
    UNIMERNET_AVAILABLE = False

class ImageTypeDetector:
    """
    Detects the type of image content to route to appropriate processor.
    """
    
    @staticmethod
    def detect_image_type(image_path: str, hint: str = None) -> str:
        """
        Detect image type based on file characteristics and hints.
        
        Args:
            image_path: Path to image file
            hint: Optional hint about image type
            
        Returns:
            Image type: 'formula', 'table', 'academic', or 'unknown'
        """
        if hint and hint.lower() in ['formula', 'table', 'academic']:
            return hint.lower()
        
        # Basic heuristics based on filename
        filename = Path(image_path).name.lower()
        
        if any(word in filename for word in ['formula', 'equation', 'math', 'latex']):
            return 'formula'
        elif any(word in filename for word in ['table', 'chart', 'graph', 'plot']):
            return 'table'
        elif any(word in filename for word in ['academic', 'paper', 'document', 'research']):
            return 'academic'
        else:
            # Default to academic for general images
            return 'academic'

class ImageProcessor:
    """
    Main image processing class that routes images to appropriate processors.
    """
    
    def __init__(self):
        """Initialize the image processor."""
        self.cache_system = ImageCacheSystem()
        self.type_detector = ImageTypeDetector()
        
        # Initialize UnimerNet model if available
        if UNIMERNET_AVAILABLE:
            try:
                self.unimernet_model, self.unimernet_tokenizer = load_unimernet_model()
                logger.info("UnimerNet model initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize UnimerNet: {e}")
                self.unimernet_model = None
                self.unimernet_tokenizer = None
        else:
            self.unimernet_model = None
            self.unimernet_tokenizer = None
    
    def process_image(self, image_path: str, image_type: str = None, 
                     mode: str = "academic", force_reprocess: bool = False, 
                     output_format: str = "md") -> Dict[str, Any]:
        """
        Process an image using the appropriate processor.
        
        Args:
            image_path: Path to the image file
            image_type: Type of image ('formula', 'table', 'image', 'auto')
            mode: Processing mode for general images
            force_reprocess: Force reprocessing even if cached
            output_format: Output format ("html" or "md")
            
        Returns:
            Dictionary with processing results
        """
        image_path = Path(image_path)
        
        if not image_path.exists():
            return {
                "success": False,
                "error": f"Image file not found: {image_path}",
                "timestamp": datetime.now().isoformat()
            }
        
        # Read image data
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read image: {e}",
                "timestamp": datetime.now().isoformat()
            }
        
        # Check cache first (unless force reprocessing)
        if not force_reprocess:
            cached_result = self.cache_system.get_cached_description(image_data)
            if cached_result:
                logger.info(f"Using cached result for {image_path.name}")
                return {
                    "success": True,
                    "result": cached_result,
                    "image_path": str(image_path),
                    "image_type": "cached",
                    "processor": "cache",
                    "timestamp": datetime.now().isoformat(),
                    "from_cache": True
                }
        
        # Detect image type if not specified
        if image_type is None or image_type == "auto":
            image_type = self.type_detector.detect_image_type(str(image_path))
        
        # TODO: Temporarily redirect to EXTRACT_PDF for better results
        logger.info(f"Redirecting {image_path.name} to EXTRACT_PDF for processing (format: {output_format})")
        return self._process_with_extract_pdf(image_path, image_type, force_reprocess, output_format)
        
        # TODO: Original routing logic preserved but temporarily disabled
        # The following code implements the original UNIMERNET/IMG2TEXT routing
        # It can be re-enabled by removing the early return above
        
        logger.info(f"Processing {image_path.name} as {image_type}")
        
        # Route to appropriate processor based on image type
        result = None
        processor_used = None
        
        if image_type in ['formula', 'table'] and self.unimernet_model:
            # Use UnimerNet for formulas and tables
            result = self._process_with_unimernet(image_path, image_data)
            processor_used = "unimernet"
        elif image_type == 'academic' and IMG2TEXT_AVAILABLE:
            # Use IMG2TEXT for academic images
            result = self._process_with_img2text(image_path, mode)
            processor_used = "img2text"
        
        # Fallback logic: try the other processor if first choice fails
        if result is None:
            if image_type in ['formula', 'table'] and IMG2TEXT_AVAILABLE:
                # Fallback to IMG2TEXT for formulas/tables if UnimerNet fails
                result = self._process_with_img2text(image_path, mode)
                processor_used = "img2text_fallback"
            elif image_type == 'academic' and self.unimernet_model:
                # Fallback to UnimerNet for academic images if IMG2TEXT fails
                result = self._process_with_unimernet(image_path, image_data)
                processor_used = "unimernet_fallback"
        
        if result is None:
            return {
                "success": False,
                "error": "No suitable processor available",
                "image_path": str(image_path),
                "image_type": image_type,
                "timestamp": datetime.now().isoformat()
            }
        
        # Cache the result
        if result and result.strip():
            self.cache_system.store_image_and_description(
                image_data, result, str(image_path)
            )
        
        return {
            "success": True,
            "result": result,
            "image_path": str(image_path),
            "image_type": image_type,
            "processor": processor_used,
            "timestamp": datetime.now().isoformat(),
            "from_cache": False
        }
    
    def _process_with_unimernet(self, image_path: Path, image_data: bytes) -> Optional[str]:
        """
        Process image with UnimerNet.
        
        Args:
            image_path: Path to image file
            image_data: Image bytes data
            
        Returns:
            Processing result or None if failed
        """
        try:
            result = recognize_image(str(image_path), self.unimernet_model, self.unimernet_tokenizer)
            if result and result.strip():
                logger.info(f"UnimerNet processing successful for {image_path.name}")
                return result
        except Exception as e:
            logger.warning(f"UnimerNet processing failed: {e}")
        
        return None
    
    def _process_with_img2text(self, image_path: Path, mode: str) -> Optional[str]:
        """
        Process image with IMG2TEXT.
        
        Args:
            image_path: Path to image file
            mode: Processing mode
            
        Returns:
            Processing result or None if failed
        """
        try:
            result = get_image_analysis(str(image_path), mode)
            if result and result.strip() and not result.startswith("*["):
                logger.info(f"IMG2TEXT processing successful for {image_path.name}")
                return result
        except Exception as e:
            logger.warning(f"IMG2TEXT processing failed: {e}")
        
        return None
    
    def _process_with_extract_pdf(self, image_path: Path, image_type: str, force_reprocess: bool, output_format: str = "md") -> Dict[str, Any]:
        """
        Process image using EXTRACT_PDF for superior results.
        
        TODO: This is a temporary redirection to EXTRACT_PDF's MinerU-based processing.
              EXTRACT_PDF provides better formula and table recognition than standalone tools.
        
        Args:
            image_path: Path to image file
            image_type: Type of image content
            force_reprocess: Whether to force reprocessing
            output_format: Output format ("html" or "md")
            
        Returns:
            Processing result dictionary
        """
        try:
            # Import EXTRACT_PDF functionality
            extract_pdf_proj = Path(__file__).parent / "EXTRACT_PDF_PROJ"
            if str(extract_pdf_proj) not in sys.path:
                sys.path.insert(0, str(extract_pdf_proj))
            
            from mineru_wrapper import MinerUWrapper
            
            # Initialize MinerU wrapper
            wrapper = MinerUWrapper()
            
            # Process the image using MinerU
            logger.info(f"Processing {image_path.name} with EXTRACT_PDF/MinerU")
            result_path = wrapper.extract_and_analyze_pdf(
                str(image_path),
                layout_mode="arxiv",
                mode="academic",
                call_api=False,  # Disable external API calls
                call_api_force=force_reprocess,
                page_range=None,
                debug=False,
                async_mode=False
            )
            
            if result_path and Path(result_path).exists():
                # Read the generated markdown content
                with open(result_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
                
                # Apply HTML table to Markdown conversion only if output format is "md"
                if output_format == "md":
                    processed_content = wrapper._convert_html_tables_to_markdown(markdown_content)
                else:
                    processed_content = markdown_content
                
                # Extract meaningful content (skip metadata)
                lines = processed_content.split('\n')
                content_lines = []
                skip_yaml = False
                
                for line in lines:
                    if line.strip() == '```yaml':
                        skip_yaml = True
                        continue
                    elif line.strip() == '```' and skip_yaml:
                        skip_yaml = False
                        continue
                    elif not skip_yaml and line.strip() and not line.startswith('#'):
                        content_lines.append(line.strip())
                
                result_text = '\n'.join(content_lines).strip()
                
                if result_text:
                    return {
                        "success": True,
                        "result": result_text,
                        "image_path": str(image_path),
                        "image_type": image_type,
                        "processor": "extract_pdf_mineru",
                        "timestamp": datetime.now().isoformat(),
                        "from_cache": False,
                        "note": "Processed using EXTRACT_PDF/MinerU for superior recognition"
                    }
            
            # If no meaningful content was extracted
            return {
                "success": False,
                "error": "EXTRACT_PDF processing completed but no meaningful content extracted",
                "image_path": str(image_path),
                "image_type": image_type,
                "processor": "extract_pdf_mineru",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"EXTRACT_PDF processing failed: {e}")
            return {
                "success": False,
                "error": f"EXTRACT_PDF processing failed: {e}",
                "image_path": str(image_path),
                "image_type": image_type,
                "processor": "extract_pdf_mineru",
                "timestamp": datetime.now().isoformat()
            }
    
    def batch_process_images(self, image_paths: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Process multiple images in batch.
        
        Args:
            image_paths: List of image file paths
            **kwargs: Additional arguments for process_image
            
        Returns:
            List of processing results
        """
        results = []
        
        for image_path in image_paths:
            result = self.process_image(image_path, **kwargs)
            results.append(result)
        
        return results
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache_system.get_cache_stats()

def main():
    """Command line interface for EXTRACT_IMG."""
    parser = argparse.ArgumentParser(description="EXTRACT_IMG - Intelligent Image Analysis Tool")
    
    parser.add_argument("image_path", help="Path to image file")
    parser.add_argument("--type", choices=["formula", "table", "image", "auto"], 
                       default="auto", help="Image type hint")
    parser.add_argument("--mode", choices=["academic", "general", "code_snippet"],
                       default="academic", help="Processing mode for general images")
    parser.add_argument("--force", action="store_true", 
                       help="Force reprocessing even if cached")
    parser.add_argument("--format", choices=["html", "md"], default="md",
                       help="Output format: html (raw) or md (post-processed)")
    parser.add_argument("--batch", nargs="+", help="Process multiple images")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = ImageProcessor()
    
    # Show cache statistics if requested
    if args.stats:
        stats = processor.get_cache_stats()
        print("Cache Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return
    
    # Process images
    if args.batch:
        # Batch processing
        results = processor.batch_process_images(
            args.batch,
            image_type=args.type,
            mode=args.mode,
            force_reprocess=args.force,
            output_format=args.format
        )
        
        if args.json:
            output = {"batch_results": results}
            print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            for i, result in enumerate(results):
                print(f"\n--- Image {i+1}: {result.get('image_path', 'Unknown')} ---")
                if result.get('success'):
                    print(f"Type: {result.get('image_type', 'Unknown')}")
                    print(f"Processor: {result.get('processor', 'Unknown')}")
                    print(f"From cache: {result.get('from_cache', False)}")
                    print(f"Result: {result.get('result', 'No result')}")
                else:
                    print(f"Error: {result.get('error', 'Unknown error')}")
    else:
        # Single image processing
        result = processor.process_image(
            args.image_path,
            image_type=args.type,
            mode=args.mode,
            force_reprocess=args.force,
            output_format=args.format
        )
        
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            if result.get('success'):
                print(f"Image: {result.get('image_path', 'Unknown')}")
                print(f"Type: {result.get('image_type', 'Unknown')}")
                print(f"Processor: {result.get('processor', 'Unknown')}")
                print(f"From cache: {result.get('from_cache', False)}")
                print(f"\nResult:\n{result.get('result', 'No result')}")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")
    
    # Save output to file if requested
    if args.output:
        if args.batch:
            output_data = {"batch_results": results}
        else:
            output_data = result
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to: {args.output}")

if __name__ == "__main__":
    main() 