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

# Import the UnimerNet model components
try:
    # Add parent directory to path
    parent_dir = current_dir.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    from unimernet_model import UnimernetModel, MathDataset
    UNIMERNET_AVAILABLE = True
except ImportError:
    UNIMERNET_AVAILABLE = False
    print(f" UnimerNet model components not available")

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
        print(f"Error:  UnimerNet model components not available")
        return None, None
    
    # Default model path
    if model_path is None:
        model_path = current_dir.parent / "unimernet_models" / "unimernet_base"
    
    model_path = Path(model_path)
    
    if not model_path.exists():
        print(f"Error: Model path not found: {model_path}")
        return None, None
    
    try:
        print(f"Loading UnimerNet model from {model_path}")
        print(f"📱 Using device: {device}")
        
        # Load the model
        model = UnimernetModel(str(model_path), device)
        
        # The tokenizer is embedded in the model for UnimerNet
        tokenizer = model.model.tokenizer if hasattr(model.model, 'tokenizer') else None
        
        print(f"UnimerNet model loaded successfully")
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
        print(f"Error:  Model not loaded")
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
                print(f" No recognition result")
                return None
                
    except Exception as e:
        print(f"Error: Recognition failed: {e}")
        return None

def test_unimernet_recognition():
    """Test function for UnimerNet recognition."""
    print(f"Testing UnimerNet recognition")
    
    # Load model
    model, tokenizer = load_unimernet_model()
    
    if model is None:
        print(f"Error:  Cannot test without model")
        return False
    
    # Test with a sample image (if available)
    test_image_path = current_dir.parent / "test_images" / "formula_sample.png"
    
    if test_image_path.exists():
        result = recognize_image(str(test_image_path), model, tokenizer)
        if result:
            print(f"Test successful: {result}")
            return True
        else:
            print(f"Error:  Test failed: No recognition result")
            return False
    else:
        print(f"Warning:  Test image not found: {test_image_path}")
        print(f"Model loaded successfully but cannot test without sample image")
        return True

if __name__ == "__main__":
    # Run test
    test_unimernet_recognition() 