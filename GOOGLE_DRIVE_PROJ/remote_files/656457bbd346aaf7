# GaussianObject Reproduction Progress

## Project Overview
Reproducing the GaussianObject paper: "High-Quality 3D Object Reconstruction from Four Views with Gaussian Splatting" (SIGGRAPH Asia 2024)

## Current Status: Initial Setup Complete ✅

### Completed Tasks:
1. ✅ **Environment Setup**
   - Repository cloned with submodules
   - Python environment configured
   - Required dependencies installed

2. ✅ **Model Downloads**
   - Stable Diffusion v1.5 and ControlNet models downloaded
   - SAM model downloaded (sam_vit_h_4b8939.pth)
   - DUSt3R model downloaded (DUSt3R_ViTLarge_BaseDecoder_512_dpt.pth)
   - MASt3R model downloaded (MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth)

3. ✅ **Dataset Preparation**
   - Available datasets: `realcap/rabbit` and `test_object`
   - Basic dataset structure in place

### Next Steps (Pending):
1. 🔄 **Dataset Processing**
   - Generate masks using SAM for test_object dataset
   - Generate depth maps using monocular depth estimation
   - Prepare proper dataset structure

2. 🔄 **Pipeline Execution**
   - Generate camera poses using DUSt3R/MASt3R
   - Run visual hull generation
   - Train coarse 3DGS representation
   - Execute leave-one-out strategy
   - Fine-tune LoRA model
   - Run Gaussian repair

3. 🔄 **Visualization & Results**
   - Generate test renderings
   - Create path renderings
   - Save results to _TAKEAWAY folder

### Available Datasets:
- `data/realcap/rabbit/` - Real captured rabbit object (4 images)
- `data/test_object/` - Test object dataset

### Output Structure (To be created):
- `output/gs_init/` - Initial Gaussian splatting results
- `output/controlnet_finetune/` - LoRA fine-tuned models
- `output/gaussian_object/` - Final repaired models
- `_TAKEAWAY/results/` - Final visualization results

## Next Action Required:
Start with the test_object dataset processing and run the complete pipeline. 