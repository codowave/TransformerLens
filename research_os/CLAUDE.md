# CLAUDE.md — research_os/

このディレクトリで作業する際のガイド。See the repo-root `CLAUDE.md` for how this fits alongside the vendored `transformer_lens/` library, which this file does not cover.

コードコメント・docstring・このファイル自体を含め、`research_os/` 配下は日本語で書く（`research/` は兄弟ディレクトリで、この規約は `research/CLAUDE.md` に別途書かれている——このファイルはそちらを継承しない）。`transformer_lens/` にはこの規約は適用されない。

## What this is

`research/hypotheses/*.md` は仮説ファイル：YAML front-matter（claims, structural checks, known failure points, promotion criteria）に続けて自由記述の根拠が書かれる。今のところ `hyp-001.md` のみ存在し、transformer の Q/K/V attention とスウェーデンボルグの三層対応理論（天界・霊的・自然的）の構造的対応を主張している。

`research_os/` はその仮説ファイルに対して検証タスクを実行する CLI：

```shell
python -m research_os verify research/hypotheses/hyp-001.md --task mechanism_mapping --dry-run
python -m research_os verify research/hypotheses/hyp-001.md --task textual_comparison --mode falsification --focus fp-2
```

`--task` は次の3種類（`research_os/__main__.py` で定義）：

- `mechanism_mapping` — 静的構造互換性チェック。モデル不要。
- `textual_comparison` — `biblical_correspondence/correspondence/correspondence_index.json` を対象に反証を探す（索引の形式は `biblical_correspondence/CLAUDE.md`）。判定の規則は下の「textual_comparison の判定規則」を参照。
- `activation_analysis` — 実際の `transformer_lens` モデルを動かして attention パターンを取得する予定のタスク。**未実装**（`research_os/verify.py` 参照）。

タスクの実行順序が重要：`mechanism_mapping` が `textual_comparison` より先。構造の因果方向・対称性が破綻している仮説を、意味密度の高い文言検索（似ている記述は必ず見つかる）に進めてしまうと、検証にならない足場を仮説に与えてしまう。

結果は YAML で出力される（`research_os/tasks/mechanism_mapping.py` の `MechanismMappingResult`、`research_os/tasks/textual_comparison.py` の `TextualComparisonResult`）。

仮説の promotion stage（`exploration` → `candidate` → `verified`）と未解決の failure point（`hyp-001.md` の `fp-1`〜`fp-4`）は、仮説ファイル自身の YAML front-matter で管理する。`mitigation_status`/`mitigation_rejection_reason` は、提案された緩和策が却下された場合にその理由を記録するフィールド。

## textual_comparison の判定規則（PR #31、2026-10-31）

**この節は要約であり、規則の正は `research_os/tasks/textual_comparison.py` と `research_os/tests/test_textual_comparison.py` にある。**

- キーワード一致は `leads`（読む候補）を挙げるだけで、判定に使わない。influx / love / will / light 等はスウェーデンボルグの基本語彙なので、一致数は反証の強さを測らない
- 反証項目（`challenges`）は、索引エントリに人が付けた `falsification_relevance == focus_fp` かつ `falsification_direction == "challenges"` のものだけ
- `verified` は三状態：`true`＝原典照合済み、`false`＝未照合と明記、キーなし・`null`＝不明。キーなし・`null` を `true` と同一視しない（`biblical_correspondence/` の `found / not_found / unavailable` と同じ考え方）
- `falsified` は照合済みの反証項目が1件以上ある時だけ。件数の閾値は持たないので、索引を増やしても照合済みの反証が増えない限り判定は動かない
- 不在（`survives`）を言う時だけ索引の最低件数（20）を要求する

`verified: true` は、人が原典で照合した項目にだけ付ける。AIの推論・記憶・要約を根拠に付けない。

## テスト

```shell
python -m pytest -q -o addopts="" research_os/tests
```

リポジトリの `pyproject.toml` の pytest 設定は `transformer_lens/` 向け（`--doctest-plus` 等）なので、`research_os/` だけを走らせる時は `-o addopts=""` を付ける。
