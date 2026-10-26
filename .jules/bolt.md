## 2024-05-24 - GeLU optimization
**Learning:** PyTorch native `F.gelu(..., approximate="tanh")` is ~6x faster than naive Python mathematical implementations of GPT-2's GeLU (`gelu_new`) and standard GeLU approximations (`gelu_fast`), while maintaining mathematically identical precision (within floating point precision max diff ~1e-7).
**Action:** Always replace custom Python mathematical implementations of standard activation functions with their fused PyTorch equivalents (like `F.gelu`) where available, specifically verifying the `approximate` flag matches the desired behavior.
