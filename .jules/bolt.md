## 2023-10-27 - Native PyTorch GeLU for Faster MLPs
**Learning:** Recreating complex activations (like GeLU approximations) using element-wise operations (e.g. `0.5 * x * (1 + tanh(sqrt(2/pi) * (x + 0.044715 * x^3)))`) is significantly slower (~4x) than using native PyTorch optimized implementations (`F.gelu(x, approximate="tanh")`).
**Action:** Use native PyTorch activations whenever possible, especially for heavily used functions like MLP activations.
