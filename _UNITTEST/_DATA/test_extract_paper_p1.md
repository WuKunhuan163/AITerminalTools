# Page 1

[placeholder: image]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_DATA/images/326bbc74999734fc6322d01c4b7a24ea.png)

GaussianObject: High-!ality 3D Object Reconstruction from Four Views with Gaussian Spla"ing CHEN YANG∗, MoE Key Lab of Artificial Intelligence, AI Institute, SJTU, China SIKUANG LI∗, MoE Key Lab of Artificial Intelligence, AI Institute, SJTU, China JIEMIN FANG†, Huawei Inc., China RUOFAN LIANG, University of Toronto, Canada LINGXI XIE, Huawei Inc., China XIAOPENG ZHANG, Huawei Inc., China WEI SHEN‡, MoE Key Lab of Artificial Intelligence, AI Institute, SJTU, China QI TIAN, Huawei Inc., China (a) 4 Input Views (d) FreeNeRF (e) 3DGS (c) DietNeRF (f) Ours (b) Ground Truth 17.7 dB / 0.15 22.6 dB / 0.08 18.2 dB / 0.16 25.6 dB / 0.05 PSNR   / LPIPS 8.17dB / 0.28 11.9 dB / 0.32 15.7dB / 0.17 25.5 dB / 0.05 PSNR   / LPIPS Fig. 1. We introduce GaussianObject, a framework capable of reconstructing high-quality 3D objects from only 4 images with Gaussian spla"ing. Gaus- sianObject demonstrates superior performance over previous state-of-the-art (SOTA) methods on challenging objects.

Reconstructing and rendering 3D objects from highly sparse views is of critical importance for promoting applications of 3D vision techniques and improving user experience. However, images from sparse views only contain very limited 3D information, leading to two signi!cant challenges: 1) Di"- culty in building multi-view consistency as images for matching are too few;

2) Partially omitted or highly compressed object information as view cover- age is insu"cient. To tackle these challenges, we propose GaussianObject, a framework to represent and render the 3D object with Gaussian splatting that achieves high rendering quality with only 4 input images. We !rst ∗Equal contributions.

†Project lead.

‡Corresponding author.

Authors’ addresses: Chen Yang, MoE Key Lab of Arti!cial Intelligence, AI Institute, SJTU, Shanghai, China, ycyangchen@sjtu.edu.cn; Sikuang Li, MoE Key Lab of Arti!- cial Intelligence, AI Institute, SJTU, Shanghai, China, uranusits@sjtu.edu.cn; Jiemin Fang, Huawei Inc., Wuhan, China, jaminfong@gmail.com; Ruofan Liang, University of Toronto, Toronto, Canada, ruofan@cs.toronto.edu; Lingxi Xie, Huawei Inc., Bei- jing, China, 198808xc@gmail.com; Xiaopeng Zhang, Huawei Inc., Shanghai, China, zxphistory@gmail.com; Wei Shen, MoE Key Lab of Arti!cial Intelligence, AI Institute, SJTU, Shanghai, China, wei.shen@sjtu.edu.cn; Qi Tian, Huawei Inc., Shenzhen, China, tian.qi1@huawei.com.

2024. ACM 0730-0301/2024/12-ART https://doi.org/10.1145/3687759 introduce techniques of visual hull and #oater elimination, which explicitly inject structure priors into the initial optimization process to help build multi-view consistency, yielding a coarse 3D Gaussian representation. Then we construct a Gaussian repair model based on di$usion models to supple- ment the omitted object information, where Gaussians are further re!ned.

We design a self-generating strategy to obtain image pairs for training the repair model. We further design a COLMAP-free variant, where pre-given accurate camera poses are not required, which achieves competitive quality and facilitates wider applications. GaussianObject is evaluated on several challenging datasets, including MipNeRF360, OmniObject3D, OpenIllumi- nation, and our-collected unposed images, achieving superior performance from only four views and signi!cantly outperforming previous SOTA meth- ods. Our demo is available at https://gaussianobject.github.io/, and the code has been released at https://github.com/GaussianObject/GaussianObject.

CCS Concepts: • Computing methodologies →Reconstruction; Ren- dering; Point-based models.

Additional Key Words and Phrases: Sparse view reconstruction, 3D Gaussian Splatting, ControlNet, Visual hull, Novel view synthesis ACM Reference Format:

Chen Yang, Sikuang Li, Jiemin Fang, Ruofan Liang, Lingxi Xie, Xiaopeng Zhang, Wei Shen, and Qi Tian. 2024. GaussianObject: High-Quality 3D Object ACM Trans. Graph., Vol. 43, No. 6, Article . Publication date: December 2024.

arXiv:2402.10259v4  [cs.CV]  13 Nov 2024


