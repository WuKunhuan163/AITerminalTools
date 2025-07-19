#!/usr/bin/env python3
"""
UnimerNet Model Wrapper
Extracted and adapted from MinerU for standalone usage with improved configuration
"""

import torch
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm
from pathlib import Path
import sys

# Add current directory to path for imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import MinerU configuration
from mineru_config import config as mineru_config

class MathDataset(Dataset):
    """Dataset for mathematical images."""
    
    def __init__(self, image_paths, transform=None):
        self.image_paths = image_paths
        self.transform = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        raw_image = self.image_paths[idx]
        if self.transform:
            image = self.transform(raw_image)
            return image
        return raw_image

class UnimernetModel(object):
    """
    UnimerNet model wrapper for mathematical formula and table recognition.
    Adapted from MinerU implementation.
    """
    
    def __init__(self, weight_dir=None, _device_=None):
        """
        Initialize UnimerNet model with improved configuration.
        
        Args:
            weight_dir: Path to model weights directory (optional, uses config if not provided)
            _device_: Device to run model on (optional, uses config if not provided)
        """
        try:
            # Use configuration if not provided
            if weight_dir is None:
                weight_dir = mineru_config.get_model_path()
            if _device_ is None:
                _device_ = mineru_config.device
            
            # Import the HuggingFace model using the same approach as MinerU
            from unimernet_hf import UnimernetModel as HFUnimernetModel
            
            print(f"🔄 Loading UnimerNet from {weight_dir}")
            print(f"📱 Using device: {_device_}")
            
            # Get attention implementation from config
            attention_impl = mineru_config.get_attention_implementation()
            
            # Load model with appropriate attention implementation
            if attention_impl == "eager":
                self.model = HFUnimernetModel.from_pretrained(weight_dir, attn_implementation="eager")
            else:
                self.model = HFUnimernetModel.from_pretrained(weight_dir)
            
            self.device = _device_
            self.model.to(_device_)
            
            # Use appropriate dtype based on device
            if mineru_config.should_use_float16():
                self.model = self.model.to(dtype=mineru_config.get_model_dtype())
            
            self.model.eval()
            print(f"✅ UnimerNet model loaded on {_device_}")
            
        except ImportError as e:
            print(f"❌ Failed to import UnimerNet HF model: {e}")
            raise
        except Exception as e:
            print(f"❌ Failed to load UnimerNet model: {e}")
            raise

    def predict(self, mfd_res, image):
        """
        Predict formulas from MFD (Mathematical Formula Detection) results.
        
        Args:
            mfd_res: MFD detection results with bounding boxes
            image: Input image
            
        Returns:
            List of formula predictions with LaTeX output
        """
        formula_list = []
        mf_image_list = []
        
        for xyxy, conf, cla in zip(
            mfd_res.boxes.xyxy.cpu(), mfd_res.boxes.conf.cpu(), mfd_res.boxes.cls.cpu()
        ):
            xmin, ymin, xmax, ymax = [int(p.item()) for p in xyxy]
            new_item = {
                "category_id": 13 + int(cla.item()),
                "poly": [xmin, ymin, xmax, ymin, xmax, ymax, xmin, ymax],
                "score": round(float(conf.item()), 2),
                "latex": "",
            }
            formula_list.append(new_item)
            bbox_img = image[ymin:ymax, xmin:xmax]
            mf_image_list.append(bbox_img)

        dataset = MathDataset(mf_image_list, transform=self.model.transform)
        dataloader = DataLoader(dataset, batch_size=32, num_workers=0)
        mfr_res = []
        
        for mf_img in dataloader:
            mf_img = mf_img.to(dtype=self.model.dtype)
            mf_img = mf_img.to(self.device)
            with torch.no_grad():
                output = self.model.generate({"image": mf_img})
            mfr_res.extend(output["fixed_str"])
            
        for res, latex in zip(formula_list, mfr_res):
            res["latex"] = latex
            
        return formula_list

    def batch_predict(self, images_mfd_res: list, images: list, batch_size: int = 64) -> list:
        """
        Batch prediction for multiple images.
        
        Args:
            images_mfd_res: List of MFD results for each image
            images: List of input images
            batch_size: Batch size for processing
            
        Returns:
            List of formula predictions for each image
        """
        images_formula_list = []
        mf_image_list = []
        backfill_list = []
        image_info = []  # Store (area, original_index, image) tuples

        # Collect images with their original indices
        for image_index in range(len(images_mfd_res)):
            mfd_res = images_mfd_res[image_index]
            pil_img = images[image_index]
            formula_list = []

            for idx, (xyxy, conf, cla) in enumerate(zip(
                    mfd_res.boxes.xyxy, mfd_res.boxes.conf, mfd_res.boxes.cls
            )):
                xmin, ymin, xmax, ymax = [int(p.item()) for p in xyxy]
                new_item = {
                    "category_id": 13 + int(cla.item()),
                    "poly": [xmin, ymin, xmax, ymin, xmax, ymax, xmin, ymax],
                    "score": round(float(conf.item()), 2),
                    "latex": "",
                }
                formula_list.append(new_item)
                bbox_img = pil_img.crop((xmin, ymin, xmax, ymax))
                area = (xmax - xmin) * (ymax - ymin)

                curr_idx = len(mf_image_list)
                image_info.append((area, curr_idx, bbox_img))
                mf_image_list.append(bbox_img)

            images_formula_list.append(formula_list)
            backfill_list += formula_list

        # Stable sort by area
        image_info.sort(key=lambda x: x[0])  # sort by area
        sorted_indices = [x[1] for x in image_info]
        sorted_images = [x[2] for x in image_info]

        # Create mapping for results
        index_mapping = {new_idx: old_idx for new_idx, old_idx in enumerate(sorted_indices)}

        # Create dataset with sorted images
        dataset = MathDataset(sorted_images, transform=self.model.transform)
        dataloader = DataLoader(dataset, batch_size=batch_size, num_workers=0)

        # Process batches and store results
        mfr_res = []

        with tqdm(total=len(sorted_images), desc="MFR Predict") as pbar:
            for index, mf_img in enumerate(dataloader):
                mf_img = mf_img.to(dtype=self.model.dtype)
                mf_img = mf_img.to(self.device)
                with torch.no_grad():
                    output = self.model.generate({"image": mf_img})
                mfr_res.extend(output["fixed_str"])

                # Update progress bar
                current_batch_size = min(batch_size, len(sorted_images) - index * batch_size)
                pbar.update(current_batch_size)

        # Restore original order
        unsorted_results = [""] * len(mfr_res)
        for new_idx, latex in enumerate(mfr_res):
            original_idx = index_mapping[new_idx]
            unsorted_results[original_idx] = latex

        # Fill results back
        for res, latex in zip(backfill_list, unsorted_results):
            res["latex"] = latex

        return images_formula_list

    def predict_single_image(self, image):
        """
        Predict formula from a single image without MFD preprocessing.
        
        Args:
            image: PIL Image or image array
            
        Returns:
            Recognition result string
        """
        try:
            # Create dataset with single image
            dataset = MathDataset([image], transform=self.model.transform)
            
            # Process the image
            with torch.no_grad():
                # Get the transformed image
                transformed_image = dataset[0].unsqueeze(0)  # Add batch dimension
                transformed_image = transformed_image.to(dtype=self.model.dtype)
                transformed_image = transformed_image.to(self.device)
                
                # Generate result
                output = self.model.generate({"image": transformed_image})
                
                # Extract the result
                if "fixed_str" in output and len(output["fixed_str"]) > 0:
                    return output["fixed_str"][0]
                else:
                    return None
                    
        except Exception as e:
            print(f"❌ Single image prediction failed: {e}")
            return None 