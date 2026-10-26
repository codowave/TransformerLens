import torch
import torch.nn.functional as F
import numpy as np

def gelu_new(input):
    return (
        0.5
        * input
        * (1.0 + torch.tanh(np.sqrt(2.0 / np.pi) * (input + 0.044715 * torch.pow(input, 3.0))))
    )

def gelu_pytorch_tanh(input):
    return F.gelu(input, approximate="tanh")

x = torch.randn(10, 10, dtype=torch.float32)

print("Max diff:", torch.max(torch.abs(gelu_new(x) - gelu_pytorch_tanh(x))).item())
