
## 2024-03-24 - native PyTorch vs einops
**Learning:** einops.einsum and einops.rearrange add significant Python-side string parsing overhead.
**Action:** Prefer native PyTorch functions like transpose, reshape, and torch.einsum in performance critical paths.
