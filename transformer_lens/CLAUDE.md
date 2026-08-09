# CLAUDE.md — transformer_lens/

Guidance for working in the vendored TransformerLens library within this repository. See the repo-root `CLAUDE.md` if you haven't already — this repo also contains an unrelated project (`research_os/` + `biblical_correspondence/`) that this file does not cover.

## Vendor status — read before editing

`transformer_lens/` is an import of the upstream [TransformerLens](https://github.com/TransformerLensOrg/TransformerLens) library. This fork has no `upstream` git remote configured (`git remote -v` shows only `origin`, pointing at this fork), and every commit in this repo's history touching `transformer_lens/` carries an upstream PR reference in its message (e.g. `updated transformers (#939)`, `Add qwen3 (#937)`) — this fork has made **no local modifications** to `transformer_lens/` in its own history. Treat the directory as vendored and not being actively synced:

- Don't "fix" things here to match conventions or recent upstream changes you recall from elsewhere unless the task is specifically about this library — there's no mechanism in this repo pulling in upstream updates, so drive-by changes just diverge silently.
- If a change is needed to support the `research_os`/`biblical_correspondence` side of this repo (most likely the future `activation_analysis` task), prefer calling into `transformer_lens/` as a library from `research_os/` rather than editing internals here.
- Avoid adding new files at the repo root (outside any subproject directory) — root-level additions are the main merge-conflict surface if this fork ever resumes tracking upstream.

### Setup & commands

Dependency management is via **Poetry**.

```shell
poetry install --with dev
```

Common tasks (see `makefile`):

```shell
make format              # pycln + isort + black
make check-format        # same tools, check-only (used in CI)
make unit-test           # pytest tests/unit
make integration-test    # pytest tests/integration
make acceptance-test     # pytest tests/acceptance
make docstring-test      # pytest transformer_lens/ (runs doctests)
make coverage-report-test  # unit+integration+acceptance with coverage, HTML report
make notebook-test        # runs nbval against demos/*.ipynb (allow-listed set)
make test                 # unit-test + acceptance-test + docstring-test + notebook-test
poetry run mypy .          # type check (CI runs this separately)
```

Run a single test with pytest directly, e.g.:

```shell
poetry run pytest tests/unit/test_hook_points.py -k test_name
poetry run pytest tests/unit/components/some_test.py::TestClass::test_method
```

Note: `pyproject.toml` sets global pytest addopts including `--doctest-modules --doctest-plus --nbval`, so running `pytest` against source/notebook paths will also execute doctests/notebooks — scope your `pytest` invocation to `tests/unit`, `tests/integration`, or `tests/acceptance` when you just want unit-style tests.

CI (`.github/workflows/checks.yml`) runs, per PR: `make unit-test`, `make acceptance-test`, `poetry build` (compatibility-checks job); `make check-format`, `make docstring-test`, `mypy .`, `make coverage-report-test`, `poetry build` (code-checks job); and an allow-listed subset of demo notebooks (notebook-checks job). These jobs are skipped entirely for changes that only touch `*.md` files (see the `paths-ignore` block in that workflow).

### Architecture

The center of the library is **`HookedTransformer`** (`transformer_lens/HookedTransformer.py`), a from-scratch, fully hooked reimplementation of GPT-2-style transformers. Nearly everything else exists to support it:

- **`HookedTransformerConfig`** — the single config object (`n_layers`, `d_model`, `n_heads`, `act_fn`, `normalization_type`, etc.) that determines which architecture variant gets built. Most conditional logic in the model (e.g. which attention/MLP/normalization class to instantiate) branches on config fields rather than subclassing.
- **`transformer_lens/components/`** — the building blocks assembled into a `HookedTransformer`: `attention.py`/`abstract_attention.py`/`grouped_query_attention.py`/`t5_attention.py` (attention variants), `mlps/` + `factories/mlp_factory.py` (MLP variants, selected via `factories/activation_function_factory.py` for the activation fn), `layer_norm.py`/`layer_norm_pre.py`/`rms_norm.py`/`rms_norm_pre.py` (normalization, including the "folded" pre-normalization variants used after weight processing), `embed.py`/`pos_embed.py`/`token_typed_embed.py`, `transformer_block.py`, plus BERT-specific pieces (`bert_block.py`, `bert_embed.py`, `bert_mlm_head.py`, `bert_nsp_head.py`, `bert_pooler.py`) used by `HookedEncoder`/`HookedEncoderDecoder`/`BertNextSentencePrediction`.
- **`hook_points.py`** — the hooking mechanism (`HookPoint`, `HookedRootModule`) that every activation passes through, giving `run_with_cache`, `run_with_hooks`, and arbitrary activation editing/patching. This is the core abstraction that makes the library useful for interpretability — read this before modifying anything about how activations flow.
- **`loading_from_pretrained.py`** + **`pretrained/`** (with `pretrained/weight_conversions/`) — maps 50+ HuggingFace model families to `HookedTransformerConfig` + converts their weights into TransformerLens's internal parameter layout/naming. Adding support for a new model family means adding a weight-conversion function here plus config entries.
- **`ActivationCache.py`** — the object returned by `run_with_cache`; indexed access into cached activations by hook name.
- **`FactoredMatrix.py`** — utility for representing low-rank matrix products (e.g. `W_Q @ W_K.T`) without materializing them, used throughout for efficient analysis of circuits.
- **`patching.py`** / **`head_detector.py`** / **`SVDInterpreter.py`** / **`evals.py`** / **`train.py`** — higher-level analysis utilities (activation patching, automatic head-type detection, SVD-based interpretation, eval harnesses, a minimal training loop) built on top of the hooked model.
- **`utilities/`** — shared helpers (device placement, attention masking, addmm, activation functions).

Weight processing note: `HookedTransformer` applies transformations like LayerNorm folding (`fold_ln`), centering writing weights, and folding value-bias into the reasoning-relevant components when loading pretrained weights, so the model's internal parameters are not always numerically identical to the original checkpoint even though the function computed is equivalent. See `further_comments.md` (repo root) for a detailed writeup of these weight-processing options (LayerNorm folding, shortformer positional embeddings, etc.) before changing anything in that area.

Tests mirror this structure under `tests/unit`, `tests/integration`, `tests/acceptance` (unit tests exercise components/utilities in isolation; integration tests check specific mechanisms like KV caching, padding, GQA; acceptance tests run full `HookedTransformer`/`HookedEncoder`/`HookedEncoderDecoder` behavior, often against real pretrained weights).

Formatting/lint config lives in `pyproject.toml`: black (line-length 100), isort (black profile), pycln (unused imports), mypy (`check_untyped_defs`, excludes `assets`/`demos`/`docs`/`easy_transformer`/`tests`), and a strict pyright config that is currently scoped to just `transformer_lens/hook_points.py`.
