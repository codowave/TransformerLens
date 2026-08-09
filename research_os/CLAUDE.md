# CLAUDE.md — research_os/

このディレクトリで作業する際のガイド。See the repo-root `CLAUDE.md` for how this fits alongside the vendored `transformer_lens/` library, which this file does not cover.

コードコメント・docstring・このファイル自体を含め、`research_os/`（および `research/`）配下は日本語で書く。`transformer_lens/` にはこの規約は適用されない。

## What this is

`research/hypotheses/*.md` は仮説ファイル：YAML front-matter（claims, structural checks, known failure points, promotion criteria）に続けて自由記述の根拠が書かれる。今のところ `hyp-001.md` のみ存在し、transformer の Q/K/V attention とスウェーデンボルグの三層対応理論（天界・霊的・自然的）の構造的対応を主張している。

`research_os/` はその仮説ファイルに対して検証タスクを実行する CLI：

```shell
python -m research_os verify research/hypotheses/hyp-001.md --task mechanism_mapping --dry-run
python -m research_os verify research/hypotheses/hyp-001.md --task textual_comparison --mode falsification --focus fp-2
```

`--task` は次の3種類（`research_os/__main__.py` で定義）：

- `mechanism_mapping` — 静的構造互換性チェック。モデル不要。
- `textual_comparison` — `biblical_correspondence/correspondence/correspondence_index.json` を検索し、確証・反証となる典拠を探す（詳細は `biblical_correspondence/CLAUDE.md`）。
- `activation_analysis` — 実際の `transformer_lens` モデルを動かして attention パターンを取得する予定のタスク。**未実装**（`research_os/verify.py` 参照）。

タスクの実行順序が重要：`mechanism_mapping` が `textual_comparison` より先。構造の因果方向・対称性が破綻している仮説を、意味密度の高い文言検索（似ている記述は必ず見つかる）に進めてしまうと、検証にならない足場を仮説に与えてしまう。

結果は YAML で出力される（`research_os/tasks/mechanism_mapping.py` の `MechanismMappingResult`、`research_os/tasks/textual_comparison.py` の `TextualComparisonResult`）。

仮説の promotion stage（`exploration` → `candidate` → `verified`）と未解決の failure point（`hyp-001.md` の `fp-1`〜`fp-4`）は、仮説ファイル自身の YAML front-matter で管理する。`mitigation_status`/`mitigation_rejection_reason` は、提案された緩和策が却下された場合にその理由を記録するフィールド。
