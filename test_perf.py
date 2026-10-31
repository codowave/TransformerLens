import time
import torch
import torch.nn.functional as F

from transformer_lens.utils import gelu_new, gelu_fast

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
