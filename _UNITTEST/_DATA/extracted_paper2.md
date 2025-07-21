# AutoPartGen: Autoregressive 3D Part Generation and Discovery

Minghao Chen1,2 Jianyuan Wang1,2 Roman Shapovalov2 Tom Monnier2 Hyunyoung Jung2 Dilin Wang2 Rakesh Ranjan2 Iro Laina2 Andrea Vedaldi1,2 1Visual Geometry Group, University of Oxford 2Meta AI

[placeholder: image]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/4119bdfa68e7f7d7609272dd16b96d703dd0f31d919d3a65abc398467b9f11a8.jpg)  
Figure 1: AutoPartGen can be applied, by itself or in combination with other models, to the generation of compositional 3D objects, scenes and cities starting from 3D models, images or text.

# Abstract

We introduce AutoPartGen, a model that generates objects composed of 3D parts in an autoregressive manner. This model can take as input an image of an object, 2D masks of the object’s parts, or an existing 3D object, and generate a corresponding compositional 3D reconstruction. Our approach builds upon 3DShape2VecSet, a recent latent 3D representation with powerful geometric expressiveness. We observe that this latent space exhibits strong compositional properties, making it particularly well-suited for part-based generation tasks. Specifically, AutoPartGen generates object parts autoregressively, predicting one part at a time while conditioning on previously generated parts and additional inputs, such as 2D images, masks, or 3D objects. This process continues until the model decides that all parts have been generated, thus determining automatically the type and number of parts. The resulting parts can be seamlessly assembled into coherent objects or scenes without requiring additional optimization. We evaluate both the overall 3D generation capabilities and the part-level generation quality of AutoPartGen, demonstrating that it achieves state-of-the-art performance in 3D part generation.

# 1 Introduction

Processing 3D objects, including generating them based on a textual description or an image, is an important aspect of Spatial Intelligence. Current 3D generators often treat objects or even entire scenes as monolithic shells. However, many applications require modeling their compositional structure, decomposing them into well-defined 3D parts to enable reasoning or manipulation at a finer granularity, such as applying textures and materials to each part separately. More specifically, a character in a video game should be decomposable into different parts to support animation or allow the game software to swap clothes or accessories. Windows and doors in the 3D model of a house need to be separate entities to allow user interaction, such as opening or closing them. Similarly, the design of a machine must consist of distinct parts to be functional (e.g., the cogs in a clock) or to enable 3D printing or other kinds of CNC manufacturing.

In this paper, we address the problem of generating 3D objects with a compositional structure. We introduce AutoPartGen, a new autoregressive model that can directly generate a 3D object part by part, building on a powerful latent 3D representation. AutoPartGen is robust, flexible, and scalable. As shown in Fig. 1, AutoPartGen can be applied, either independently or in combination with other models, to generate compositional 3D objects, scenes, or even cities, starting from 3D models, images, or text prompts. AutoPartGen solves three key problems to enable such applications: (i) object-to-parts, where it decomposes an existing 3D object into meaningful parts; (ii) image-to-parts, where the model generates 3D parts from an unstructured input image; and (iii) masks-to-parts, where users can provide 2D part masks to guide the generation. In the first two scenarios, AutoPartGen automatically predicts semantically meaningful 3D parts without requiring part annotations. In the third scenario, user-provided masks offer fine-grained control over the model partitioning.

Our autoregressive approach has two key benefits. First, it models the joint distribution over the object parts, ensuring that they fit together cohesively. Second, it enables the model to generate a variable number of parts, which is crucial since the number of parts is not fixed or known a priori.

We build AutoPartGen on recent advances in latent 3D representations and parameterize the 3D surface x ⊂ R3 of the object using a latent code vector z ∈ Rd. We use the 3DShape2VecSet representation [62, 30, 63] and observe, for the first time, that this representation is inherently compositional. Specifically, we show that the concatenation z = z(1) ⊕ z(2) of two codes z(1) and z(2) decodes into the union x = x(1) ∪ x(2) of the corresponding surfaces x(1) and x(2).

Based on this insight, we propose generating a sequence of latent codes z(1), . . . , z(K), each decoding into a corresponding 3D part x(k). Crucially, the generation of each part is conditioned on an overall latent representation of the target 3D object x as well as on all previously generated parts x(1), . . . , x(k−1). This conditioning improves the consistency of the generated parts, meaning that they better fit each other compared to the output of the methods that extract parts independently [5, 58].

As noted in [5], object decomposition is an ambiguous problem. For example, a chair might be decomposed into few high-level parts (e.g., seat, back, legs) or a more granular set of components (e.g., individual leg segments, cushion, backrest slats). This choice typically depends on the application or the preferences of the 3D artist creating the asset. We address this ambiguity by making the 3D autoregressive model stochastic, using denoising diffusion to generate the next part vector z(k) based on the previously generated parts z(1), . , z(k−1) and the available evidence (i.e., the full 3D object, an image of the object, or 2D part masks, depending on the application). Importantly, we train a single diffusion model capable of handling all three cases.

We evaluate AutoPartGen against state-of-the-art part-aware 3D generators. Compared to the recent PartGen [5], AutoPartGen is easier to implement and maintain (as it does not require training several multi-view image generators) and more accurate. Compared to HoloPart [58], a method that completes a pre-segmented outer surface of a mesh to form 3D parts, AutoPartGen is more accurate and significantly more capable, as it can automatically discover parts and reconstruct them from either a 2D image or a “shell” 3D object, optionally guided by 2D masks, not requiring any 3D annotation.

# 2 Related Work

Generating a 3D object from a single image, or even just text, faces an obvious challenge: the 3D object contains significantly more information than the image or the text. This is similar to the problem of generating images or videos from text, and it is solved by learning a prior, or conditional distribution, from billions of data samples. However, data of this size is unavailable for 3D objects. Authors address this problem by involving 2D image or video generators in the 3D generation process. We distinguish two main camps: multi-view direct and single-view latent 3D generation.

Multi-view 3D Generation. In multi-view 3D generation, one asks the image generator to do most of the lifting, generating several views of the 3D objects, and thus simplifying extracting a 3D object from them. First, this was done using Score Distillation Sampling (SDS) [41], an idea explored extensively in follow-ups like GET3D [13], ProlificDreamer [52], Dream Gaussians [49], Lucid Dreamer [9] which seek to achieve multi-view consistency via iterative (and slow) optimization of a radiance field (NeRF [43] or 3DGS [23]). A significant innovation, pioneered by UpFusion [22], 3DiM [53], Zero-1-to-3 [35] and MVDream [44], was to fine-tune the image generator to directly produce multiple consistent views of the object. By making the image generator more 3D aware, 3D reconstruction becomes simpler, as noted in InstantMesh [55], GRM [56], and others [54].

Single-view Latent 3D Generation. The alternative approach is to start from a single image of the object and directly reconstruct the 3D object from it. Because single-view reconstruction is extremely ambiguous, this requires to learn a reconstruction function. This was the path taken, for example, by LRM [19] and others [17, 47]. However, their deterministic reconstruction model cannot cope well with this ambiguity and often produces blurry outputs. Much better results were recently obtained by switching to stochastic 3D reconstruction based on latent diffusion. Some of the best single-image 3D reconstructors are based on the 3DShapeToVecSet [62] latent representation (also similar to Michelangelo’s [64]). Building on it, CLAY [63], DreamCraft3D [46], CraftsMan [29], TripoSG [30], and others [10, 57, 60] are able to generate highly detailed and accurate 3D shapes. We build on this representation as well and show that it also supports compositionality very effectively.

Composable 3D Generation. Approaches to composable 3D generation typically start by decomposing objects into constituent parts. One common strategy represents objects as mixtures of primitives, often without semantic labels. For instance, SIF [16] models object occupancy using mixtures of 3D Gaussians. LDIF [15] represents shapes as a set of local deep implicit functions (DIFs), spatially arranged and blended using a template of Gaussian primitives. Methods such as Neural Template [20] and SPAGHETTI [1] achieve decompositions through auto-decoding. SALAD [28] utilizes SPAGHETTI for diffusion-based generation. PartNeRF [50] expands this concept by employing mixtures of NeRFs. NeuForm [31] and DifFacto [38] specifically target part-level controllability. DBW [37] uses textured superquadrics to decompose scenes. In contrast, another research direction emphasizes explicitly semantic parts. PartSLIP [34] and PartSLIP++ [67] segment objects into semantic components from point clouds using vision-language models. Part123 [33] adapts techniques from scene-level approaches like Contrastive Lift [2] to reconstruct object parts. PartSDF [48] learns latent codes for parts using an auto-decoder and then uses SALAD for part prediction. Comboverse [8] leverages single-view inpainting model and 3D generator for composable 3D generation with spatial-aware SDS optimization. HoloPart [58], a recent work, starts from the shell of a 3D object and a part-level segmentation for it and performs 3D amodal part completion.

The work most related to ours is PartGen [5]. This squarely sits on the ‘multi-view direct’ camp (see above). It uses multi-view diffusion models for segmentation and completion of compositional 3D objects from diverse modalities.

3D Segmentation. 3D parts can be obtained by segmenting a 3D object (although the resulting parts will generally be incomplete). Some approaches for semantic 3D segmentation such as [65, 27, 51, 24, 2] used neural fields to ‘fuse’ 2D semantic features in 3D. Contrastive Lift [2] introduced a slow-fast contrastive clustering scheme for 3D instance segmentation. Recent methods such as [25, 61, 42, 3] integrate SAM [26] and often CLIP to model multi-scale concepts, where LangSplat explicitly encodes scale information and N2F2 learns to bind concepts to scales automatically. Neural Part Priors [4] used learned priors for test-time decomposition. Additionally, efforts to develop 3D ‘foundation’ models [66, 7] are enabling zero-shot point cloud segmentation across diverse domains.

# 3 Method

Let x ⊂ R3 be a 3D object given by a surface embedded in R3. We assume that the object is compositional, meaning that it can be expressed as the union x = SKk=1 x(k) of K disjoint parts x(1), . . . , x(K), each of which is also a surface. Concretely, x is usually a 3D mesh created by an artist, and x(k) are the components of the mesh that the artist has manually defined when creating the mesh. These parts are thus defined to facilitate editing of the 3D object or for functional purposes, such as animation. Generally, the same 3D object can have different and equally valid part decompositions.

[placeholder: image]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/289227f0e20142946ba55bcaddada6ceea41d6fbe26b96a4f313cb1d121e86ca.jpg)  
Figure 2: AutoPartGen generates parts autoregressively. At each step, a 3D latent diffusion model generate the next part, conditioned on the previously generated parts z(1,...,k), the overall object z˜, and, optionally, an image I of the object and an image J(k) of the part. The latent representation uses 3DShape2VecSet and the diffusion model is a DiT.

Our aim is to learn to generate 3D objects x and their part decompositions x(1), . . . , x(K). We consider three different scenarios. In the first scenario (object-to-parts), we are given the 3D object x, and the goal is to sample a possible decomposition of this object into parts. Furthermore, we may potentially have an object xˆ which is incomplete with respect to its constituent parts — a case that may arise if x is acquired by a 3D scanner that cannot look inside the object or synthesized by a generator that is not aware of the internal structure of the object, as exemplified by [58]. In this case, therefore, the goal is to also complete the parts, thus recovering the complete object x as a byproduct.

In the second scenario (image-to-parts), the starting point is an image I : Ω → R3 of the object, where Ω ⊂ R2 is the (finite) image domain. Inferring the object x from a single image is also known as the image-to-3D problem. Here, the task is to also infer its part decomposition x(1), . . . , x(K).

In the third scenario (masks-to-parts), we are given, in addition to the image I, K 2D part masks M (k) : Ω → {0, 1} that indicate the pixels in the image I that belong to each part x(k). These masks can be defined manually or, more likely, automatically, utilizing a 2D segmentation model. The problem is the same as before, but the 3D parts must match the prescribed masks.

In all these cases, recovering the parts (or the object) is ambiguous. These problems are thus stochastic and are solved by learning suitable conditional probability distributions: p(x(1), . . . , x(K) | x) (object-to-parts), p(x(1), . . . , x(K) | I ) (image-to-parts), and p(x(1), . . . , x(K) | I, M (1), . . . , M (K)) (masks-to-parts). We develop a single model that can handle all three cases.

# 3.1 Latent 3D shape space

Directly defining, modeling, and learning a distribution on 3D surfaces is difficult. We thus introduce a latent space, providing a finite-dimensional parametrization of the surfaces.

We utilize the VecSet representation developed by [62]. This representation is based on learning an encoder-decoder pair (E, D). The encoder E takes a collection of N object points P = {p1, . . . , pN } = sampleN x and maps them to a latent vector z = E(P ). Here sampleN is a function that samples N random points from the surface of the object x, so that P ⊂ x. The decoder takes the latent vector z and a query 3D point p ∈ R3 and evaluates the signed distance function (SDF) at p as SDF(p|x) = D(p|z). The encoder-decoder pair is thus ‘translational’, in the sense that it translates one type of representation of the object (the point cloud P ) into another (the signed distance function SDF(·|x)).1

In more detail, the encoder E compresses the point cloud P into a sequence z = (z1, . . . , zM ) of M tokens zi ∈ RD. The M ≪ N tokens are obtained by first subsampling the point cloud P into a much smaller set of points P˜ = {p1, . . . , pM } = sampleM P ⊂ P and then by applying a transformer neural network to the points in P˜ to output z. The transformer also attends to the large number of points in P efficiently via cross-attention. The network is designed to be permutation equivariant, meaning that the order of the points and tokens is immaterial, explaining the moniker ‘VecSet’. The decoder D takes a point p ∈ R3 and the tokens z and outputs the value of the signed distance function SDF(p|x), also utilizing a transformer neural network in the form of a Perceiver [21].

[placeholder: image]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/9857629f41b66a421f2d91f7e4664627c837b59df6f06b68d9d8722e7189a717.jpg)  
Figure 3: Compositionality of the VecSet space. Concatenation of two latents will result in a spatial combined mesh.

The intuition behind this representation is that each token vector zi encodes a local region of the surface centered at the point pi. However, the transformer allows tokens to communicate globally, which makes this interpretation somewhat loose. Empirically, we have discovered that locality, or at least compositionality, is well supported by the representation. As we show in Fig. 3, the tokens can be concatenated to form a new latent vector z = z(1) ⊕ z(2) that decodes into a new surface x = x(1) ∪ x(2) that is a good approximation of the union of the two parts, without any retraining.

# 3.2 Latent 3D diffusion

Having established the latent representation z for the shapes, the next task is to learn a model that can sample a shape given some evidence y, from a conditional probability distribution p(z | y) (for example, y could be the image I of the object). This utilizes (latent) diffusion. In brief, we define a√ sequence of progressively more noised versions of the latent vector z as zt = αtz + 1 − αtϵ, where ϵ ∼ N (0, I) is a Gaussian noise vector and αt, t = 0, 1, . . . , T is a schedule of noise levels.√ Following [45, 14], we introduce the flow velocity v(t, zt, ϵ) = z − ϵ = (zt − αtz)/ 1 − αt. The diffusion model vˆ(t, zt, ϵ) is trained to predict the flow velocity vˆ(t, zt | y) given only the latent vector zt and the condition y, minimizing the loss L(vˆ) = E(y,z),t,ϵ∥vˆ(t, zt | y) − v(t, zt, ϵ)∥2 averaged over a training set of evidence-latent vector pairs (y, z), a random time step t and noise ϵ.

# 3.3 Autoregressive 3D part generation

The model described in Section 3.1 generates the entire 3D object x (or, more precisely, its latent representation z) as a whole. Here, we consider the problem of generating the object parts instead. Our goal is to learn a single model that can handle all three part generation scenarios: object-to-part, image-to-part, and masks-to-part, depending on the inputs y provided.

To generate an undetermined number of parts K, we consider an autoregressive approach, where a single part x(k) is generated each time, based on what was generated before. The model can thus be described as a conditional distribution p(z(k) | y, z(1), . . . , z(k−1)) where z(k) is the latent representation of the k-th part and the input y collects the additional evidence available to the model.

The nature of this evidence depends on the reconstruction scenario. In the object-to-part scenario, y is simply the 3D object x. In the image-to-part scenario, y is the image I of the object. In the masks-to-part scenario, y is the image I as well as the masked image J(k) = M (k) ⊙ I, denoting which parts should be generated next.

Table 1: 3D part completion. Reconstruction quality of the parts and whole object. ∗reproduced.   
[placeholder: table]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/2b61d3e059e3f76c9c88c6945eb801041fa9af7b291f6f5259bb5810522a5da9.jpg)

Knowledge of the previously generated parts z(1), . . . , z(k−1) is essential as this allows the model to ensure that the next part fits together well with the previously generated ones. Furthermore, in all cases we consider, the evidence y also provides some evidence on the overall shape of the object. As suggested in Fig. 3, we can represent the union of parts by simply concatenating their latent representations. However, for compactness, we found it useful to fuse their codes into one, which we obtain as: z(1,...,k−1) = E  ∪k−1j=1 sampleN D(· | z(j)), where sampleN is a function that samples N points from the surface of the object defined by the zero level set of the SDF function D(·|z(k)).

We found it optional but useful to pin down the overall object by adding to the evidence y a code z˜ for the object as a whole, which is either given outright (object-to-part, z˜ = E(sampleN xˆ)) or can be obtained by the model itself (image-to-part and masks-to-part, z˜ ∼ p(z | I)).

With all this, we learn a conditional generator model

[placeholder: interline_equation]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/430f13be86519d62cff4c0b0704cf18fcad64a5c4891cb15409d370726d2e59e.jpg)

where y = ϕ for the object-to-part scenario, y = I for the image-to-part scenario, and y = (I, M (k)) for the masks-to-part scenario. The generation process stops when all the input masks have been processed, if available, or when the model outputs a special [EoT] token, representing empty shape.

Based on Section 3.2, learning the distribution Eq. (1) amounts to learning a velocity field vˆ(t, zt | z˜, z(1,...,k−1), y). During inference, we use classifier-free guidance (CFG) [18] to modulate the strength of the conditioning. In the most general case, the model is conditioned by the overall (partial) object z˜, the previously generated parts z(1,...,k−1), and a masked image pair y = (I, J(k)). We modulate the importance of the geometric and visual conditioning as follows:

[placeholder: interline_equation]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/4a0718f370d48af796927f7e1131feb06b86298343b8bf7acb045f7ebdca5fb4.jpg)

where wimg and wgeom modulate, respectively, image and geometry conditioning. The different inputs are implemented by appending tokens, which are then cross-attended by a transformer neural network computing the flow velocity. Hence, to suppress an input we simply replace it with dummy tokens. In the same way, we randomly drop some input at training time to allow the model to learn to use any required subset of the inputs.

Discussion Here, we contrast our model to prior works and justify its design. The most straightforward approach to part generation is to sample each part x(k) independently from a ‘marginal’ distribution p(x(k)). However, this model lacks a mechanism to tie the parts together and would result in a soup of random, uncoordinated parts. The simplest such mechanism is to provide evidence y for the overall shape of the 3D object. For instance, in the image-to-3D case, y = I could be a 2D image of the object, and we may sample parts from the conditional distribution p(x(k) | I). While I constrains the shape and position of the possible parts, these are still quite ambiguous. This explains why PartGen [5] conditions part generation on a multi-view image y = IMV of the 3D object x, and HoloPart [58] starts from a (partial) 3D reconstruction y = xˆ of the object itself.

Even then, the reconstruction context y is likely insufficient because there is no indication of which part should be reconstructed next. We could sample the parts in a random order, but this would not be very efficient. Furthermore, because the part decomposition is not unique, we would still need to extract a coherent subset of parts from the ‘part soup’ so obtained.

[placeholder: image]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/7ba908a70395e263b6a27d5fea462c6470d13a4f470bbe8c2ddbdf4645804292.jpg)  
Figure 4: Image-to-parts scenario. Given an input image, AutoPartGen recovers a compositional 3D object made up of several meaningful and complete parts.

Prior works address this issue by explicitly telling the 3D reconstruction model which part to extract next. PartGen does so by providing a multi-view image JMV of the part, and HoloPart by providing a 3D mask M3D of the part, defining distributions p(x(k) | IMV, JMV) and p(x(k) | xˆ, M3D), respectively. Hence, the problem of generating a coherent collection of parts is offloaded to a mechanism external to the 3D reconstructor. On the contrary, our 3D generator/reconstructor makes this determination by itself, operating autoregressively, one part at a time, without additional models.

# 4 Experiments

We first give the implementation details of AutoPartGen, including network architectures, training procedures, and datasets. We then demonstrate its performance under various conditions, highlighting its versatility for different applications. Next, we compare our approach with state-of-the-art 3D completion methods and provide ablation studies to analyze key design choices. Finally, we showcase several applications of AutoPartGen.

# 4.1 Implementation Details

Architecture. Our architecture builds upon the 3DShape2VecSet [62] framework, with some modifications. Specifically, we increase the input points of the VAE encoder to 32K, and utilize both point coordinates and normals as input features to better capture fine-grained geometric details. The diffusion model is implemented as a DiT [40] with a width of 2048 and 24 layers. For imageconditioned generation, we use DINOv2 [39] to encode the input image I and part-masked images J(k) = I ⊙ M (k) independently. The resulting features are concatenated along the channel dimension and passed through a small MLP to match the diffusion transformer input. We provide more details in the supplementary material.

Training. We use the AdamW optimizer with a learning rate of 1e-4 and train the model for 500K iterations on 256 NVIDIA H100 GPUs. Training the full model takes approximately 4 days. More details on hyperparameters and data preprocessing are provided in the supplementary material. During training, we randomly drop the image condition, the geometry condition, or both with probabilities of 0.05 each. For CFG, we use wimg = 7 and wgeom = 4 as the default setting.

Training Data. Our training data pipeline draws inspiration from PartGen [5], but is substantially scaled to encompass approximately 300K assets and 2M individual parts. We start with a collection of 1.8M 3D assets, all licensed that permit AI training. Each asset is stored in glTF/GLB formats, which contains multiple meshes in it and embeds a hierarchical structure. To manage complexity, if an asset contains more than a predefined maximum of 15 meshes, we iteratively merge meshes from the bottom up, until the mesh count is within this limit. To prepare for training VAE and diffusion models, we compute a truncated signed distance for each part in a normalized space and also render different views for image-conditioned cases. More details are included in the supplementary materials.

[placeholder: image]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/99a51ca7ed8111d8f3142a2b3ff5f0595068572c5d7a68ccc1c6c04447bb3799.jpg)  
Figure 5: Object-to-parts scenario. Given an input 3D object, AutoPartGen regenerates it as a composition of meaningful and complete 3D parts.

[placeholder: image]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/d13f22cadd30e3427b0dccafdb222731eaac62de00892a252326f16cf2a94dd3.jpg)  
Figure 6: Masks-to-parts scenario. AutoPartGen reconstructs a compositional 3D object guided by user-provided 2D part masks. Varying these masks yields different decompositions, potentially at different levels of granularity.

# 4.2 Object, Image and Masks to 3D Parts Generation

We test AutoPartGen with different types of inputs to demonstrate its versatility. Specifically, we consider: (1) image-to-parts generation from a single input image, where the images are generated by text-to-image (2D) generators; (2) object-to-parts decomposition from a full 3D mesh, with meshes sourced from Google Scanned Objects [11]; and (3) masks-to-parts generation with user-provided 2D part masks, where the masks are taken from PartObjaverse-Tiny [59]. Figures 4 to 6 qualitatively demonstrates that AutoPartGen produces accurate and consistent 3D parts across all these input types.

# 4.3 Comparison to the State-of-the-Art

Evaluation Protocol. We use PartObjaverse-Tiny [59] for evaluation, filtering out very small parts following the protocol of [58]. This dataset comprises objects from diverse categories with manually annotated 3D part segmentations. We use standard metrics to assess the quality of the reconstructed geometry: Intersection-over-Union (IoU), Chamfer Distance (CD), and F-score. IoU is calculated on 643 voxel grids, and the F-score adopts a distance threshold of 0.02. We report the quality of the reconstruction of individual parts and of the overall object after merging them.

Results. We compare AutoPartGen to two recent methods: PartGen [5] and HoloPart [58]. We focus on mask-controlled part generation. Recall that HoloPart takes as input the overall partial 3D object and 3D part segmentations and outputs the complete parts. We adapt both PartGen and AutoPartGen to solve the same problem. For AutoPartGen, we provide the overall partial 3D mesh and 2D part masks (a variant of masks-to-parts). For PartGen, we supply four masked views of each part, which are compatible with its input requirements.

The results in Table 1 show that HoloPart outperforms PartGen, likely due to its access to more comprehensive input information (the partial 3D object and 3D part masks). Nevertheless, AutoPartGen surpasses both baselines across all key metrics: IoU, F-score, and Chamfer Distance. This advantage holds true for both part completion and overall object reconstruction, indicating that AutoPartGen generates geometrically precise parts that form a well-formed and coherent whole.

[placeholder: image]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/e56480192e5919c3d1fdf758ed7898b2305df66c45567f11bd1fefc7c0476cb5.jpg)  
Figure 7: Visual comparison of different completion methods. Our approach achieves better geometric coherence by considering previously generated parts in context.

[placeholder: image]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/bff1866b2f7774ed56365cdb96451069812d4cd79082b35769fabebe6e450621.jpg)  
Figure 8: Ablation Study. (a) Without autoregressive generation, parts overlap and intersect. (b) Increasing image guidance wimg encourages the model to follow image mask, while a larger geometry guidance wgeom biases the generation towards a generic part distribution and order in the data.

# 4.4 Ablation Study

Autoregressive Modeling. We investigate the contribution of the autoregressive design. We remove the autoregressive condition z(1,...,k−1) in the masks-to-part scenario. This is the only scenario where we can do so, as external part guidance is needed to tell the model what part to generate next and when to stop. As shown in Fig. 8 (a), removing this conditioning causes parts to overlap and intersect.

Effectiveness of Guidance. We investigate the impact of varying image guidance wimg and geometry guidance wgeom in the mask-to-parts generation scenario. Since we randomly drop image conditions and geometry conditions, the model will implicitly learn a data-driven prior for part partitioning and ordering when no image condition is provided. As shown in Fig. 8 (b), increasing wimg encourages the model to generate parts more closely aligned with the input image masks. Conversely, a higher wgeom biases the model towards adhering to its learned prior of plausible part structures and arrangements.

# 4.5 Applications

3D Scene Generation. Our method’s capability for decomposable object generation naturally extends to entire 3D scenes. As illustrated in Figure 1 (middle row), given an isometric view of a small scene, our approach automatically generates individual scene objects such as chairs, clocks, plants, and tables in a decomposable manner. This decomposable nature facilitates flexible manipulation and editing of individual scene components.

City Generation. Figure 1 (bottom row) further showcases our method’s potential for large-scale outdoor scene generation. Drawing inspiration from SynCity [12], we employ a text-to-image generator to produce diverse tile images from text prompts. These tiles are subsequently assembled to form coherent cityscapes, enabling scalable and controllable generation of complex urban environments. Further examples and qualitative demonstrations are provided in the supplementary material.

# 5 Conclusion

We introduced AutoPartGen, an autoregressive model for compositional 3D part generation. By leveraging latent 3D representations, our method generates coherent object parts sequentially. The same model can handle different input types, including images, 2D masks, and 3D meshes. AutoPartGen outperforms existing methods in part completion and coherence while simplifying the overall pipeline. Our experiments demonstrate its effectiveness across various tasks and applications, highlighting its potential for scalable and controllable 3D content creation.

References   
[1] Hertz Amir, Perel Or, Giryes Raja, Sorkine-Hornung Olga, and Cohen-Or Daniel. SPAGHETTI: editing implicit shapes through part aware generation. In ACM Transactions on Graphics, 2022.   
[2] Yash Sanjay Bhalgat, Iro Laina, Joao F. Henriques, Andrea Vedaldi, and Andrew Zisserman. Contrastive Lift: 3D object instance segmentation by slow-fast contrastive fusion. In Proceedings of Advances in Neural Information Processing Systems (NeurIPS), 2023.   
[3] Yash Sanjay Bhalgat, Iro Laina, Joao F. Henriques, Andrew Zisserman, and Andrea Vedaldi. N2F2: Hierarchical scene understanding with nested neural feature fields. In Proceedings of the European Conference on Computer Vision (ECCV), 2024.   
[4] Aleksei Bokhovkin and Angela Dai. Neural part priors: Learning to optimize part-based object completion in rgb-d scans. In Proc. CVPR, 2023.   
[5] Minghao Chen, Roman Shapovalov, Iro Laina, Jianyuan Wang Tom Monnier, David Novotny, and Andrea Vedaldi. PartGen: Part-level 3d generation and reconstruction with multi-view diffusion models. In Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR), 2025.   
[6] Rui Chen, Jianfeng Zhang, Yixun Liang, Guan Luo, Weiyu Li, Jiarui Liu, Xiu Li, Xiaoxiao Long, Jiashi Feng, and Ping Tan. Dora: Sampling and benchmarking for 3D shape variational auto-encoders. arXiv, 2412.17808, 2024.   
[7] Yilun Chen, Shuai Yang, Haifeng Huang, Tai Wang, Runsen Xu, Ruiyuan Lyu, Dahua Lin, and Jiangmiao Pang. Grounded 3d-llm with referent tokens. arXiv preprint arXiv:2405.10370, 2024.   
[8] Yongwei Chen, Tengfei Wang, Tong Wu, Xingang Pan, Kui Jia, and Ziwei Liu. Comboverse: Compositional 3d assets creation using spatially-aware diffusion guidance. In Proc. ECCV, 2024.   
[9] Jaeyoung Chung, Suyoung Lee, Hyeongjin Nam, Jaerin Lee, and Kyoung Mu Lee. LucidDreamer: Domain-free generation of 3d gaussian splatting scenes. In arXiv, 2023.   
[10] Ken Deng, Yuanchen Guo, Jingxiang Sun, Zixin Zou, Yangguang Li, Xin Cai, Yanpei Cao, Yebin Liu, and Ding Liang. DetailGen3D: generative 3D geometry enhancement via data-dependent flow. arXiv, 2411.16820, 2024.   
[11] Laura Downs, Anthony Francis, Nate Koenig, Brandon Kinman, Ryan Hickman, Krista Reymann, Thomas B. McHugh, and Vincent Vanhoucke. Google Scanned Objects: A high-quality dataset of 3D scanned household items. In Proc. ICRA, 2022.   
[12] Paul Engstler, Aleksandar Shtedritski, Iro Laina, Christian Rupprecht, and Andrea Vedaldi. SynCity: training-free generation of 3d worlds. arXiv, 2503.16420, 2025.   
[13] Jun Gao, Tianchang Shen, Zian Wang, Wenzheng Chen, Kangxue Yin, Daiqing Li, Or Litany, Zan Gojcic, and Sanja Fidler. GET3D: A generative model of high quality 3D textured shapes learned from images. arXiv.cs, abs/2209.11163, 2022.   
[14] Ruiqi Gao, Emiel Hoogeboom, Jonathan Heek, Valentin De Bortoli, Kevin P. Murphy, and Tim Salimans. Diffusion meets flow matching: Two sides of the same coin, 2024.   
[15] Kyle Genova, Forrester Cole, Avneesh Sud, Aaron Sarna, and Thomas A. Funkhouser. Local deep implicit functions for 3D shape. In Proc. CVPR, 2020.   
[16] Kyle Genova, Forrester Cole, Daniel Vlasic, Aaron Sarna, William T. Freeman, and Thomas Funkhouser. Learning shape templates with structured implicit functions. In Proc. CVPR, 2019.   
[17] Junlin Han, Filippos Kokkinos, and Philip Torr. Vfusion3d: Learning scalable 3d generative models from video diffusion models. In European Conference on Computer Vision, pages 333–350. Springer, 2024.

[18] Jonathan Ho and Tim Salimans. Classifier-free diffusion guidance. In Proc. NeurIPS, 2021.

[19] Yicong Hong, Kai Zhang, Jiuxiang Gu, Sai Bi, Yang Zhou, Difan Liu, Feng Liu, Kalyan Sunkavalli, Trung Bui, and Hao Tan. LRM: Large reconstruction model for single image to 3D. In Proc. ICLR, 2024.   
[20] Ka-Hei Hui, Ruihui Li, Jingyu Hu, and Chi-Wing Fu. Neural template: Topology-aware reconstruction and disentangled generation of 3d meshes. In Proc. CVPR, 2022.   
[21] Andrew Jaegle, Sebastian Borgeaud, Jean-Baptiste Alayrac, Carl Doersch, Catalin Ionescu, David Ding, Skanda Koppula, Daniel Zoran, Andrew Brock, Evan Shelhamer, Olivier J. Hénaff, Matthew M. Botvinick, Andrew Zisserman, Oriol Vinyals, and João Carreira. Perceiver IO: A general architecture for structured inputs & outputs. In Proc. ICLR, 2022.   
[22] Bharath Raj Nagoor Kani, Hsin-Ying Lee, Sergey Tulyakov, and Shubham Tulsiani. UpFusion: novel view diffusion from unposed sparse view observations. arXiv, 2024.   
[23] Bernhard Kerbl, Georgios Kopanas, Thomas Leimkühler, and George Drettakis. 3D Gaussian Splatting for real-time radiance field rendering. Proc. SIGGRAPH, 42(4), 2023.   
[24] Justin Kerr, Chung Min Kim, Ken Goldberg, Angjoo Kanazawa, and Matthew Tancik. LERF: language embedded radiance fields. In Proc. ICCV, 2023.   
[25] Chung Min Kim, Mingxuan Wu, Justin Kerr, Ken Goldberg, Matthew Tancik, and Angjoo Kanazawa. Garfield: Group anything with radiance fields. arXiv.cs, abs/2401.09419, 2024.   
[26] Alexander Kirillov, Eric Mintun, Nikhila Ravi, Hanzi Mao, Chloe Rolland, Laura Gustafson, Tete Xiao, Spencer Whitehead, Alexander C. Berg, Wan-Yen Lo, Piotr Dollár, and Ross Girshick. Segment anything. In Proc. CVPR, 2023.   
[27] Sosuke Kobayashi, Eiichi Matsumoto, and Vincent Sitzmann. Decomposing NeRF for editing via feature field distillation. In Proc. NeurIPS, 2022.   
[28] Juil Koo, Seungwoo Yoo, Minh Hieu Nguyen, and Minhyuk Sung. SALAD: part-level latent diffusion for 3D shape generation and manipulation. In Proc. ICCV, 2023.   
[29] Weiyu Li, Jiarui Liu, Rui Chen, Yixun Liang, Xuelin Chen, Ping Tan, and Xiaoxiao Long. CraftsMan: high-fidelity mesh generation with 3d native generation and interactive geometry refiner. arXiv, 2405.14979, 2024.   
[30] Yangguang Li, Zi-Xin Zou, Zexiang Liu, Dehu Wang, Yuan Liang, Zhipeng Yu, Xingchao Liu, Yuan-Chen Guo, Ding Liang, Wanli Ouyang, and Yan-Pei Cao. TripoSG: high-fidelity 3D shape synthesis using large-scale rectified flow models. arXiv, 2502.06608, 2025.   
[31] Connor Lin, Niloy Mitra, Gordon Wetzstein, Leonidas J. Guibas, and Paul Guerrero. NeuForm: adaptive overfitting for neural shape editing. In Proc. NeurIPS, 2022.   
[32] Shanchuan Lin, Bingchen Liu, Jiashi Li, and Xiao Yang. Common diffusion noise schedules and sample steps are flawed. arXiv.cs, abs/2305.08891, 2023.   
[33] Anran Liu, Cheng Lin, Yuan Liu, Xiaoxiao Long, Zhiyang Dou, Hao-Xiang Guo, Ping Luo, and Wenping Wang. Part123: Part-aware 3d reconstruction from a single-view image. arXiv, 2405.16888, 2024.   
[34] Minghua Liu, Yinhao Zhu, Hong Cai, Shizhong Han, Zhan Ling, Fatih Porikli, and Hao Su. PartSLIP: low-shot part segmentation for 3D point clouds via pretrained image-language models. In Proc. CVPR, 2023.   
[35] Ruoshi Liu, Rundi Wu, Basile Van Hoorick, Pavel Tokmakov, Sergey Zakharov, and Carl Vondrick. Zero-1-to-3: Zero-shot one image to 3D object. In Proc. ICCV, 2023.   
[36] Yuan Liu, Cheng Lin, Zijiao Zeng, Xiaoxiao Long, Lingjie Liu, Taku Komura, and Wenping Wang. SyncDreamer: Generating multiview-consistent images from a single-view image. arXiv, 2309.03453, 2023.   
[37] Tom Monnier, Jake Austin, Angjoo Kanazawa, Alexei Efros, and Mathieu Aubry. Differentiable blocks world: Qualitative 3d decomposition by rendering primitives. In Proc. NeurIPS, 2023.   
[38] George Kiyohiro Nakayama, Mikaela Angelina Uy, Jiahui Huang, Shi-Min Hu, Ke Li, and Leonidas Guibas. DiffFacto: controllable part-based 3D point cloud generation with cross diffusion. In Proc. ICCV, 2023.   
[39] Maxime Oquab, Timothée Darcet, Théo Moutakanni, Huy V. Vo, Marc Szafraniec, Vasil Khalidov, Pierre Fernandez, Daniel HAZIZA, Francisco Massa, Alaaeldin El-Nouby, Mido Assran, Nicolas Ballas, Wojciech Galuba, Russell Howes, Po-Yao Huang, Shang-Wen Li, Ishan Misra, Michael Rabbat, Vasu Sharma, Gabriel Synnaeve, Hu Xu, Herve Jegou, Julien Mairal, Patrick Labatut, Armand Joulin, and Piotr Bojanowski. DINOv2: Learning robust visual features without supervision. Transactions on Machine Learning Research, 2024.   
[40] William Peebles and Saining Xie. Scalable diffusion models with transformers. In Proceedings of the IEEE/CVF international conference on computer vision, pages 4195–4205, 2023.   
[41] Ben Poole, Ajay Jain, Jonathan T. Barron, and Ben Mildenhall. DreamFusion: Text-to-3D using 2D diffusion. In Proc. ICLR, 2023.   
[42] Minghan Qin, Wanhua Li, Jiawei Zhou, Haoqian Wang, and Hanspeter Pfister. LangSplat: 3D language Gaussian splatting. In Proc. CVPR, 2024.   
[43] Viktor Rudnev, Mohamed Elgharib, William Smith, Lingjie Liu, Vladislav Golyanik, and Christian Theobalt. NeRF for outdoor scene relighting. In Proc. ECCV, 2021.   
[44] Yichun Shi, Peng Wang, Jianglong Ye, Mai Long, Kejie Li, and Xiao Yang. MVDream: Multi-view diffusion for 3D generation. In Proc. ICLR, 2024.   
[45] Jiaming Song, Chenlin Meng, and Stefano Ermon. Denoising diffusion implicit models. In Proc. ICLR, 2021.   
[46] Jingxiang Sun, Bo Zhang, Ruizhi Shao, Lizhen Wang, Wen Liu, Zhenda Xie, and Yebin Liu. DreamCraft3D: Hierarchical 3D generation with bootstrapped diffusion prior. arXiv.cs, abs/2310.16818, 2023.   
[47] Stanislaw Szymanowicz, Christian Rupprecht, and Andrea Vedaldi. Splatter Image: Ultra-fast single-view 3D reconstruction. In Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR), 2024.   
[48] Nicolas Talabot, Olivier Clerc, Arda Cinar Demirtas, Doruk Oner, and Pascal Fua. PartSDF: partbased implicit neural representation for composite 3d shape parametrization and optimization. arXiv, 2502.12985, 2025.   
[49] Jiaxiang Tang, Jiawei Ren, Hang Zhou, Ziwei Liu, and Gang Zeng. DreamGaussian: Generative gaussian splatting for efficient 3D content creation. arXiv, 2309.16653, 2023.   
[50] Konstantinos Tertikas, Despoina Paschalidou, Boxiao Pan, Jeong Joon Park, Mikaela Angelina Uy, Ioannis Z. Emiris, Yannis Avrithis, and Leonidas J. Guibas. PartNeRF: Generating partaware editable 3D shapes without 3D supervision. arXiv.cs, abs/2303.09554, 2023.   
[51] Vadim Tschernezki, Iro Laina, Diane Larlus, and Andrea Vedaldi. Neural Feature Fusion Fields: 3D distillation of self-supervised 2D image representation. In Proceedings of the International Conference on 3D Vision (3DV), 2022.   
[52] Zhengyi Wang, Cheng Lu, Yikai Wang, Fan Bao, Chongxuan Li, Hang Su, and Jun Zhu. ProlificDreamer: High-fidelity and diverse text-to-3D generation with variational score distillation. arXiv.cs, abs/2305.16213, 2023.   
[53] Daniel Watson, William Chan, Ricardo Martin-Brualla, Jonathan Ho, Andrea Tagliasacchi, and Mohammad Norouzi. Novel view synthesis with diffusion models. In Proc. ICLR, 2023.   
[54] Xinyue Wei, Kai Zhang, Sai Bi, Hao Tan, Fujun Luan, Valentin Deschaintre, Kalyan Sunkavalli, Hao Su, and Zexiang Xu. MeshLRM: large reconstruction model for high-quality mesh. arXiv, 2404.12385, 2024.   
[55] Jiale Xu, Weihao Cheng, Yiming Gao, Xintao Wang, Shenghua Gao, and Ying Shan. InstantMesh: efficient 3D mesh generation from a single image with sparse-view large reconstruction models. arXiv, 2404.07191, 2024.   
[56] Yinghao Xu, Zifan Shi, Wang Yifan, Hansheng Chen, Ceyuan Yang, Sida Peng, Yujun Shen, and Gordon Wetzstein. GRM: Large gaussian reconstruction model for efficient 3D reconstruction and generation. arXiv, 2403.14621, 2024.   
[57] Jiayu Yang, Taizhang Shang, Weixuan Sun, Xibin Song, Ziang Chen, Senbo Wang, Shenzhou Chen, Weizhe Liu, Hongdong Li, and Pan Ji. Pandora3D: A comprehensive framework for high-quality 3D shape and texture generation. arXiv, 2502.14247, 2025.   
[58] Yunhan Yang, Yuan-Chen Guo, Yukun Huang, Zi-Xin Zou, Zhipeng Yu, Yangguang Li, Yan-Pei Cao, and Xihui Liu. HoloPart: generative 3d part amodal segmentation. arXiv, 2504.07943, 2025.   
[59] Yunhan Yang, Yukun Huang, Yuan-Chen Guo, Liangjun Lu, Xiaoyang Wu, Edmund Y Lam, Yan-Pei Cao, and Xihui Liu. Sampart3d: Segment any part in 3d objects. arXiv preprint arXiv:2411.07184, 2024.   
[60] Chongjie Ye, Yushuang Wu, Ziteng Lu, Jiahao Chang, Xiaoyang Guo, Jiaqing Zhou, Hao Zhao, and Xiaoguang Han. Hi3DGen: High-fidelity 3D geometry generation from images via normal bridging. arXiv, 2025.   
[61] Haiyang Ying, Yixuan Yin, Jinzhi Zhang, Fan Wang, Tao Yu, Ruqi Huang, and Lu Fang. Omniseg3d: Omniversal 3d segmentation via hierarchical contrastive learning. In Proc. CVPR, 2024.   
[62] Biao Zhang, Jiapeng Tang, Matthias Niessner, and Peter Wonka. 3DShape2VecSet: A 3D shape representation for neural fields and generative diffusion models. In ACM Transactions on Graphics, 2023.   
[63] Longwen Zhang, Ziyu Wang, Qixuan Zhang, Qiwei Qiu, Anqi Pang, Haoran Jiang, Wei Yang, Lan Xu, and Jingyi Yu. CLAY: A controllable large-scale generative model for creating high-quality 3D assets. arXiv, 2024.   
[64] Zibo Zhao, Wen Liu, Xin Chen, Xianfang Zeng, Rui Wang, Pei Cheng, Bin Fu, Tao Chen, Gang Yu, and Shenghua Gao. Michelangelo: Conditional 3D shape generation based on shape-image-text aligned latent representation. In Proc. NeurIPS, 2023.   
[65] Shuaifeng Zhi, Tristan Laidlow, Stefan Leutenegger, and Andrew J. Davison. In-place scene labelling and understanding with implicit scene representation. In Proc. ICCV, 2021.   
[66] Junsheng Zhou, Jinsheng Wang, Baorui Ma, Yu-Shen Liu, Tiejun Huang, and Xinlong Wang. Uni3D: Exploring unified 3D representation at scale. In Proc. ICLR, 2024.   
[67] Yuchen Zhou, Jiayuan Gu, Xuanlin Li, Minghua Liu, Yunhao Fang, and Hao Su. PartSLIP++: enhancing low-shot 3d part segmentation via multi-view instance segmentation and maximum likelihood estimation. arXiv, 2312.03015, 2023.

# Supplementary Material

This supplementary material provides additional details and results to complement the main paper. It includes the following sections:

• Implementation Details: Detailed descriptions of model architectures, training and inference procedures, and evaluation protocols.   
• Additional Comparisons with PartGen: Extended evaluation against PartGen.   
• Ablation Study: Quantitative analysis highlighting the effectiveness of autoregressive training and different guidance scale.   
• 3D Scene Generation: Additional qualitative examples for scene generation.   
• City Generation: Details of the city generation pipeline and additional visual results.   
• Failure Case: Visualization of failure cases in AutoPartGen.   
• Limitations and Broader Impact: Discussion of limitations and potential societal implications of AutoPartGen.

# A Implementation Details

# A.1 Training

Our model consists of two primary components: a 3D Variational Autoencoder (VAE) and a diffusion model.

3D Variational Autoencoder. We adopt the 3D representation from 3DShape2VecSet, extending it to a larger model capacity compared to the original VAE [62]. Our VAE architecture comprises an 8-layer encoder with a dimension of 768 and a 16-layer decoder with a dimension of 1024. The model is trained on approximately 1.7M 3D assets, with data augmentation techniques including point cloud rotations, as suggested by Dora [6]. We employ a signed distance function (SDF) representation for smoother isosurface extraction. During training, we supervise the VAE using a combination of surface normal loss, Eikonal loss, and KL divergence regularization, weighted by 10, 0.1, and 0.001, respectively, following TripoSG [30]. To learn a single signed distance field, we calculate a combination of L1 and MSE loss on a total of 24,576 points per shape: 8192 each from surface points, near-surface points, and randomly in the volume. We randomly vary the number of input tokens between {512, 2048} during training. The model is optimized using AdamW with a learning rate of 1e−4, linearly warmed up from 1e−5 over the first 3 epochs. We use a batch size of 1536 and set the weight decay to 0.01. Training is conducted on 128 NVIDIA H100 GPUs for 150 epochs.

Diffusion Model. For diffusion training, we first pretrain a general image-to-3D model using the same 1.7M assets. The diffusion model follows DiT [40], configured with 24 transformer layers and a dimension of 2048. The model is trained with a fixed token length of 512 for 300 epochs with a learning rate of 1e−4 and a batch size of 10 per GPU on 128 GPUs. We then fine-tune the model to additionally condition on masked image and geometry tokens on the part dataset in an autoregressive manner for approximately 300k steps. The image condition is encoded with DINO-v2 [39] and the geometry token is encoded with our trained 3D VAE. To reduce computational overhead, geometry tokens are only used in the first 12 transformer layers. We apply condition with a drop probability of 0.05 independently for the geometry token, image token, and both simultaneously. Fine-tuning also uses the AdamW optimizer with a weight decay of 0.01, batch size of 6 per GPU, on 128 GPUs. Subsequently, we increase the token length to 2048 and continue training for an additional 100k steps using 256 GPUs with batch size 1 per GPU. We train the model using the DDIM scheduler [45] with 1000 steps, employing v-prediction and a zero signal-to-noise ratio [32].

# A.2 Inference

In all scenarios, we use 50 denoising steps during inference. For the object-to-parts setting, geometry guidance is set to 10, while image guidance is disabled (set to 0). For both the image-to-parts and masks-to-parts settings, we first perform image-to-3D reconstruction to obtain the overall object shape. When user-provided masks are available, we apply the default guidance setting, with image guidance set to 7 and geometry guidance set to 4.

[placeholder: image]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/53e1310957e35a088bb93d724359eb89ab4a2249796bc2cacbec6d5faeccb67f.jpg)  
Figure 9: Comparison between AutoPartGen and PartGen. AutoPartGen produces more accurate geometry, as highlighted in the red circle. Additionally, its autoregressive generation prevents the overlapping parts observed in PartGen, as shown in the yellow circle.

# A.3 Evaluation

The most relevant baseline to AutoPartGen is PartGen. We compare the two methods under the object-to-parts setting, without incorporating any user inputs. For this comparison, we use objects from the Google Scanned Objects (GSO) dataset [11].

When users provide masks to guide part partitioning, we compare our method with recent approaches, including HoloPart and PartGen. For evaluation, we use the PartObjaverse-Tiny dataset [59]. To exclude negligible parts, we filter out objects containing segments that occupy only a small fraction of the total object volume as in [58].

# B Additional Comparison with PartGen

To further highlight the improvements over PartGen, we provide a qualitative comparison in Figure 9. As shown in the figure, AutoPartGen produces sharper and more detailed meshes, as highlighted by the red circle. Additionally, the autoregressive generation in AutoPartGen avoids over-generation issues seen in PartGen, which arise from its lack of explicit modeling of the joint distribution of different parts. This is a key capability addressed by AutoPartGen.

# C Ablation Study

We first conduct quantitative ablations to assess the impact of using an autoregressive strategy in AutoPartGen pipeline, as shown in Table 2. Results indicate that enabling autoregression significantly improves both part-level completion and overall shape quality across all metrics. Specifically, the autoregressive model achieves higher IoU and F-score, and lower Chamfer Distance (CD), suggesting better geometric fidelity and coherence in generated outputs.

Table 2: Ablation study on autoregressive. Autoregressive generation clearly show better results in terms of the part completion and overall object coherence. The models are only trained for 200 epochs.   
[placeholder: table]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/58732ea46e991e5e52d7ed32370d3431b1458059983de99c56973f39c12f049a.jpg)

Table 3: Effects of different guidance scales. We report the three metrics on the part completion task.   
[placeholder: table]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/635623580a28c0d10ef3b67963f19ba48c6d789c4b5f820e2a075f7126fed439.jpg)

We also investigate the influence of the guidance scale during inference as shown in Table 3. Varying the geometry/image guidance scales, we notice that moderate guidance values (e.g., 4/7) strike the best balance, achieving peak performance in IoU, F-score, and CD. Excessively low or high scales tend to degrade performance.

# D 3D Scene Generation

Small scene generation is a natural extension of our method. Specifically, we begin by providing prompts such as “an isometric view of an office” or “an isometric view of a small bedroom” to an off-the-shelf 2D text-to-image generator to produce corresponding images. We first generate the overall shape of the small scene. Subsequently, we apply AutoPartGen again to decompose the scene into distinct components such as “chair”, “able” and so on. More qualitative examples are provided in Figure 10.

# E City Generation

As shown in Fig.1 of the main paper, we demonstrate the ability of AutoPartGen to generate 3D cities by integrating it into the SynCity [36] pipeline, replacing its original 3D generator. Specifically, the pipeline begins with text prompts generated by a large language model, which are then used to guide a 2D image generator in creating isometric views of individual tiles, taking into account the context of neighboring tiles. These generated images are then passed to AutoPartGen to produce compositional 3D tiles.

We present additional examples in Figure 11. As illustrated, AutoPartGen can be seamlessly integrated into the city generation pipeline, generating different cities, such as a ’medieval town‘ or a “solarpunk city”. For further details on prompt generation and 2D image synthesis, please refer to the SynCity paper.

[placeholder: image]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/37ce5d22156a37300ef79431c0ece6e2023bb3f58ae607f4443e155e2a6087a1.jpg)  
Figure 10: 3D scene generation. AutoPartGen generates 3D scenes while decomposing them into their constituent elements. The input images are generated by a 2D text-to-image generator.

[placeholder: image]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/610bf9153de6bee1b2d4e6380af9204d58c73d63486de752afc13a43ac7da1ba.jpg)  
Figure 11: City Generation. We showcase AutoPartGen on larger scenes by integrating it within Syncity [12]. From top to bottom, the images depict a medieval town, a cozy town, and a solarpunk city.

# F Failure Cases

[placeholder: image]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_PROJ/pdf_extractor_data/images/d6a216cba268ffa2b8258daaacd82d58e51d1c4a3cae79cd66ee3f965fcbd5aa.jpg)  
Figure 12: Failure Case. When there are identical parts, the model sometimes will try to predict the parts together even if masks are given.

We present a failure case in Figure 12. As shown in the figure, when the object contains identical parts, the model attempts to predict multiple parts together, even when only one is masked. We conjecture that this behavior comes from the bias in the training data, where some artists may have grouped identical parts into a single mesh. Additionally, as discussed in the ablation study, users may adjust the guidance scale to enforce stronger adherence to the image, which can amplify this effect. Due to the model’s autoregressive nature, each prediction depends on

previously generated parts. In the example shown in Figure 12, where both window instances are generated together, when the mask for the second window is given as input, the model’s prediction will be (nearly) empty, since the model has already generated that content. Hence, despite this potential failure mode, the model produces coherent results, maintaining consistency in the overall shape.

# G Limitations and Boarder Impact

Limitations. While AutoPartGen demonstrates strong performance across all three scenarios, it also has some limitations that point to potential directions for future improvement. First, the current model can only generate bounded scenes, as it inherits the spatial constraints from the underlying VAE latent space. Extending the framework to support unbounded world generation, where scenes can grow or evolve without a predefined spatial limit, would be both an interesting challenge and a promising research direction. Second, the method currently lacks explicit control over the granularity of part partitioning, except in the masks-to-parts setting, where masks can be provided as a way of control. In the image-to-parts and object-to-parts settings, the decomposition of parts can vary. In future iterations, one may incorporate high-level controls for granularity levels, such as ‘simple‘, ‘medium‘, and ‘complicated‘, to make the system more flexible and interactive. Finally, the model learns part distributions directly from the training data, which introduces the risk of bias being inherited from the dataset.

Broader Impact. Although our model is trained on a large amount of data, it may still exhibit biases that reflect imbalances in the underlying distribution. These biases can influence downstream tasks and should be carefully evaluated before practical deployment. To mitigate potential misuse or harmful applications, we recommend implementing safeguards and conducting thorough audits to ensure responsible usage. Additionally, the training process requires substantial computational resources, particularly in terms of GPU usage. This raises concerns about energy consumption and the associated environmental impact, which should be taken into account when scaling or deploying the model in real-world settings.