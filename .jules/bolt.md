## 2024-05-24 - PyTorch Native GeLU is 4x Faster
**Learning:** PyTorch's native `F.gelu(..., approximate="tanh")` is roughly 4x faster on GPU than manually implementing the tanh approximation equation in PyTorch.
**Action:** Always prefer `F.gelu(..., approximate="tanh")` over manual implementations of GPT-2's `gelu_new` or `gelu_fast`.

## 2024-05-24 - Cross Entropy Loss Optimization Surprise
**Learning:** Flattening and using `F.cross_entropy` instead of manual `gather` was actually slower on GPU for `lm_cross_entropy_loss` in this specific setup.
**Action:** Do not optimize `lm_cross_entropy_loss` with flattening + `F.cross_entropy` without rigorous benchmarking across sizes, as manual indexing may be faster due to kernel launch overheads or specific tensor shapes.
