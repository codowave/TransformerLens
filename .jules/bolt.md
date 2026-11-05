## 2024-05-24 - Tensor contraction (OOM avoidance & optimization)
**Learning:** Manual broadcasting using `einops.rearrange` to add singleton dimensions followed by element-wise multiplication and `.sum()` (e.g. `(z * w).sum(-2)`) creates huge intermediate tensors leading to massive memory bloat (OOM errors) and slow down on CPU. In `abstract_attention.py`'s `forward` path this takes 50x more time.
**Action:** Always prefer native fused operations like `torch.einsum` or `torch.matmul` over explicit element-wise broadcasting when doing tensor contractions in PyTorch.
