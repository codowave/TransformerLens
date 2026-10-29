import torch
import torch.nn.functional as F
import numpy as np
import time

def gelu_new(input):
    return (
        0.5
        * input
        * (1.0 + torch.tanh(np.sqrt(2.0 / np.pi) * (input + 0.044715 * torch.pow(input, 3.0))))
    )

def gelu_fast(input):
    return 0.5 * input * (1.0 + torch.tanh(input * 0.7978845608 * (1.0 + 0.044715 * input * input)))

def native_gelu(input):
    return F.gelu(input, approximate="tanh")

x = torch.randn(32, 1024, 4096)

# Warmup
for _ in range(10):
    gelu_new(x)
    gelu_fast(x)
    native_gelu(x)

t0 = time.time()
for _ in range(100):
    gelu_new(x)
t1 = time.time()
print(f"gelu_new: {t1 - t0:.4f}s")

t0 = time.time()
for _ in range(100):
    gelu_fast(x)
t1 = time.time()
print(f"gelu_fast: {t1 - t0:.4f}s")

t0 = time.time()
for _ in range(100):
    native_gelu(x)
t1 = time.time()
print(f"native_gelu: {t1 - t0:.4f}s")
