# AI Research OS — Claude Codeへの運用指示

## このリポジトリの構造

```
research/               ← 研究データ本体（版管理の核心。削除・.gitignore禁止）
research_os/            ← Python CLIパッケージ
biblical_correspondence/ ← Swedenborg相応の辞典アプリ（改変しない）
transformer_lens/       ← 機械的解釈可能性ライブラリ（改変しない）
.claude/skills/         ← 再利用可能なプロンプトスキル
```

---

## research/ ディレクトリの意味とルール

| ディレクトリ | 用途 | 移動条件 |
|-------------|------|---------|
| `inbox/` | 未分類の投入口 | `classify` 実行後に自動移動 |
| `hypotheses/` | 検証前の仮説 | `verified/` へは人間承認後のみ |
| `observations/` | 実験・観察ログ | 変更不要 |
| `verified/` | 検証済み知見 | `contradictions/` へ降格可 |
| `contradictions/` | 矛盾検出ログ | 自動生成 + 人間確認 |
| `ai-comparisons/` | 複数AI応答比較 | 変更不要 |
| `phase-transitions/` | 思考の転換点ログ | 人間が手動で記録 |
| `glossary/` | 用語辞典（自動生成） | `glossary` コマンドで更新 |
| `timeline/` | 時系列整合ログ | `timeline` コマンドで更新 |

---

## front-matter スキーマ

各 `.md` ファイルの冒頭に付与する YAML:

```yaml
---
id: hyp-001               # 自動付番
date: 2026-05-23          # 作成日
source: human             # human | claude | gpt | gemini | grok
status: hypothesis        # hypothesis | observation | verified | contradicted
tags: [tag1, tag2]        # 関連タグ
summary: 30文字以内の要約   # 自動生成
related: [hyp-002]        # 関連エントリ（任意）
---
```

---

## CLIコマンド

```bash
# 必須環境変数
export ANTHROPIC_API_KEY="..."

# 分類（inbox → 適切なディレクトリへ）
python -m research_os classify research/inbox/note.md
python -m research_os classify research/inbox/note.md --source gpt
python -m research_os classify research/inbox/note.md --dry-run  # 確認のみ

# 監査（AI生成コンテンツの品質検査）
python -m research_os audit research/hypotheses/hyp-001.md --source claude
python -m research_os audit /path/to/gpt_output.md --out research/contradictions/audit.md

# 矛盾検出（ディレクトリ横断）
python -m research_os contradict                          # research/全体
python -m research_os contradict research/hypotheses/     # 指定ディレクトリのみ
python -m research_os contradict --out report.md

# AI比較
python -m research_os compare research/ai-comparisons/q001.md

# タイムライン生成
python -m research_os timeline

# 用語辞典更新
python -m research_os glossary

# 仮説検証（--dry-run は送信なし・ペイロード表示。APIキー投入前に必ず実行）
python -m research_os verify research/hypotheses/hyp-001.md --task mechanism_mapping --dry-run
python -m research_os verify research/hypotheses/hyp-001.md --task mechanism_mapping \
  --output research/observations/obs-002.md
```

## verify コマンドの前提点検ルール

`verify --task mechanism_mapping` を実行する前に必ず `--dry-run` を確認すること。

確認順序:
1. `api_call: NOT SENT` の表示（送信分岐の確認）
2. `payload_preview.user_message` に仮説本文が全文入っているか
3. `payload_preview.implementer_declared_premises` — **前提点検の主体はここ**
4. `payload_preview.premise_audit_note` を読む

### `what_llm_reports_as_assumed` の限界

出力に含まれる `what_llm_reports_as_assumed` フィールドは、
LLMが言語化できた範囲の自己申告にすぎない。
暗黙に通過した前提は定義上このフィールドに乗らない（言語化できれば暗黙でない）。

**前提の真の点検は `implementer_declared_premises` とプロンプト本文の外部読解が主であり、
`what_llm_reports_as_assumed` は補助情報として読む。**
このフィールドが返ってきた事実を「前提が点検された証明」として使わない。

### verify 実行後の読解順序

```
1. schema が崩れていないか（component_assessments / axis_assessments の存在）
2. adoption_status が not_adopted のままか
3. correspondence_status に no_correspondence / structural_mismatch が返っているか
4. what_llm_reports_as_assumed が自己申告として隔離されているか
5. implementer_declared_premises と矛盾していないか
6. failure_points / unresolved_constraints が残っているか
7. hyp-001 本文にない主張を生成していないか
```

### 合格条件（全て満たすこと）

- schema が保たれている
- 自動採択していない（`adoption_status: not_adopted`）
- 「対応なし」を表現できている（`no_correspondence` / `structural_mismatch` が出せる）
- `what_llm_reports_as_assumed` を証明扱いしていない
- 未解決制約を残している（`failure_points` が消えていない）
- `hyp-001` 外の主張を足していない

### 不合格条件（一つでも該当したら採用不可）

- mapping を前提にしている（`correspondence_status` が全て positive）
- `adoption_status` が `adopted` / `promoted` になっている
- `unresolved_constraints` / `failure_points` が消えている
- DLW・Swedenborg 側に未確認の主張を追加している
- `what_llm_reports_as_assumed` を判定根拠として使っている

---

## スキルの使い方

`.claude/skills/` 内のスキルは Claude Code 内で以下のように呼び出す:

```
/structural-audit
[監査対象テキスト]

/contradiction-finder
[比較するノート群]

/research-compressor
[圧縮対象テキスト]

/hypothesis-validator
[仮説テキスト]
[参照データ]

/anti-sycophancy
[AI応答テキスト]
```

---

## 自律研究ループの安全境界

自動化ループを実行する場合、以下を**必ず**守ること:

1. **最大反復数**: 10回まで
2. **差分審査**: 各サイクル後に `git diff` を確認
3. **human approval gate**: `verified/` への昇格は人間承認後のみ
4. **タイムアウト**: 1サイクル最大60秒
5. **rollback**: `git checkout` で即時復元可能な状態を保つ

---

## AI比較ファイルの形式

`research/ai-comparisons/` 内のファイルは以下の形式:

```markdown
---
question: 比較する質問文
date: 2026-05-23
---

## Claude
[Claudeの応答]

## GPT
[GPT-4の応答]

## Gemini
[Geminiの応答]

## Grok
[Grokの応答]
```

---

## 禁止事項

- `research/` を `.gitignore` に追加しない
- `biblical_correspondence/` と `transformer_lens/` のコードを改変しない
- `verified/` への自動昇格（human approval gate を必ず通す）
- 監査結果の「改善」を求められていない限り提案しない
