"""Attention.

Utilities for attention components.
"""

import einops
import torch
import torch.nn.functional as F
from jaxtyping import Float


def simple_attn_linear(
    input: Float[torch.Tensor, "batch pos d_model"],
    w: Float[torch.Tensor, "head_index d_model d_head"],
    b: Float[torch.Tensor, "head_index d_head"],
) -> Float[torch.Tensor, "batch pos head_index d_head"]:
    """Linear layer for attention calculation."""

    if input.device != w.device:
        w = w.to(input.device)
    if input.device != b.device:
        b = b.to(input.device)

    # Use native PyTorch F.linear for significant speedup, avoiding rearrange overhead.
    # w: H M D -> (H D) M
    w_reshaped = w.transpose(1, 2).reshape(-1, w.size(1))
    b_reshaped = b.reshape(-1)

    out = F.linear(input, w_reshaped, b_reshaped)  # B P (H D)
    return out.view(*input.shape[:-1], w.shape[0], w.shape[2])


def complex_attn_linear(
    input: Float[torch.Tensor, "batch pos head_index d_model"],
    w: Float[torch.Tensor, "head_index d_model d_head"],
    b: Float[torch.Tensor, "head_index d_head"],
) -> Float[torch.Tensor, "batch pos head_index d_head"]:
    """Linear layer for attention calculation.

    This is almost the same as simple_attn_linear, but the input tensor has an extra head_index dimension, used when calculating the input of each attention head separately.
    """

    # Use native PyTorch einsum for significant speedup over einops.einsum
    result = torch.einsum("... h m, h m d -> ... h d", input, w)
    return result + b
