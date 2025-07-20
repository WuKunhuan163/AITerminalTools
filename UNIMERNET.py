#!/usr/bin/env python3
"""
UNIMERNET - UnimerNet Formula and Table Recognition Tool
Based on MinerU's UnimerNet implementation for high-accuracy mathematical formula and table recognition.
"""

import os
import sys
import json
import argparse
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def is_run_environment(command_identifier=None):
    """Check if running in RUN environment by checking environment variables"""
    if command_identifier:
        return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
    return False

# Add UNIMERNET_PROJ to path
UNIMERNET_PROJ_PATH = Path(__file__).parent / "UNIMERNET_PROJ"
sys.path.insert(0, str(UNIMERNET_PROJ_PATH))

# Add EXTRACT_IMG_PROJ for cache system
EXTRACT_IMG_PROJ_PATH = Path(__file__).parent / "EXTRACT_IMG_PROJ"
if str(EXTRACT_IMG_PROJ_PATH) not in sys.path:
    sys.path.insert(0, str(EXTRACT_IMG_PROJ_PATH))

try:
    # Import centralized cache system
    from cache_system import ImageCacheSystem
    CACHE_AVAILABLE = True
except ImportError:
    print("Warning: Centralized cache system not available", file=sys.stderr)
    CACHE_AVAILABLE = False

# Lazy import for UnimerNet model components
UNIMERNET_AVAILABLE = None
load_unimernet_model = None
simple_recognize = None

def _lazy_import_unimernet():
    """Lazy import UnimerNet components only when needed"""
    global UNIMERNET_AVAILABLE, load_unimernet_model, simple_recognize
    if UNIMERNET_AVAILABLE is None:
        try:
            from test_simple_unimernet import load_unimernet_model, recognize_image as simple_recognize
            UNIMERNET_AVAILABLE = True
        except ImportError:
            print("Warning: UnimerNet model components not available", file=sys.stderr)
            UNIMERNET_AVAILABLE = False
    return UNIMERNET_AVAILABLE

class UnimerNetProcessor:
    """UnimerNet processor using simplified unimernet interface"""
    
    def __init__(self):
        # Initialize cache system
        if CACHE_AVAILABLE:
            # Use EXTRACT_IMG_PROJ as base directory for cache system
            extract_img_proj_dir = Path(__file__).parent / "EXTRACT_IMG_PROJ"
            self.cache_system = ImageCacheSystem(base_dir=extract_img_proj_dir)
        else:
            self.cache_system = None
        
        # Initialize UnimerNet model (lazy loading)
        self.model = None
        self.tokenizer = None
        self._model_loaded = False
    
    def _init_unimernet_model(self):
        """Initialize UnimerNet model using simplified interface"""
        if not _lazy_import_unimernet():
            print("Warning: UnimerNet components not available", file=sys.stderr)
            return
        
        try:
            # Determine device - check environment first
            import torch
            device = os.environ.get('MINERU_DEVICE_MODE')
            if device is None:
                if torch.cuda.is_available():
                    device = "cuda"
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    device = "mps"
                else:
                    device = "cpu"
            
            # Load model
            self.model, self.tokenizer = load_unimernet_model(device=device)
            
        except Exception as e:
            print(f"Warning: Failed to initialize UnimerNet model: {e}", file=sys.stderr)
            self.model = None
            self.tokenizer = None
    
    def is_available(self) -> bool:
        """Check if UnimerNet is available and ready"""
        return self.model is not None
    
    def recognize_image(self, image_path: str, content_type: str = "auto", use_cache: bool = True, force: bool = False) -> Dict[str, Any]:
        """
        Recognize formula or table from image using MinerU's UnimerNet.
        
        Args:
            image_path: Path to the image file
            content_type: Type of content ("formula", "table", "auto")
            use_cache: Whether to use cache system
            force: Force reprocessing even if cached
            
        Returns:
            Recognition result dictionary
        """
        
        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"Image file not found: {image_path}"
            }
        
        # Check cache first
        if use_cache and not force and self.cache_system:
            try:
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                cached_description = self.cache_system.get_cached_description(image_data)
                if cached_description:
                    return {
                        "success": True,
                        "result": cached_description,
                        "image_path": image_path,
                        "content_type": "auto",  # We don't store content type in cache
                        "processor": "unimernet",
                        "timestamp": datetime.now().isoformat(),
                        "from_cache": True
                    }
            except Exception as e:
                print(f"Warning: Cache check failed: {e}", file=sys.stderr)
        
        # Load model only when needed (lazy loading)
        if not self._model_loaded:
            self._init_unimernet_model()
            self._model_loaded = True
        
        if not self.is_available():
            return {
                "success": False,
                "error": "UnimerNet is not available. Please check MinerU installation."
            }
        
        try:
            # Use simplified recognition interface
            result_text = simple_recognize(image_path, self.model, self.tokenizer)
            
            if result_text is None:
                return {
                    "success": False,
                    "error": "UnimerNet recognition failed - no result returned"
                }
            
            # Auto-detect content type if needed (simplified heuristic)
            if content_type == "auto":
                # Simple heuristic: if result contains table-like patterns, it's a table
                if "|" in result_text or "\\begin{array}" in result_text or "\\begin{tabular}" in result_text:
                    content_type = "table"
                else:
                    content_type = "formula"
            
            # Prepare result
            result = {
                "success": True,
                "result": result_text,
                "image_path": image_path,
                "content_type": content_type,
                "processor": "unimernet",
                "timestamp": datetime.now().isoformat(),
                "from_cache": False
            }
            
            # Cache the result
            if use_cache and self.cache_system:
                try:
                    with open(image_path, 'rb') as f:
                        image_data = f.read()
                    self.cache_system.store_image_and_description(
                        image_data, 
                        result_text
                    )
                except Exception as e:
                    print(f"Warning: Cache storage failed: {e}", file=sys.stderr)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"UnimerNet processing failed: {str(e)}"
            }
    

    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.cache_system:
            return {"cache_available": False}
        
        return self.cache_system.get_cache_stats()

def main():
    """Main CLI interface for UNIMERNET"""
    # 获取command_identifier
    args_list = sys.argv[1:]
    command_identifier = None
    
    # 检查是否被RUN调用（第一个参数是command_identifier）
    if args_list and is_run_environment(args_list[0]):
        command_identifier = args_list[0]
        args_list = args_list[1:]  # 移除command_identifier，保留实际参数
        # 重新构建sys.argv以供argparse使用
        sys.argv = [sys.argv[0]] + args_list
    
    parser = argparse.ArgumentParser(
        description="UNIMERNET - UnimerNet Formula and Table Recognition Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("image_path", nargs="?", help="Path to image file")
    parser.add_argument("--type", choices=["formula", "table", "auto"], default="auto",
                       help="Content type hint (default: auto)")
    parser.add_argument("--force", action="store_true", help="Force reprocessing even if cached")
    parser.add_argument("--batch", action="store_true", help="Process multiple images")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--output", help="Specify a file to save the result")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--check", action="store_true", help="Check if UnimerNet is available")
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = UnimerNetProcessor()
    
    # Handle check command
    if args.check:
        # Check if components can be imported
        if _lazy_import_unimernet():
            print("✅ Local UnimerNet components loaded successfully")
            # Try to initialize model to check full availability
            try:
                processor._init_unimernet_model()
                processor._model_loaded = True
                if processor.is_available():
                    print("✅ UnimerNet is available and ready")
                else:
                    print("❌ UnimerNet model initialization failed")
            except Exception as e:
                print("❌ UnimerNet model initialization failed")
                print(f"Error: {e}")
            
            if processor.cache_system:
                stats = processor.get_cache_stats()
                if stats.get("cache_available"):
                    print(f"Cache: {stats.get('total_cached_images', 0)} images cached")
        else:
            print("❌ UnimerNet is not available")
            print("Please ensure MinerU dependencies are installed")
        return
    
    # Handle stats command
    if args.stats:
        stats = processor.get_cache_stats()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            if stats.get("cache_available"):
                print("Cache Statistics:")
                print(f"  Total cached images: {stats.get('total_cached_images', 0)}")
                print(f"  Cache directory: {stats.get('cache_dir', 'N/A')}")
            else:
                print("Cache system not available")
        return
    
    # Check if image path is provided
    if not args.image_path:
        parser.print_help()
        return
    
    # Process images
    use_cache = True  # Cache is always enabled, --force bypasses it
    
    if args.batch:
        # Process multiple images
        image_paths = args.image_path.split() if isinstance(args.image_path, str) else [args.image_path]
        results = []
        
        for image_path in image_paths:
            result = processor.recognize_image(
                image_path=image_path,
                content_type=args.type,
                use_cache=use_cache,
                force=args.force
            )
            results.append(result)
        
        # Output results
        if args.json or args.output:
            output_data = {"batch_results": results}
            output_text = json.dumps(output_data, indent=2)
        else:
            output_lines = []
            for result in results:
                if result.get("success"):
                    output_lines.append(f"Image: {result['image_path']}")
                    output_lines.append(f"Type: {result['content_type']}")
                    output_lines.append(f"From cache: {result.get('from_cache', False)}")
                    output_lines.append(f"Result: {result['result']}")
                    output_lines.append("")
                else:
                    output_lines.append(f"Error processing {result.get('image_path', 'unknown')}: {result.get('error', 'unknown error')}")
                    output_lines.append("")
            output_text = "\n".join(output_lines)
    
    else:
        # Process single image
        result = processor.recognize_image(
            image_path=args.image_path,
            content_type=args.type,
            use_cache=use_cache,
            force=args.force
        )
        
        # Output result
        # Use JSON format if explicitly requested, for file output, OR if running in RUN environment
        if args.json or args.output or is_run_environment(command_identifier):
            output_text = json.dumps(result, indent=2)
        else:
            if result.get("success"):
                output_text = f"""Image: {result['image_path']}
Type: {result['content_type']}
From cache: {result.get('from_cache', False)}

Result:
{result['result']}"""
            else:
                output_text = f"Error: {result.get('error', 'unknown error')}"
    
    # Save to file if specified
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_text)
        print(f"Results saved to {args.output}")
    else:
        print(output_text)

if __name__ == "__main__":
    main() 