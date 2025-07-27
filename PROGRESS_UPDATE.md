# GaussianObject Reproduction Progress

## Project Overview
Reproducing the GaussianObject paper: "High-Quality 3D Object Reconstruction from Four Views with Gaussian Splatting" (SIGGRAPH Asia 2024)

## Current Status: Dependencies Installation 🔄

### Completed Tasks:
1. ✅ **Environment Setup**
   - Repository cloned with submodules
   - Python environment: Using system Python 3.11.13 in Colab
   - Working directory: ~/GaussianObject

2. ✅ **Model Downloads**
   - Stable Diffusion v1.5 and ControlNet models downloaded
   - SAM model downloaded (sam_vit_h_4b8939.pth)
   - DUSt3R model downloaded (DUSt3R_ViTLarge_BaseDecoder_512_dpt.pth)
   - MASt3R model downloaded (MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth)

3. ✅ **Dataset Preparation**
   - Available datasets: `realcap/rabbit` (4 images: 001.png-004.png) and `test_object`
   - Basic dataset structure in place
   - Training configuration: sparse_4.txt and sparse_test.txt ready

4. 🔄 **Dependencies Installation** (In Progress)
   - ✅ Basic pip packages installed: camtools, einops, lpips, tensorboard, tqdm, transformers, omegaconf, open-clip-torch, open3d, opencv-python, Pillow, plyfile, pytorch-lightning, PyYAML, ipykernel, trimesh, roma
   - ✅ CLIP submodule installed successfully
   - ✅ segment-anything submodule installed successfully  
   - ✅ simple-knn submodule installed successfully
   - 🔄 pytorch3d submodule installing (in progress)
   - ❌ diff-gaussian-rasterization failed (CUDA compilation issue)
   - ❌ diff-gaussian-rasterization-w-pose not attempted yet

### Next Steps (Pending):
1. 🔄 **Complete Dependencies Installation**
   - Finish pytorch3d installation
   - Attempt diff-gaussian-rasterization installation
   - Install remaining submodules (minLoRA)

2. 🔄 **Pipeline Execution**
   - Generate camera poses using DUSt3R: `python3 pred_poses.py -s data/realcap/rabbit --sparse_num 4`
   - Run visual hull generation
   - Train coarse 3DGS representation
   - Execute leave-one-out strategy
   - Fine-tune LoRA model
   - Run Gaussian repair

3. 🔄 **Visualization & Results**
   - Generate test renderings
   - Create path renderings
   - Save results to _TAKEAWAY folder

### Environment Details:
- **Python**: /usr/bin/python3 (Python 3.11.13)
- **Platform**: Google Colab Linux environment
- **CUDA**: Available but some extensions require compilation
- **Virtual Environment**: Not used (system Python in Colab)

### Current Issues:
1. CUDA extensions compilation: diff-gaussian-rasterization failed to compile
2. Runtime changes: Colab runtime resets require dependency reinstallation

### Available Datasets:
- `data/realcap/rabbit/` - Real captured rabbit object (4 images)
- `data/test_object/` - Test object dataset (empty)

### Output Structure (To be created):
- `output/gs_init/` - Initial Gaussian splatting results
- `output/controlnet_finetune/` - LoRA fine-tuned models
- `output/gaussian_object/` - Final repaired models
- `_TAKEAWAY/results/` - Final visualization results

## Next Action Required:
Complete pytorch3d installation, then attempt pose generation for rabbit dataset. 