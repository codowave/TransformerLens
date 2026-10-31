# CLAUDE.md — research/

このディレクトリで作業する際のガイド。See the repo-root `CLAUDE.md` for how this fits alongside the vendored `transformer_lens/` library, which this file does not cover.

コードコメント・docstring・このファイル自体を含め、`research/` 配下は日本語で書く。`transformer_lens/` にはこの規約は適用されない。

## What this is

`research/hypotheses/*.md` は仮説ファイル：YAML front-matter（claims, structural checks, known failure points, promotion criteria）に続けて自由記述の根拠が書かれる。今のところ `hyp-001.md` のみ存在し、transformer の Q/K/V attention とスウェーデンボルグの三層対応理論（天界・霊的・自然的）の構造的対応を主張している。

このディレクトリ自体にはツールはない。仮説ファイルを検証する CLI（`python -m research_os verify ...`）は `research_os/` にあり、使い方・タスクの説明は `research_os/CLAUDE.md` を参照。検証対象になる相応辞典データは `biblical_correspondence/` にあり、詳細は `biblical_correspondence/CLAUDE.md` を参照。

仮説ファイルを直接編集する場合は、YAML front-matter の構造（`hyp-001.md` を参照）を崩さないこと。promotion stage（`exploration` → `candidate` → `verified`）や `mitigation_status`/`mitigation_rejection_reason` は `research_os verify` の判定結果を反映して更新される値なので、検証を経ずに手で書き換えない。
