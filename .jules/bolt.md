## 2024-10-28 - PyTorch native gelu outperforms custom element-wise approximations
**Learning:** Element-wise math implementations of gelu (`gelu_new`, `gelu_fast`) are significantly slower (3-4x) than native `torch.nn.functional.gelu(..., approximate="tanh")`.
**Action:** Replace `gelu_new` and `gelu_fast` with `F.gelu(..., approximate="tanh")` which compute identically but leverage C++ fused kernels.
