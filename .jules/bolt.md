## 2024-03-24 - Faster GeLU Functions
**Learning:** PyTorch native `F.gelu(x, approximate="tanh")` is roughly 3-4x faster than mathematically evaluating the tanh approximation piece-by-piece in Python as done in `gelu_new` and `gelu_fast`. The codebase was defining custom approximations when it could rely on the native, highly optimized C++/CUDA PyTorch implementations.
**Action:** Always prefer native PyTorch operations, particularly for standard activation functions, instead of mathematically re-implementing them.
