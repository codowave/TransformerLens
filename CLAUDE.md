# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

This repo hosts two independent projects that happen to share one git history. Their tooling, languages, and conventions do not overlap — figure out which one a task belongs to before doing anything else, then read **that project's own CLAUDE.md** (each subdirectory's CLAUDE.md loads automatically once you're working inside it; don't assume this root file alone gives you everything).

| Working in... | Read | What it is |
|---|---|---|
| `transformer_lens/` | `transformer_lens/CLAUDE.md` | vendored upstream [TransformerLens](https://github.com/TransformerLensOrg/TransformerLens) — mechanistic-interpretability toolkit for GPT-2-style models |
| `research_os/` | `research_os/CLAUDE.md` | hypothesis-verification CLI that runs checks against `research/hypotheses/*.md` |
| `research/` | `research/CLAUDE.md` | the hypothesis files themselves (`research/hypotheses/*.md`) |
| `biblical_correspondence/` | `biblical_correspondence/CLAUDE.md` | Japanese-language FastAPI app + lookup layer that `research_os` verifies claims against |

`easy_transformer/` is a deprecated shim package — importing it just logs a warning and re-exports `transformer_lens`. Don't add new code there.

`research/hypotheses/hyp-001.md` is the document that ties the two projects together: it claims a structural analogy between transformer Q/K/V attention (`transformer_lens/`) and Swedenborgian correspondence theory (`biblical_correspondence/`), and `research_os/` is the tool that verifies or falsifies that claim against both. `activation_analysis` (task 3 in `research_os`, not yet implemented — see `research_os/verify.py`) is the point where `research_os` will actually invoke `transformer_lens` on real models; today that's the only place the two projects' code is meant to touch.
