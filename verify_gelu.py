import torch
import torch.nn.functional as F
import numpy as np

def gelu_new_old(input):
    return (
        0.5
        * input
        * (1.0 + torch.tanh(np.sqrt(2.0 / np.pi) * (input + 0.044715 * torch.pow(input, 3.0))))
    )

def gelu_fast_old(input):
    return 0.5 * input * (1.0 + torch.tanh(input * 0.7978845608 * (1.0 + 0.044715 * input * input)))

x = torch.randn(100, 100, dtype=torch.float32)

new_old = gelu_new_old(x)
fast_old = gelu_fast_old(x)
pt_tanh = F.gelu(x, approximate="tanh")

print("gelu_new diff:", torch.max(torch.abs(new_old - pt_tanh)).item())
print("gelu_fast diff:", torch.max(torch.abs(fast_old - pt_tanh)).item())
