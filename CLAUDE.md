# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This is a fork of [TransformerLens](https://github.com/TransformerLensOrg/TransformerLens), a library
for mechanistic interpretability of GPT-2-style language models. It exposes internal activations of
50+ open-source language models and lets you cache, edit, and replace those activations at runtime.

The repo also contains two unrelated, self-contained side projects that are **not** part of the
TransformerLens library itself — treat them as separate codebases living in the same repo:

- `biblical_correspondence/` — a standalone Japanese-language web app (FastAPI-style `app.py` +
  static PWA frontend) for looking up Swedenborgian scriptural correspondences, with its own
  `requirements.txt`, lexicon data, and tests (`biblical_correspondence/tests/`).
- `research_os/` — a small standalone CLI (`python -m research_os verify <hypothesis.md> --task ...`)
  for running verification tasks (`mechanism_mapping`, `textual_comparison`) against hypothesis files
  in `research/hypotheses/`. Also Japanese-language, `argparse`-based.

Unless a task explicitly concerns one of those two directories, "the codebase" below refers to the
`transformer_lens/` package.

## Development setup

This project uses [Poetry](https://python-poetry.org/). Python `>=3.8,<4.0` is supported (CI runs
3.9–3.11).

```bash
poetry config virtualenvs.in-project true
poetry install --with dev,docs,jupyter
```

## Common commands (see `makefile`)

```bash
make format              # pycln + isort + black, auto-fix
make check-format        # same tools, check-only (what CI runs)

make unit-test           # poetry run pytest tests/unit
make integration-test    # poetry run pytest tests/integration
make acceptance-test     # poetry run pytest tests/acceptance
make docstring-test      # poetry run pytest transformer_lens/  (doctest via --doctest-modules)
make notebook-test       # runs a curated subset of demos/*.ipynb through nbval
make coverage-report-test  # unit+integration+acceptance with coverage (--cov=transformer_lens/)
make test                 # unit-test + acceptance-test + docstring-test + notebook-test

make docs-hot-reload     # poetry run docs-hot-reload
make build-docs          # poetry run build-docs
```

Type checking is not in the makefile but is run in CI: `poetry run mypy .`

To run a single test:

```bash
poetry run pytest tests/unit/path/to/test_file.py::test_name
poetry run pytest tests/unit/path/to/test_file.py -k "some_pattern"
```

Test suites live under `tests/unit`, `tests/integration`, `tests/acceptance`, and
`tests/manual_checks` (not run in CI). `pytest` is configured (in `pyproject.toml`) with
`--doctest-modules`, `--doctest-plus`, `--nbval`, and jaxtyping/beartype checking enabled globally, so
running pytest against `transformer_lens/` also executes docstring examples and shape-checks
`jaxtyping`-annotated tensors.

CI (`.github/workflows/checks.yml`) caches HF weights for `gpt2`, `attn-only-{1,2,3,4}l`, and
`tiny-stories-1M` — prefer these models in new tests (`attn-only-1l` / `tiny-stories-1M` over `gpt2`,
since CI runners are CPU-only and `gpt2` is comparatively slow).

## Formatting & typing conventions

- `black` with line length 100 (not the default 88), `isort` (profile=`black`), `pycln` for unused
  imports — run via `make format` before committing.
- `mypy` config in `pyproject.toml` excludes `assets`, `demos`, `docs`, `easy_transformer`, `tests`.
- Public functions/classes use Google-style docstrings with reST extensions (see
  `docs/source/content/contributing.md` for the exact section order: Title, description, Warning,
  Examples with doctest-checked `>>>` blocks, Args, Returns, Raises). Cross-reference other symbols
  with `` :class:`transformer_lens.HookedTransformer` `` etc. Docstring examples are executed as
  doctests in CI (`make docstring-test`), so keep them runnable.
- Tensor shapes are documented/enforced with `jaxtyping` + `beartype`/`typeguard`.

## Architecture

### Core model classes

- **`HookedTransformer`** (`transformer_lens/HookedTransformer.py`, ~2600 lines) — the main model
  class, a decoder-only transformer with a hook on every interesting activation. Loaded via
  `HookedTransformer.from_pretrained(name)`, which pulls HuggingFace weights and converts them into
  TransformerLens's internal format (see "Weight loading" below). Also supports
  `run_with_cache(...)` to get `(logits, ActivationCache)` and `run_with_hooks(...)` to run with
  temporary hook functions attached.
- **`HookedEncoder`** / **`HookedEncoderDecoder`** / **`BertNextSentencePrediction`** — BERT-style
  encoder-only and encoder-decoder (T5-style) variants of the same hooking approach.
- **`HookedTransformerConfig`** (`HookedTransformerConfig.py`) — a dataclass holding every
  architectural knob (`d_model`, `n_layers`, `n_heads`, `act_fn`, positional embedding type,
  normalization type, etc). See `further_comments.md` for deep-dive explanations of non-obvious
  options like `positional_embeddings_type == "shortformer"`, `fold_ln`, `center_writing_weights`,
  `center_unembed`, and `fold_value_biases` — these are weight-preprocessing transforms applied at
  load time that are mathematically equivalent to the original model but easier to interpret.
- **`ActivationCache`** (`ActivationCache.py`) — dict-like wrapper returned by `run_with_cache`,
  keyed by hook names (e.g. `blocks.0.attn.hook_pattern`), with helpers like `.remove_batch_dim()`,
  `.to(device)`, `.toggle_autodiff()`.
- **`FactoredMatrix`** — represents low-rank `A @ B` matrix products (e.g. `W_Q @ W_K.T`) lazily, for
  efficient analysis (SVD, eigenvalues) without materializing the full matrix.

### Hook system

- **`hook_points.py`** is the foundation everything else builds on: `HookPoint` (an identity
  `nn.Module` that hooks can attach to) and `HookedRootModule` (base class providing
  `run_with_hooks`, `add_hook`, `reset_hooks`, hook-name caching, etc). `HookedTransformer` and the
  BERT/encoder variants all subclass `HookedRootModule`.
- Hooks are referenced by dotted string names following the pattern `blocks.{layer}.{component}.hook_{activation}`
  (e.g. `blocks.0.attn.hook_pattern`, `blocks.0.mlp.hook_pre`, `blocks.0.hook_resid_post`).
  `utils.py` has helpers for building/parsing these names.

### Model components (`transformer_lens/components/`)

Building blocks assembled into `HookedTransformer` by `HookedTransformerConfig`-driven logic:
`embed.py`, `pos_embed.py`, `attention.py` / `abstract_attention.py` / `grouped_query_attention.py` /
`t5_attention.py`, `mlps/` (regular, gated, MoE variants selected via `factories/mlp_factory.py`),
`layer_norm.py` / `layer_norm_pre.py` / `rms_norm.py` / `rms_norm_pre.py`, `transformer_block.py`
(one attn+MLP block), `unembed.py`, plus BERT-specific pieces (`bert_block.py`, `bert_embed.py`,
`bert_mlm_head.py`, `bert_nsp_head.py`, `bert_pooler.py`).

`transformer_lens/factories/` (`activation_function_factory.py`, `mlp_factory.py`) select the
concrete component implementation based on config fields (e.g. `act_fn`, whether the model is MoE).

### Weight loading (`loading_from_pretrained.py` + `pretrained/`)

- `loading_from_pretrained.py` (~2000 lines) is the registry of every officially supported model name
  (`OFFICIAL_MODEL_NAMES`) and maps aliases to canonical names, builds the `HookedTransformerConfig`
  for a given HF model, and drives `HookedTransformer.from_pretrained`.
- `transformer_lens/pretrained/weight_conversions/` has one file per model family (`gpt2.py`,
  `llama.py`, `mistral.py`, `qwen2.py`, `qwen3.py`, `gemma.py`, `t5.py`, `bert.py`, `mixtral.py`,
  `phi3.py`, `neox.py`, `bloom.py`, `opt.py`, ...) — each converts that family's HF `state_dict` into
  TransformerLens's internal parameter naming/shape convention. When adding support for a new model
  family, this is the pattern to follow: add a conversion module here, register the model name(s) in
  `loading_from_pretrained.py`.

### Other top-level modules

- `evals.py` — evaluation helpers (e.g. induction-head, factual-recall evals).
- `train.py` — a minimal training loop for toy models.
- `head_detector.py` — heuristics for detecting attention head types (e.g. induction heads,
  previous-token heads).
- `patching.py` — activation patching utilities.
- `SVDInterpreter.py` — SVD-based analysis of weight matrices.
- `past_key_value_caching.py` — `HookedTransformerKeyValueCache` for autoregressive generation.
- `utilities/` — smaller shared helpers: `devices.py` (device placement), `attention.py`,
  `activation_functions.py`, `addmm.py`.
- `easy_transformer/` — a near-empty package kept only for backwards-compat re-exports (the library
  was originally named EasyTransformer); `transformer_lens/__init__.py` also re-exports
  `HookedTransformer` as `EasyTransformer` for the same reason. Don't build new functionality here.

### Demos and docs

- `demos/*.ipynb` are both user-facing tutorials and part of the test suite (`make notebook-test` /
  the `notebook-checks` CI job runs a curated subset through `nbval`). If you touch behavior a demo
  notebook depends on, expect to need to update the notebook's cell outputs too.
- `docs/` is a Sphinx project (`docs/source/`); `make build-docs` / `make docs-hot-reload` build it.
  API docs are generated from docstrings, so docstring accuracy matters.

## Notes on library conventions

- Config options that are non-obvious or affect numerical equivalence with the original HF model are
  documented in `further_comments.md` rather than repeated inline everywhere — check there first
  before guessing at semantics of a `HookedTransformerConfig` flag.
- `HookedSAETransformer`/SAE support was removed in v2.0 and moved to
  [SAELens](http://github.com/jbloomAus/SAELens) — don't re-add SAE-specific functionality here.
- Version in `pyproject.toml` is intentionally `0.0.0`; the real version is set by the release
  pipeline, not edited by hand.
