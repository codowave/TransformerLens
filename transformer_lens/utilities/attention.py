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

    # Native operations avoid einops string parsing overhead, ~25% faster
    w = w.transpose(-1, -2).reshape(-1, w.shape[-2])
    b_ = b.view(-1)

    return F.linear(input, w, b_).reshape(input.shape[0], input.shape[1], b.shape[0], b.shape[1])


def complex_attn_linear(
    input: Float[torch.Tensor, "batch pos head_index d_model"],
    w: Float[torch.Tensor, "head_index d_model d_head"],
    b: Float[torch.Tensor, "head_index d_head"],
) -> Float[torch.Tensor, "batch pos head_index d_head"]:
    """Linear layer for attention calculation.

    This is almost the same as simple_attn_linear, but the input tensor has an extra head_index dimension, used when calculating the input of each attention head separately.
    """

    # torch.einsum avoids einops string parsing overhead, ~50% faster
    result = torch.einsum(
        "b p h m, h m d -> b p h d",
        input,
        w,
    )
    return result + b
