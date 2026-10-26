import torch
import torch.nn.functional as F
import numpy as np
import timeit

def gelu_new(input):
    # Implementation of GeLU used by GPT2 - subtly different from PyTorch's
    return (
        0.5
        * input
        * (1.0 + torch.tanh(np.sqrt(2.0 / np.pi) * (input + 0.044715 * torch.pow(input, 3.0))))
    )

def gelu_fast(input):
    return 0.5 * input * (1.0 + torch.tanh(input * 0.7978845608 * (1.0 + 0.044715 * input * input)))

def gelu_pytorch_tanh(input):
    """
    Approximation of the gelu activation function, used in some older models.
    """
    return F.gelu(input, approximate="tanh")

x = torch.randn(1000, 1000, dtype=torch.float32)

t_new = timeit.timeit(lambda: gelu_new(x), number=100)
t_fast = timeit.timeit(lambda: gelu_fast(x), number=100)
t_pytorch = timeit.timeit(lambda: gelu_pytorch_tanh(x), number=100)
t_pytorch_gelu = timeit.timeit(lambda: F.gelu(x), number=100)

print(f"gelu_new: {t_new:.5f}s")
print(f"gelu_fast: {t_fast:.5f}s")
print(f"gelu_pytorch_tanh: {t_pytorch:.5f}s")
print(f"F.gelu: {t_pytorch_gelu:.5f}s")

if torch.cuda.is_available():
    print("Running with CUDA:")
    x = x.cuda()
    # warmup
    for _ in range(10):
        gelu_new(x)
        gelu_fast(x)
        gelu_pytorch_tanh(x)

    torch.cuda.synchronize()
    t0 = timeit.default_timer()
    for _ in range(100):
        gelu_new(x)
    torch.cuda.synchronize()
    t_new = timeit.default_timer() - t0

    torch.cuda.synchronize()
    t0 = timeit.default_timer()
    for _ in range(100):
        gelu_fast(x)
    torch.cuda.synchronize()
    t_fast = timeit.default_timer() - t0

    torch.cuda.synchronize()
    t0 = timeit.default_timer()
    for _ in range(100):
        gelu_pytorch_tanh(x)
    torch.cuda.synchronize()
    t_pytorch = timeit.default_timer() - t0

    print(f"gelu_new (CUDA): {t_new:.5f}s")
    print(f"gelu_fast (CUDA): {t_fast:.5f}s")
    print(f"gelu_pytorch_tanh (CUDA): {t_pytorch:.5f}s")
