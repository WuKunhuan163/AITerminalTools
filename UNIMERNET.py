#!/usr/bin/env python3
"""
UNIMERNET - UnimerNet Formula and Table Recognition Tool
Standalone tool for mathematical formula and table recognition using UnimerNet
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
    # Fallback import path
    import sys
    from pathlib import Path
    extract_img_proj = Path(__file__).parent / "EXTRACT_IMG_PROJ"
    if str(extract_img_proj) not in sys.path:
        sys.path.insert(0, str(extract_img_proj))
    from cache_system import ImageCacheSystem

# Try to import UnimerNet functionality
try:
    # Add UNIMERNET_PROJ to path
    unimernet_proj_path = current_dir / "UNIMERNET_PROJ"
    if str(unimernet_proj_path) not in sys.path:
        sys.path.insert(0, str(unimernet_proj_path))
    
    # Import UnimerNet with improved configuration
    from unimernet_model import UnimernetModel
    from mineru_config import config as mineru_config
    UNIMERNET_AVAILABLE = True
    logger.info("UnimerNet processor imported successfully")
except ImportError as e:
    logger.error(f"Failed to import UnimerNet processor: {e}")
    UNIMERNET_AVAILABLE = False

class UnimerNetProcessor:
    """
    Standalone UnimerNet processor for mathematical formulas and tables.
    """
    
    def __init__(self, use_cache: bool = True):
        """
        Initialize the UnimerNet processor.
        
        Args:
            use_cache: Whether to use the centralized cache system
        """
        self.use_cache = use_cache
        if use_cache:
            self.cache_system = ImageCacheSystem()
        else:
            self.cache_system = None
        
        # Initialize UnimerNet model
        self.unimernet_model = None
        if UNIMERNET_AVAILABLE:
            try:
                self.unimernet_model = UnimernetModel()
                logger.info("UnimerNet model initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize UnimerNet: {e}")
                self.unimernet_model = None
    
    def is_available(self) -> bool:
        """Check if UnimerNet is available and properly initialized."""
        return self.unimernet_model is not None
    
    def recognize_formula(self, image_path: str, force_reprocess: bool = False) -> Dict[str, Any]:
        """
        Recognize mathematical formula from image.
        
        Args:
            image_path: Path to the image file
            force_reprocess: Force reprocessing even if cached
            
        Returns:
            Dictionary with recognition results
        """
        return self.recognize_image(image_path, "formula", force_reprocess)
    
    def recognize_table(self, image_path: str, force_reprocess: bool = False) -> Dict[str, Any]:
        """
        Recognize table structure from image.
        
        Args:
            image_path: Path to the image file
            force_reprocess: Force reprocessing even if cached
            
        Returns:
            Dictionary with recognition results
        """
        return self.recognize_image(image_path, "table", force_reprocess)
    
    def recognize_image(self, image_path: str, content_type: str = "auto", 
                       force_reprocess: bool = False) -> Dict[str, Any]:
        """
        Recognize content from image using UnimerNet.
        
        Args:
            image_path: Path to the image file
            content_type: Type of content ('formula', 'table', 'auto')
            force_reprocess: Force reprocessing even if cached
            
        Returns:
            Dictionary with recognition results
        """
        image_path = Path(image_path)
        
        if not image_path.exists():
            return {
                "success": False,
                "error": f"Image file not found: {image_path}",
                "timestamp": datetime.now().isoformat()
            }
        
        if not self.is_available():
            return {
                "success": False,
                "error": "UnimerNet processor not available",
                "timestamp": datetime.now().isoformat()
            }
        
        # Read image data for caching
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
        if self.use_cache and not force_reprocess:
            cached_result = self.cache_system.get_cached_description(image_data)
            if cached_result:
                logger.info(f"Using cached result for {image_path.name}")
                return {
                    "success": True,
                    "result": cached_result,
                    "image_path": str(image_path),
                    "content_type": "cached",
                    "processor": "unimernet",
                    "timestamp": datetime.now().isoformat(),
                    "from_cache": True
                }
        
        # Process with UnimerNet
        try:
            logger.info(f"Processing {image_path.name} with UnimerNet")
            result = self._process_with_unimernet(image_path)
            
            if result and result.strip():
                # Cache the result
                if self.use_cache:
                    self.cache_system.store_image_and_description(
                        image_data, result, str(image_path)
                    )
                
                return {
                    "success": True,
                    "result": result,
                    "image_path": str(image_path),
                    "content_type": content_type,
                    "processor": "unimernet",
                    "timestamp": datetime.now().isoformat(),
                    "from_cache": False
                }
            else:
                return {
                    "success": False,
                    "error": "UnimerNet returned empty result",
                    "image_path": str(image_path),
                    "timestamp": datetime.now().isoformat()
                }
        
        except Exception as e:
            logger.error(f"UnimerNet processing failed: {e}")
            return {
                "success": False,
                "error": f"UnimerNet processing failed: {e}",
                "image_path": str(image_path),
                "timestamp": datetime.now().isoformat()
            }
    
    def _process_with_unimernet(self, image_path: Path) -> Optional[str]:
        """
        Internal method to process image with UnimerNet.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Processing result or None if failed
        """
        try:
            from PIL import Image
            # Load image
            image = Image.open(image_path).convert('RGB')
            
            # Use the improved UnimerNet model
            result = self.unimernet_model.predict_single_image(image)
            
            if result and result.strip():
                return result
        except Exception as e:
            logger.warning(f"UnimerNet processing failed: {e}")
        
        return None
    
    def batch_recognize(self, image_paths: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Process multiple images in batch.
        
        Args:
            image_paths: List of image file paths
            **kwargs: Additional arguments for recognize_image
            
        Returns:
            List of recognition results
        """
        results = []
        
        for image_path in image_paths:
            result = self.recognize_image(image_path, **kwargs)
            results.append(result)
        
        return results
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self.use_cache:
            return self.cache_system.get_cache_stats()
        else:
            return {"cache_disabled": True}

def main():
    """Command line interface for UNIMERNET."""
    parser = argparse.ArgumentParser(description="UNIMERNET - UnimerNet Formula and Table Recognition Tool")
    
    parser.add_argument("image_path", nargs="?", help="Path to image file")
    parser.add_argument("--type", choices=["formula", "table", "auto"], 
                       default="auto", help="Content type hint")
    parser.add_argument("--force", action="store_true", 
                       help="Force reprocessing even if cached")
    parser.add_argument("--batch", nargs="+", help="Process multiple images")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--check", action="store_true", help="Check if UnimerNet is available")
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = UnimerNetProcessor(use_cache=not args.no_cache)
    
    # Check availability if requested
    if args.check:
        if processor.is_available():
            print("✅ UnimerNet is available and ready")
            if not args.no_cache:
                stats = processor.get_cache_stats()
                print(f"Cache: {stats.get('total_images', 0)} images cached")
        else:
            print("❌ UnimerNet is not available")
            print("Please ensure UnimerNet dependencies are installed")
        return
    
    # Show cache statistics if requested
    if args.stats:
        stats = processor.get_cache_stats()
        if stats.get('cache_disabled'):
            print("Cache is disabled")
        else:
            print("Cache Statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        return
    
    # Process images
    if args.batch:
        # Batch processing
        results = processor.batch_recognize(
            args.batch,
            content_type=args.type,
            force_reprocess=args.force
        )
        
        if args.json:
            output = {"batch_results": results}
            print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            for i, result in enumerate(results):
                print(f"\n--- Image {i+1}: {result.get('image_path', 'Unknown')} ---")
                if result.get('success'):
                    print(f"Type: {result.get('content_type', 'Unknown')}")
                    print(f"From cache: {result.get('from_cache', False)}")
                    print(f"Result: {result.get('result', 'No result')}")
                else:
                    print(f"Error: {result.get('error', 'Unknown error')}")
    elif args.image_path:
        # Single image processing
        result = processor.recognize_image(
            args.image_path,
            content_type=args.type,
            force_reprocess=args.force
        )
        
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            if result.get('success'):
                print(f"Image: {result.get('image_path', 'Unknown')}")
                print(f"Type: {result.get('content_type', 'Unknown')}")
                print(f"From cache: {result.get('from_cache', False)}")
                print(f"\nResult:\n{result.get('result', 'No result')}")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")
    else:
        parser.print_help()
        return
    
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