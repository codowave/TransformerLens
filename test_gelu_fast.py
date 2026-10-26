import torch
import torch.nn.functional as F
import numpy as np

def gelu_fast(input):
    return 0.5 * input * (1.0 + torch.tanh(input * 0.7978845608 * (1.0 + 0.044715 * input * input)))

x = torch.randn(10, 10, dtype=torch.float32)

print("Max diff:", torch.max(torch.abs(gelu_fast(x) - F.gelu(x, approximate="tanh"))).item())
