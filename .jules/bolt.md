## 2024-03-24 - Avoid einops overhead in simple operations
**Learning:** PyTorch native operations like `torch.einsum`, `.view()`, `.reshape()`, and `.transpose()` are consistently faster than `einops.einsum` and `einops.rearrange` because they avoid Python-side string parsing overhead. In `transformer_lens`, this overhead is significant for frequently called attention functions.
**Action:** Replace `einops.einsum` and `einops.rearrange` with native PyTorch equivalents in hot paths like attention utilities.
