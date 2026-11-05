# plugin-audit

Claude Codeプラグイン（単体、またはマーケットプレイス全体）を実体から棚卸しし、
構造的な妥当性と品質を検証するプラグイン。

## インストール

```
/plugin marketplace add ./
/plugin install plugin-audit@transformerlens-plugins
```

## 使い方

`plugin-audit:plugin-audit` スキルが以下のような依頼で自動的に起動する:

- 「プラグインを監査して」
- 「このマーケットプレイスをチェックして」
- 「plugin.jsonが正しいか確認して」

直接スクリプトを実行することもできる:

```bash
python3 scripts/audit_plugin.py <marketplaceルート または プラグインディレクトリ> [--json]
```

## 検証内容

- `plugin.json` / `hooks/hooks.json` / `.mcp.json` / `.lsp.json` のJSON構文
- `plugin.json` の必須フィールド、kebab-case命名、未知フィールド
- `.claude-plugin/` 直下にコンポーネントディレクトリが紛れ込んでいないか
- スキル・コマンド・エージェントの必須frontmatterフィールド欠落
- 同名のスキル/コマンド/エージェントによる名前空間の衝突
- エージェントで `hooks`/`mcpServers`/`permissionMode` を指定してしまっている場合の検出
  （プラグイン同梱エージェントでは非対応だが、`claude plugin validate` は警告なく無視する）
- `references/`・`scripts/`・`assets/` への壊れた相対参照

`claude plugin validate` を置き換えるものではなく、それが検出しないクロスコンポーネントの
問題（名前衝突・壊れた参照・エージェントの黙って無視されるフィールド）を補うツール。
