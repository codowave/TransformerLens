# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A fork of [TransformerLens](https://github.com/TransformerLensOrg/TransformerLens) (mechanistic interpretability library for GPT-2-style language models) that additionally hosts two custom, actively-developed projects:

1. **`biblical_correspondence/`** — A FastAPI web app (Japanese UI) serving a dictionary of Swedenborg's biblical correspondences, with a streaming Claude chat backend and an original-language (Hebrew/Greek) verification layer.
2. **`research_os/` + `research/hypotheses/`** — A hypothesis-verification CLI investigating whether transformer Q/K/V attention has a formal structural mapping to Swedenborg's three-level correspondence theory (celestial/spiritual/natural).

Recent development (see git log) happens almost entirely in these two custom projects. `transformer_lens/` is the upstream library code; `easy_transformer/` is a deprecated alias that re-exports `transformer_lens`.

Code comments, docstrings, and commit messages in the custom projects are written in **Japanese** — follow that convention when working there.

## Commands

### TransformerLens core (Poetry)

```bash
poetry install --with dev          # setup (CI also runs: poetry check --lock)
make unit-test                     # poetry run pytest tests/unit
make integration-test              # poetry run pytest tests/integration
make acceptance-test               # poetry run pytest tests/acceptance (slow; downloads models)
make docstring-test                # poetry run pytest transformer_lens/ (doctests)
make coverage-report-test          # coverage across unit+integration+acceptance
make format                        # pycln + isort + black (line length 100)
make check-format                  # CI format check
poetry run mypy .                  # type check (excludes tests/, demos/, docs/, easy_transformer/)
make build-docs / make docs-hot-reload
```

Run a single test: `poetry run pytest tests/unit/path/to/test_file.py::test_name`

Note: `pyproject.toml` sets pytest `addopts` globally (`--doctest-modules`, `--nbval`, jaxtyping/beartype runtime type checking on `transformer_lens`). Shape annotations in function signatures are enforced at test time. These addopts also apply when running pytest anywhere under the repo root and require the Poetry dev-group plugins — when running the `biblical_correspondence` tests outside the Poetry env, disable them with `-o addopts=""`.

### biblical_correspondence (plain pip, not Poetry)

```bash
cd biblical_correspondence
pip install -r requirements.txt    # fastapi, uvicorn, anthropic
export ANTHROPIC_API_KEY=...
python app.py                      # serves http://localhost:8000

pytest tests/ -o addopts=""        # regression tests (no API key or data needed)
bash scripts/bootstrap_morph_data.sh   # OPTIONAL: clone morphhb/morphgnt corpora into data/
curl http://localhost:8000/api/lexicon/health   # check data availability
```

### research_os

```bash
python -m research_os verify research/hypotheses/hyp-001.md --task mechanism_mapping --dry-run
python -m research_os verify research/hypotheses/hyp-001.md --task textual_comparison --mode falsification --focus fp-2
```

Tasks: `mechanism_mapping`, `textual_comparison`, `activation_analysis`. `--dry-run` skips computation and does static structural checks only; non-dry-run `mechanism_mapping`/`activation_analysis` use TransformerLens to extract real attention patterns (needs model download/GPU). Results are printed as YAML.

## Architecture

### transformer_lens (upstream library)

- **`hook_points.py`** is the foundation: `HookPoint` modules are inserted throughout the model, and `HookedRootModule` provides `run_with_cache` / `run_with_hooks`. Everything else builds on this.
- **`HookedTransformer.py`** is the main user-facing class; `HookedTransformerConfig.py` holds the unified config that all 50+ supported architectures are normalized into.
- **`loading_from_pretrained.py`** + **`pretrained/weight_conversions/`** map HuggingFace checkpoints into that unified format — one conversion module per architecture. Adding model support means adding a config entry and a weight conversion.
- **`components/`** contains the modular layers (attention variants, MLPs in `components/mlps/`, norms, embeds) assembled by `transformer_block.py`; `factories/` picks concrete MLP/activation implementations from config.
- **`ActivationCache.py`** and **`FactoredMatrix.py`** are the main analysis data structures; `patching.py`, `evals.py`, `head_detector.py` are analysis utilities.
- `HookedEncoder` (BERT), `HookedEncoderDecoder` (T5), and `BertNextSentencePrediction` are parallel model classes for non-decoder architectures.

### biblical_correspondence

- **`app.py`** — FastAPI app. Loads `data/dictionary.json` at startup and embeds the full dictionary into the Claude system prompt (with prompt caching); chat responses stream via SSE. Static PWA frontend in `static/`.
- **`lexicon/`** — Strong's lexicon + original-language verse verification against optional morphhb (Hebrew) / morphgnt (Greek) corpora. Exposed under `/api/lexicon`.
- **`correspondence/`** — `correspondence_index.json` (paragraph-level index of Swedenborg passages keyed by OSIS refs like `Gen.3.5`) and its lookup layer, injected into chat context.

**Key invariant ("Codex P1"): the three-state distinction.** Lookups return `found` / `not_found` / `unavailable` and these must never be conflated:

| status | contains | meaning |
|---|---|---|
| `found` | `true` | verified present in the corpus |
| `not_found` | `false` | searched the corpus, verified absent |
| `unavailable` | `null` | corpus/data not available — cannot assert either way |

"Couldn't check" is a different fact from "checked and absent." Missing data is **not** an error state: every endpoint must degrade to `unavailable` rather than crash (this is what `tests/test_lexicon_health.py` pins down — it forcibly points the data paths at nonexistent dirs). See `README_DATA.md`.

Related: entries in `correspondence_index.json` that have not been checked against the original text carry `verified: false` / `status: "unverified_reference"` and must not be used as evidence — only as reference candidates.

### research_os + research/hypotheses

- Hypotheses live in `research/hypotheses/*.md` as YAML front-matter documents: `id`, `stage`, `claims`, `structural_checks`, `candidate_failure_points` (fp-1, fp-2, …), `verification_order`, `promotion_criteria`, and a `promotion_history` audit trail.
- Stage lifecycle: `exploration` → `candidate` → `verified`, with explicit demotion back to `exploration` on fatal structural failure. Promotions/demotions are recorded in the hypothesis file itself.
- **Verification order is a deliberate methodology**: `mechanism_mapping` (structural compatibility of causal direction/symmetry/information flow) runs *before* `textual_comparison`, because searching the dense correspondence index for "supporting" passages will always find something and gives hypotheses premature footing. `textual_comparison` defaults to `falsification` mode — it searches for passages that *break* the proposed mapping; `support` mode is exploratory fuel only, never verification.
- Rejected mitigations stay in the file with their rejection reasons (e.g. `rationale_deprecated`, `mitigation_rejection_reason`) rather than being deleted — the record of what was tried and why it failed is part of the artifact.

## CI and conventions

- `.github/workflows/checks.yml` runs format check, mypy, docstring tests, unit/acceptance tests (Python 3.9–3.12 matrix for tests; 3.11 for checks), notebook tests (nbval against `demos/`), and a docs build. `poetry check --lock` runs first — keep `poetry.lock` in sync with `pyproject.toml`.
- Formatting: black (line length 100), isort (black profile), pycln. mypy covers `transformer_lens/` and root-level code but excludes `tests/`, `demos/`, `docs/`, `easy_transformer/`.
- The custom projects (`biblical_correspondence/`, `research_os/`) are not covered by the Poetry/CI setup; their tests run with plain pytest.
