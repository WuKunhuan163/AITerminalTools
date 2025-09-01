#!/usr/bin/env python3
"""
Simple UnimerNet Interface
Provides simple load_unimernet_model and recognize_image functions for standalone usage
"""

import os
import sys
import torch
from pathlib import Path
from PIL import Image
import numpy as np
from typing import Tuple, Optional

# Add current directory to path
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import local UnimerNet model components (copied from MinerU)
try:
    from Unimernet import UnimernetModel, MathDataset
    UNIMERNET_AVAILABLE = True
    print("Local UnimerNet components loaded successfully")
except ImportError as e:
    UNIMERNET_AVAILABLE = False
    print(f"Warning:  Local UnimerNet model components not available: {e}")

def load_unimernet_model(model_path: str = None, device: str = "cpu") -> Tuple[Optional[object], Optional[object]]:
    """
    Load UnimerNet model and tokenizer.
    
    Args:
        model_path: Path to the model directory (default: ./unimernet_models/unimernet_base)
        device: Device to load model on ("cpu", "cuda", "mps", etc.)
        
    Returns:
        Tuple of (model, tokenizer) or (None, None) if failed
    """
    if not UNIMERNET_AVAILABLE:
        print("Error:  UnimerNet model components not available")
        return None, None
    
    # Default model path - use local model first, then download if needed
    if model_path is None:
        # Try local model first
        local_model_path = current_dir / "unimernet_models" / "unimernet_hf_small_2503"
        
        if local_model_path.exists():
            model_path = local_model_path
            print(f"Using local model path: {model_path}")
        else:
            try:
                # Download the model if local doesn't exist
                from huggingface_hub import snapshot_download
                
                # Set environment variable to use huggingface
                os.environ.setdefault('MINERU_MODEL_SOURCE', 'huggingface')
                
                # Download the model directly from HuggingFace
                repo_id = "opendatalab/PDF-Extract-Kit-1.0"
                model_subpath = "models/MFR/unimernet_hf_small_2503"
                
                print(f"📥 Downloading model from {repo_id}...")
                cache_dir = snapshot_download(
                    repo_id=repo_id,
                    allow_patterns=[f"{model_subpath}/*"]
                )
                
                model_path = Path(cache_dir) / model_subpath
                print(f"Using downloaded model path: {model_path}")
                
                # Verify the model path exists
                if not model_path.exists():
                    raise FileNotFoundError(f"Model path does not exist: {model_path}")
                    
            except Exception as e:
                print(f"Error: Failed to download model: {e}")
                raise Exception("No valid UnimerNet model found")
    
    model_path = Path(model_path)
    
    if not model_path.exists():
        print(f"Error: Model path not found: {model_path}")
        return None, None
    
    try:
        print(f"🔄 Loading UnimerNet model from {model_path}")
        print(f"📱 Using device: {device}")
        
        # Apply CPU optimizations if using CPU
        if device.startswith("cpu"):
            try:
                from mineru_config import config
                config.apply_cpu_optimizations()
                print("🚀 Applied CPU optimizations for better performance")
            except Exception as e:
                print(f"Warning:  Failed to apply CPU optimizations: {e}")
        
        # Load the model
        model = UnimernetModel(str(model_path), device)
        
        # The tokenizer is embedded in the model for UnimerNet
        tokenizer = model.model.tokenizer if hasattr(model.model, 'tokenizer') else None
        
        print("UnimerNet model loaded successfully")
        return model, tokenizer
        
    except Exception as e:
        print(f"Error: Failed to load UnimerNet model: {e}")
        return None, None

def recognize_image(image_path: str, model: object, tokenizer: object = None) -> Optional[str]:
    """
    Recognize mathematical formula or table from image.
    
    Args:
        image_path: Path to the image file
        model: Loaded UnimerNet model
        tokenizer: Tokenizer (optional, embedded in model)
        
    Returns:
        Recognition result as string, or None if failed
    """
    if model is None:
        print("Error:  Model not loaded")
        return None
    
    image_path = Path(image_path)
    if not image_path.exists():
        print(f"Error: Image not found: {image_path}")
        return None
    
    try:
        # Load and preprocess image
        image = Image.open(image_path)
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert PIL image to format expected by UnimerNet
        image_array = np.array(image)
        
        # Create a simple dataset with single image
        dataset = MathDataset([image], transform=model.model.transform)
        
        # Process the image
        with torch.no_grad():
            # Get the transformed image
            transformed_image = dataset[0].unsqueeze(0)  # Add batch dimension
            transformed_image = transformed_image.to(dtype=model.model.dtype)
            transformed_image = transformed_image.to(model.device)
            
            # Generate result
            output = model.model.generate({"image": transformed_image})
            
            # Extract the result
            if "fixed_str" in output and len(output["fixed_str"]) > 0:
                result = output["fixed_str"][0]
                print(f"Recognition successful: {result[:50]}...")
                return result
            else:
                print("⚠️  No recognition result")
                return None
                
    except Exception as e:
        print(f"Error: Recognition failed: {e}")
        return None

def test_unimernet_recognition():
    """Test function for UnimerNet recognition."""
    print("🧪 Testing UnimerNet recognition")
    
    # Load model
    model, tokenizer = load_unimernet_model()
    
    if model is None:
        print("Error:  Cannot test without model")
        return False
    
    # Test with a sample image (if available)
    test_image_path = current_dir / "test_images" / "formula_sample.png"
    
    if test_image_path.exists():
        result = recognize_image(str(test_image_path), model, tokenizer)
        if result:
            print(f"🎉 Test successful: {result}")
            return True
        else:
            print("Error:  Test failed: No recognition result")
            return False
    else:
        print(f"Warning:  Test image not found: {test_image_path}")
        print("ℹ️  Model loaded successfully but cannot test without sample image")
        return True

if __name__ == "__main__":
    # Run test
    test_unimernet_recognition() 