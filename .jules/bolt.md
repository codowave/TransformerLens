## 2024-03-24 - Tensor contraction performance
**Learning:** Manual broadcasting and element-wise multiplication with `einops.rearrange` is significantly slower than native tensor contractions with `torch.einsum` or `torch.matmul`. This is especially true for large tensors in attention mechanisms where it can cause OOM errors.
**Action:** Replace `einops.rearrange(...) @ einops.rearrange(...)` patterns with `torch.einsum` in `transformer_lens/components/abstract_attention.py` for calculating attention scores and z scores.
