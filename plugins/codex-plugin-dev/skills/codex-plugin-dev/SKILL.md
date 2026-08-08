---
description: OpenAI Codex CLI の拡張機構（skills、非推奨のcustom prompts、config.tomlのmcp_servers、hooks）を作成・更新・修復・監査する。「Codexのスキルを作って」「Codex用のプラグインを作って」「~/.codex を監査して」「Codexのカスタムプロンプトを直して」「Codex CLIのMCPサーバ設定を直して」と頼まれたら使う。Claude Code自身のプラグイン（plugin.json/marketplace.json）を対象にする場合はこのスキルではなく plugin-audit を使う。
---

# Codex Plugin Dev

OpenAI Codex CLI の拡張機構を対象に、作成・更新・修復・監査を行う。

## 前提: Codexには統一された「プラグイン」形式がない

Claude Codeの `plugin.json` + `marketplace.json` のような、1つのマニフェストにskills・commands・hooks・MCPをまとめて配布する仕組みはCodexには存在しない（2026年8月時点でこのスキルの著者が確認した範囲）。代わりに4つの独立した機構がある:

| 機構 | 場所 | 状態 |
|---|---|---|
| Skills | `~/.codex/skills/<name>/SKILL.md`（個人）/ `.codex/skills/<name>/SKILL.md`（プロジェクト）。frontmatterは `name` + `description` | 現行・推奨 |
| Custom prompts | `~/.codex/prompts/*.md`（トップレベルのみ、サブディレクトリは無視される） | **非推奨**（OpenAIはskillsへの移行を推奨） |
| MCP servers | `~/.codex/config.toml` の `[mcp_servers.<name>]`（stdioは`command`/`args`/`env`、HTTPは`url`） | 現行 |
| Hooks | `hooks.json` または `config.toml` の `[hooks]` インライン | 現行 |

## 確度について（重要）

このスキルの著者は developers.openai.com/codex（一次情報）に到達できないネットワーク環境で書いた。skills と custom prompts の仕様は複数の独立した二次情報源で一致しており確度が高い。**mcp_servers と hooks の細部（正確なキー名・イベント名一覧・優先順位規則）は未検証。** `${CLAUDE_PLUGIN_ROOT}/scripts/audit_codex.py` はこの区別を severity で表現する:

- `ERROR` / `WARN`: skills・prompts・JSON/TOML構文などの確度が高い問題
- `CHECK`: mcp_servers・hooksまわりの、二次情報に基づく「疑わしいが未確認」の指摘。ユーザーに提示する際は必ず「未検証」であることを伝え、修正を強制しない

## 監査 (audit)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/audit_codex.py" [~/.codex] [.codex] [--json]
```

複数のルート（個人スコープ・プロジェクトスコープ)を同時に渡すと、スコープ間の名前重複も検出する。結果を報告する際は `CHECK` を `ERROR`/`WARN` と同列に並べず、必ず「未検証」ラベル付きで分けて提示する。

## 作成 (create)

新しいCodex skillを作る場合:

1. `<root>/skills/<name>/SKILL.md` を作成し、frontmatterに `name` と `description` を必ず入れる（この2つは確度の高い必須フィールド）。
2. 補助ファイルが要るなら `scripts/`・`references/`・`assets/` をskillディレクトリ配下に置く。
3. 作成後、必ず `audit_codex.py` を実行して description欠落・ダングリング参照がないか確認する。

MCPサーバやhooksを新規に追加する場合は、それがconfig.tomlのどのキーになるかについてこのスキルの知識が未検証であることをユーザーに明示し、可能なら `/hooks`（Codex CLI内のコマンド、設定を確認・信頼するためのUI）で実際にCodexに認識されているか確認するよう促す。断定的に「これが正しいスキーマです」とは言わない。

## 更新・修復 (update / repair)

1. まず `audit_codex.py` を実行し、現状の issue 一覧を取得する。
2. `ERROR`/`WARN`（skills・prompts・構文エラー）は積極的に自動修正してよい: description追加、name不一致の解消、ダングリング参照先の作成またはリンク修正、非推奨prompts/のskills/への移行提案など。
3. `CHECK`（mcp_servers・hooks）は自動修正で押し切らない。何が疑わしいか・なぜ未検証なのかをユーザーに説明し、直すかどうかの判断を委ねる。
4. 修正後は再度 `audit_codex.py` を実行し、直った差分を報告する。
