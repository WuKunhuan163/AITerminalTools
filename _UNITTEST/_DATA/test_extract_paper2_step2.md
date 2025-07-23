Table 1: 3D part completion. Reconstruction quality of the parts and whole object. →reproduced.   
[placeholder: table]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_DATA/images/c7c84f7bcf90c20b1784c35c628d3cb12bd4de7662735890a6b6b21bc3def7b9.jpg)

**表格内容:**
$$
{ \begin{array} { r l r l r l r l } & { } & & { { \mathbf { M e t h o d } } } & { 3 { \mathbf { D } } { \mathbf { M a s k } } } & { { \xrightarrow { \mathbf { P a r t s } } } } & { } & { { \mathbf { W h o l e ~ O b j e c t } } } \\ & { } & & { { \overline { { \mathrm { I o U ~ \{ ~ F ~ S c o r e \ ' ~ } } } } } } & { \mathbf { C D } { \mathbf { \Phi ~ C ~ D \downarrow } } } & { } & { { \mathbf { I o U ~ \{ ~ F ~ S c o r e \ ' ~ } } }  & { \mathbf { C D } { \mathbf { \downarrow } } } \\ & { } & { { \overline { { \mathrm { H o l o P a r t ~ } ^ { * } [ { \mathsf { S 8 } } ] } } } } & { \quad \forall } & { 0 . 6 5 8 } & { 0 . 8 3 6 } & { 0 . 0 6 5 } & { 0 . 8 2 1 } & { 0 . 9 4 5 } & { 0 . 0 1 8 } \\ & { } & { \mathbf { P a r t G e n ~ } [ { \mathsf { S } } ] } & { \quad \mathbf { \chi } } & { 0 . 6 1 4 } & { 0 . 8 1 2 } & { 0 . 1 2 1 } & { 0 . 7 7 9 } & { 0 . 9 2 1 } & { 0 . 0 3 3 } \\ & { } & { { \mathbf { A u t o P a r t G e n } } } & { \quad \mathbf { \chi } } & { 0 . 6 6 5 } & { 0 . 8 6 1 } & { 0 . 0 4 7 } & { 0 . 8 3 2 } & { 0 . 9 6 7 } & { 0 . 0 1 2 } \end{array}
$$

masks-to-part scenario, y is the image I as well as the masked image J(k) = M (k) ↓ I, denoting which parts should be generated next.

Knowledge of the previously generated parts z(1), . . . , z(k↑1) is essential as this allows the model to ensure that the next part fits together well with the previously generated ones. Furthermore, in all cases we consider, the evidence y also provides some evidence on the overall shape of the object. As suggested in Fig. 3, we can represent the union of parts by simply concatenating their latent representations. However, for compactness, we found it useful to fuse their codes into one, which we obtain as: z(1,...,k↑1) = E ! ↔k↑1j=1 sampleN D(· | z(j) ) " , where sampleN is a function that samples N points from the surface of the object defined by the zero level set of the SDF function D(·|z(k) ).

We found it optional but useful to pin down the overall object by adding to the evidence y a code z˜ for the object as a whole, which is either given outright (object-to-part, z˜ = E(sampleN xˆ)) or can be obtained by the model itself (image-to-part and masks-to-part, z˜ ↗ p(z | I)).

With all this, we learn a conditional generator model

[placeholder: interline_equation]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_DATA/images/9daed601931c7dc45e90545d5335e1cbcc58e382e377760ddc3033477cc096b8.jpg)

$$
\boldsymbol { z } ^ { ( k ) } \sim p ( \boldsymbol { z } ^ { ( k ) } | \tilde { \boldsymbol { z } } , \boldsymbol { z } ^ { ( 1 , \dots , k - 1 ) } , y ) ,
$$

where y = ω for the object-to-part scenario, y = I for the image-to-part scenario, and y = (I, M (k) ) for the masks-to-part scenario. The generation process stops when all the input masks have been processed, if available, or when the model outputs a special [EoT] token, representing empty shape.

Based on Section 3.2, learning the distribution Eq. (1) amounts to learning a velocity field vˆ(t, zt | z˜, z(1,...,k↑1), y). During inference, we use classifier-free guidance (CFG) [18] to modulate the strength of the conditioning. In the most general case, the model is conditioned by the overall (partial) object z˜, the previously generated parts z(1,...,k↑1), and a masked image pair y = (I, J(k) ). We modulate the importance of the geometric and visual conditioning as follows:

[placeholder: interline_equation]
![](/Users/wukunhuan/.local/bin/EXTRACT_PDF_DATA/images/4ccaa51b81a2fc2d42cb15374f1d03adc72c7a5e5622100441bd35cfd35964f8.jpg)

$$
\begin{array} { r } { \hat { v } _ { \mathrm { C F G } } ( t , z _ { t } \mid \tilde { z } , z ^ { ( 1 , \ldots , k - 1 ) } , y ) = w _ { \mathrm { i n g } } \left( \hat { v } ( t , z _ { t } \mid \tilde { z } , z ^ { ( 1 , \ldots , k - 1 ) } , I , J ^ { ( k ) } ) - \hat { v } ( t , z _ { t } \mid \tilde { z } , z ^ { ( 1 , \ldots , k - 1 ) } ) \right) } \\ { + w _ { \mathrm { g e o m } } \left( \hat { v } ( t , z _ { t } \mid \tilde { z } , z ^ { ( 1 , \ldots , k - 1 ) } ) - \hat { v } ( t , z _ { t } , \emptyset ) \right) + \hat { v } ( t , z _ { t } , \emptyset ) } \end{array}
$$

where wimg and wgeom modulate, respectively, image and geometry conditioning. The different inputs are implemented by appending tokens, which are then cross-attended by a transformer neural network computing the flow velocity. Hence, to suppress an input we simply replace it with dummy tokens. In the same way, we randomly drop some input at training time to allow the model to learn to use any required subset of the inputs.

Discussion Here, we contrast our model to prior works and justify its design. The most straightforward approach to part generation is to sample each part x(k) independently from a ‘marginal’ distribution p(x(k) ). However, this model lacks a mechanism to tie the parts together and would result in a soup of random, uncoordinated parts. The simplest such mechanism is to provide evidence y for the overall shape of the 3D object. For instance, in the image-to-3D case, y = I could be a 2D image of the object, and we may sample parts from the conditional distribution p(x(k) | I). While I constrains the shape and position of the possible parts, these are still quite ambiguous. This explains why PartGen [5] conditions part generation on a multi-view image y = IMV of the 3D object x, and HoloPart [58] starts from a (partial) 3D reconstruction y = xˆ of the object itself.

Even then, the reconstruction context y is likely insufficient because there is no indication of which part should be reconstructed next. We could sample the parts in a random order, but this would not be very efficient. Furthermore, because the part decomposition is not unique, we would still need to extract a coherent subset of parts from the ‘part soup’ so obtained.