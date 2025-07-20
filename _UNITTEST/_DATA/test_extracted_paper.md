# GaussianObject: High-!ality 3D Object Reconstruction from Four Views with Gaussian Spla"ing

CHEN YANG∗ , MoE Key Lab of Artificial Intelligence, AI Institute, SJTU, China   
SIKUANG LI∗ , MoE Key Lab of Artificial Intelligence, AI Institute, SJTU, China   
JIEMIN FANG†, Huawei Inc., China   
RUOFAN LIANG, University of Toronto, Canada   
LINGXI XIE, Huawei Inc., China   
XIAOPENG ZHANG, Huawei Inc., China   
WEI SHEN‡, MoE Key Lab of Artificial Intelligence, AI Institute, SJTU, China   
QI TIAN, Huawei Inc., China

[placeholder: image]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/f4cd9a3ff84d91d075920ece838ca96f7a4344b466805a78f03ceb0b3ce11fb7.jpg)

[description: --- 图像分析结果 ---

Here's an analysis of the provided scientific image:

**1. Type of Plot/Figure:**

The figure is a comparative visualization of novel 3D reconstruction methods.  It's a combination of images and quantitative metrics displayed in a table-like format. Each row shows the reconstruction results for a different object (a bulldozer and a bonsai tree) using various techniques.


**2. Main Finding/Conclusion:**

The figure demonstrates the superior performance of the "Ours" method (f) in reconstructing 3D objects compared to other state-of-the-art methods (DietNeRF, FreeNeRF, and 3DGS).  This superiority is quantified using Peak Signal-to-Noise Ratio (PSNR) and Learned Perceptual Image Patch Similarity (LPIPS). Higher PSNR values and lower LPIPS values indicate better reconstruction quality.


**3. Key Data Points/Significant Numbers:**

* **Bulldozer:**
    * Ours (f): PSNR = 25.6 dB, LPIPS = 0.05
    * 3DGS (e): PSNR = 18.2 dB, LPIPS = 0.16
    * FreeNeRF (d): PSNR = 22.6 dB, LPIPS = 0.08
    * DietNeRF (c): PSNR = 17.7 dB, LPIPS = 0.15
* **Bonsai Tree:**
    * Ours (f): PSNR = 25.5 dB, LPIPS = 0.05
    * 3DGS (e): PSNR = 11.9 dB, LPIPS = 0.32
    * FreeNeRF (d): PSNR = 8.17 dB, LPIPS = 0.28
    * DietNeRF (c): PSNR = 15.7 dB, LPIPS = 0.17

**4. Trend/Relationship:**

The figure shows a clear trend: the "Ours" method consistently achieves significantly higher PSNR values and considerably lower LPIPS values than the other methods for both objects. This indicates that "Ours" produces more accurate and perceptually more similar reconstructions to the ground truth images (b).  The other methods exhibit varying degrees of success, suggesting different strengths and weaknesses in their respective approaches to 3D reconstruction.  There is a clear inverse relationship between PSNR and LPIPS across all methods, with higher PSNR corresponding to lower LPIPS.


--------------------]  
Fig. 1. We introduce GaussianObject, a framework capable of reconstructing high-quality 3D objects from only 4 images with Gaussian spla"ing. GaussianObject demonstrates superior performance over previous state-of-the-art (SOTA) methods on challenging objects.

Reconstructing and rendering 3D objects from highly sparse views is of critical importance for promoting applications of 3D vision techniques and improving user experience. However, images from sparse views only contain very limited 3D information, leading to two signi!cant challenges: 1) Di"- culty in building multi-view consistency as images for matching are too few; 2) Partially omitted or highly compressed object information as view coverage is insu"cient. To tackle these challenges, we propose GaussianObject, a framework to represent and render the 3D object with Gaussian splatting that achieves high rendering quality with only 4 input images. We !rst introduce techniques of visual hull and #oater elimination, which explicitly inject structure priors into the initial optimization process to help build multi-view consistency, yielding a coarse 3D Gaussian representation. Then we construct a Gaussian repair model based on di\$usion models to supplement the omitted object information, where Gaussians are further re!ned. We design a self-generating strategy to obtain image pairs for training the repair model. We further design a COLMAP-free variant, where pre-given accurate camera poses are not required, which achieves competitive quality and facilitates wider applications. GaussianObject is evaluated on several challenging datasets, including MipNeRF360, OmniObject3D, OpenIllumination, and our-collected unposed images, achieving superior performance from only four views and signi!cantly outperforming previous SOTA methods. Our demo is available at https:// gaussianobject.github.io/ , and the code has been released at https:// github.com/ GaussianObject/ GaussianObject.

# CCS Concepts: • Computing methodologies → Reconstruction; Rendering; Point-based models.

Additional Key Words and Phrases: Sparse view reconstruction, 3D Gaussian Splatting, ControlNet, Visual hull, Novel view synthesis

# ACM Reference Format:

Chen Yang, Sikuang Li, Jiemin Fang, Ruofan Liang, Lingxi Xie, Xiaopeng Zhang, Wei Shen, and Qi Tian. 2024. GaussianObject: High-Quality 3D Object