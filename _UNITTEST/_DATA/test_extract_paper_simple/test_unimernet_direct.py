#!/usr/bin/env python3
"""
Direct test of UnimerNet model loading and usage
"""
import sys
import os
from pathlib import Path

# Add MinerU path
sys.path.insert(0, str(Path(__file__).parent.parent / "pdf_extractor_MinerU"))

try:
    from mineru.model.mfr.unimernet.Unimernet import UnimernetModel
    print("✅ Successfully imported UnimernetModel")
    
    # Try to load the model
    model_path = Path(__file__).parent.parent / "models" / "MFR" / "unimernet_hf_small_2503"
    if model_path.exists():
        print(f"✅ Model path exists: {model_path}")
        
        # Try to create model instance
        model = UnimernetModel(str(model_path), "cpu")
        print("✅ UnimerNet model loaded successfully!")
        
        # Test with an image
        test_image_path = "test1_data/images/405b819b14936c78a5cec55aafd90a4d01bfec70a20669c243f018728cb4c1a4.jpg"
        if Path(test_image_path).exists():
            print(f"✅ Test image exists: {test_image_path}")
            print("📝 Model loaded successfully, but full prediction requires additional setup")
        else:
            print(f"❌ Test image not found: {test_image_path}")
    else:
        print(f"❌ Model path not found: {model_path}")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
