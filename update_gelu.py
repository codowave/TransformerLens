import re

with open("transformer_lens/utils.py", "r") as f:
    content = f.read()

content = re.sub(
    r"def gelu_new\([\s\S]*?return \([\s\S]*?\)\n",
    'def gelu_new(\n    input: Float[torch.Tensor, "batch pos d_mlp"]\n) -> Float[torch.Tensor, "batch pos d_mlp"]:\n    """\n    Implementation of GeLU used by GPT2 - subtly different from PyTorch\'s exact GeLU,\n    but exactly matches PyTorch\'s tanh approximation.\n    Using native F.gelu is roughly 4x faster.\n    """\n    return F.gelu(input, approximate="tanh")\n',
    content
)

content = re.sub(
    r"def gelu_fast\([\s\S]*?return 0\.5 \* input \* \(1\.0 \+ torch\.tanh\(input \* 0\.7978845608 \* \(1\.0 \+ 0\.044715 \* input \* input\)\)\)\n",
    'def gelu_fast(\n    input: Float[torch.Tensor, "batch pos d_mlp"]\n) -> Float[torch.Tensor, "batch pos d_mlp"]:\n    return F.gelu(input, approximate="tanh")\n',
    content
)

with open("transformer_lens/utils.py", "w") as f:
    f.write(content)
