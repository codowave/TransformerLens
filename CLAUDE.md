# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

This repo has two very different things living side by side:

1. **`transformer_lens/`** — the upstream [TransformerLens](https://github.com/TransformerLensOrg/TransformerLens) library, a mechanistic-interpretability toolkit for GPT-2-style language models (load 50+ open models, cache/edit/patch internal activations via a hook system).
2. **`biblical_correspondence/`** and **`research_os/`** — a bolted-on research project, unrelated to interpretability tooling on its surface, that uses this repo as its home. It investigates a hypothesis (`research/hypotheses/hyp-001.md`) about structural analogies between transformer Q/K/V attention and Swedenborgian correspondence theory, and ships a Japanese-language FastAPI chat app for browsing that theology. `research_os` is the CLI that runs verification tasks against hypothesis files; `activation_analysis` (task 3, not yet implemented) is the point where it will actually invoke `transformer_lens` on real models.

`easy_transformer/` is a deprecated shim package — importing it just logs a warning and re-exports `transformer_lens`. Don't add new code there.

When working in this repo, first figure out which of the two projects a task belongs to — their tooling, languages, and conventions are independent (Python/poetry/pytest for TransformerLens; FastAPI + Japanese docstrings/comments for the biblical_correspondence/research_os side).

---

## Part 1: TransformerLens library

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

CI (`.github/workflows/checks.yml`) runs, per PR: `make unit-test`, `make acceptance-test`, `poetry build` (compatibility-checks job); `make check-format`, `make docstring-test`, `mypy .`, `make coverage-report-test`, `poetry build` (code-checks job); and an allow-listed subset of demo notebooks (notebook-checks job).

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

Weight processing note: `HookedTransformer` applies transformations like LayerNorm folding (`fold_ln`), centering writing weights, and folding value-bias into the reasoning-relevant components when loading pretrained weights, so the model's internal parameters are not always numerically identical to the original checkpoint even though the function computed is equivalent. See `further_comments.md` for a detailed writeup of these weight-processing options (LayerNorm folding, shortformer positional embeddings, etc.) before changing anything in that area.

Tests mirror this structure under `tests/unit`, `tests/integration`, `tests/acceptance` (unit tests exercise components/utilities in isolation; integration tests check specific mechanisms like KV caching, padding, GQA; acceptance tests run full `HookedTransformer`/`HookedEncoder`/`HookedEncoderDecoder` behavior, often against real pretrained weights).

Formatting/lint config lives in `pyproject.toml`: black (line-length 100), isort (black profile), pycln (unused imports), mypy (`check_untyped_defs`, excludes `assets`/`demos`/`docs`/`easy_transformer`/`tests`), and a strict pyright config that is currently scoped to just `transformer_lens/hook_points.py`.

---

## Part 2: `research_os/` and `biblical_correspondence/`

### What these are

- **`research/hypotheses/*.md`** — hypothesis files: a YAML front-matter block (claims, structural checks, known failure points, promotion criteria) followed by free-text rationale. `hyp-001.md` is the only one so far, proposing that transformer Q/K/V attention structurally corresponds to Swedenborg's three-layer correspondence theory (celestial/spiritual/natural).
- **`research_os/`** — the verification CLI that operates on those hypothesis files:
  ```shell
  python -m research_os verify research/hypotheses/hyp-001.md --task mechanism_mapping --dry-run
  python -m research_os verify research/hypotheses/hyp-001.md --task textual_comparison --mode falsification --focus fp-2
  ```
  `--task` is one of `mechanism_mapping` (static structural compatibility check, no model needed), `textual_comparison` (searches `biblical_correspondence/correspondence/correspondence_index.json` for confirming/falsifying textual evidence), or `activation_analysis` (intended to run real `transformer_lens` models — not yet implemented, see `research_os/verify.py`). Task order matters: `mechanism_mapping` runs before `textual_comparison` — a hypothesis whose directionality/symmetry fails outright shouldn't proceed to a text search that will find superficially-similar-sounding passages regardless. Results are printed as YAML (`MechanismMappingResult`/`TextualComparisonResult` dataclasses in `research_os/tasks/`).
  Hypothesis promotion stages (`exploration` → `candidate` → `verified`) and open failure points (`fp-1`..`fp-4` in `hyp-001.md`) are tracked directly in the hypothesis file's YAML front matter, including `mitigation_status`/`mitigation_rejection_reason` when a proposed mitigation is rejected rather than accepted.
- **`biblical_correspondence/`** — a standalone FastAPI app (own `requirements.txt`, not part of the poetry project) serving a Japanese-language PWA: a chat interface backed by the Claude API (`app.py`) plus a `lexicon_router` sub-API for looking up Hebrew/Greek original-language text (Strong's numbers) and correspondence entries.
  ```shell
  cd biblical_correspondence
  pip install -r requirements.txt
  export ANTHROPIC_API_KEY="your-api-key"
  python app.py   # serves on localhost:8000
  ```
  Run its tests with: `cd biblical_correspondence && pytest tests/test_lexicon_health.py -v` (designed to pass with zero external data present).

### The three-state discipline (critical convention)

Every lookup surface in `biblical_correspondence/` (original-language verse verification, correspondence index lookup, the `/api/lexicon/health` endpoint) distinguishes **three** states, not two:

| status | meaning |
|---|---|
| `found` | checked, and the thing is present |
| `not_found` | checked, and the thing is confirmed absent |
| `unavailable` | not checked at all — e.g. the source data (`morphhb`/`morphgnt`, cloned separately via `biblical_correspondence/scripts/bootstrap_morph_data.sh`) isn't present, or the reference isn't in the index |

`unavailable` must serialize as `contains: null` (or an equivalent non-boolean sentinel), never `false` — collapsing "couldn't check" into "checked, not present" is called out in the codebase as the **"Codex P1" regression**, and there are tests specifically pinned against it (`biblical_correspondence/tests/test_lexicon_health.py`, `TestVerseVerifyUnavailable`). If you touch any lookup/verification code in this subtree, preserve this three-state return shape and don't let a missing-data exception get silently converted into a false negative.

The `biblical_lexicon` module in particular exists as an "external anchor" so that original-language claims are answered by checking the actual Hebrew/Greek text (via `morphhb`/`morphgnt`), not by an LLM's memory of what a word "sounds like" it should be — see `biblical_correspondence/lexicon/README.md` for a documented case (`Hos 4:1`) where relying on recall produced a wrong Strong's-number attribution that text-checking caught.

### Language convention

Code comments, docstrings, README files, and hypothesis documents in `biblical_correspondence/` and `research_os/` (and `research/`) are written in Japanese. Match that convention when editing those files; it does not apply to `transformer_lens/` itself.
