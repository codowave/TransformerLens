## 2023-10-25 - Use native PyTorch approximations for GeLU
**Learning:** PyTorch provides native implementations for commonly approximated activation functions like GPT-2's GeLU (`F.gelu(x, approximate="tanh")`). Custom element-wise mathematical implementations (`x * 0.5 * (1 + tanh(...))`) using `torch.tanh` and `torch.pow` are ~4x slower on CPU because they don't utilize fused kernels.
**Action:** Always prefer native, fused PyTorch operations (`F.gelu`) over custom element-wise math when implementing specific activation function behaviors.
