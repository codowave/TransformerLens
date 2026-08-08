# codex-plugin-dev

OpenAI Codex CLI の拡張機構（skills、非推奨のcustom prompts、`config.toml` の
`mcp_servers`、hooks）を作成・更新・修復・監査するプラグイン。

## インストール

```
/plugin marketplace add ./
/plugin install codex-plugin-dev@transformerlens-plugins
```

## 確度についての注意

Codexには Claude Code の `plugin.json`/`marketplace.json` に相当する統一
プラグイン形式は存在しない。このプラグインは4つの独立した機構を個別に扱う:

- **Skills**・**Custom prompts（非推奨）**: 複数の独立した二次情報源で
  一致しており確度が高い。
- **MCP servers**・**Hooks**: developers.openai.com/codex（一次情報）に
  到達できない環境で書かれたため、細部は未検証。`audit_codex.py` はこれらを
  `CHECK` severity として `ERROR`/`WARN` と区別する。

## 使い方

```bash
python3 scripts/audit_codex.py [~/.codex] [.codex] [--json]
```

複数ルートを渡すとスコープ間の名前重複も検出する。詳細は
`skills/codex-plugin-dev/SKILL.md` を参照。
