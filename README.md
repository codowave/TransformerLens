# Biblical Correspondence Dictionary Vault

## 目的

このVaultは **biblical-correspondence-dictionary**（聖書的照合辞典）のための研究・記録用Obsidian Vaultです。  
聖書テキスト・原語（ヘブライ語・ギリシャ語）・スウェーデンボルグ解釈・フィールドノート・AI対話などの資料を蓄積し、
対応・接続関係を段階的に検証・昇格させることを目的とします。

---

## フォルダ構造

```
raw/                    # 未整理・一次資料
  scripture/            # 聖書本文（章ごとのファイル）
  strongs/              # ストロングス番号・原語語義ファイル
  swedenborg/           # スウェーデンボルグ著作からの抜粋
  field-notes/          # 現場観察・体験メモ（日付ファイル）
  ai-dialogues/         # AI対話ログ（参照用。verified 昇格根拠には不可）
  articles/             # 外部論文・記事
wiki/
  candidates/           # AI生成・未検証の接続候補
  verified/
    provisional/        # AI外部直接確認を1件以上通過した接続
    confirmed/          # 複数条件通過・再検証済みの接続
  concepts/             # 概念定義・用語集
  ai-observation/       # AI観察メモ（補助資料）
  queries/              # 調査・検索クエリのメモ
schema/
  Parallax.md           # 視差・多角的読みの補助スキーマ（スタブ）
  ingest-rules.md       # raw/ への取り込みルール
  adoption-gate.md      # 昇格条件の定義
  lint-rules.md         # 構造監査ルール
templates/
  candidates-template.md
  provisional-template.md
  confirmed-template.md
```

---

## 昇格フロー

```
raw/ に資料追加
    ↓
wiki/candidates/  ← AI生成・未検証の接続候補を置く場所
    ↓  【AI外部直接確認 1件以上が必須】
wiki/verified/provisional/  ← 直接確認を通過した接続
    ↓  【複数条件通過 + 再検証で矛盾なし】
wiki/verified/confirmed/    ← 確定接続
```

詳細な昇格条件は `schema/adoption-gate.md` を参照してください。

---

## テンプレートの使い方

| ステージ | 使用テンプレート |
|---|---|
| 新規候補追加 | `templates/candidates-template.md` |
| provisional 昇格時 | `templates/provisional-template.md` |
| confirmed 昇格時 | `templates/confirmed-template.md` |

---

## 接続理由の類型

以下の8類型を全テンプレート・lintで共通使用します：

1. **原語由来** — ヘブライ語・ギリシャ語の語義・語根から導いた接続
2. **本文文脈由来** — 聖書本文の文脈・構造から導いた接続
3. **現場経験由来** — 観察・体験・実証から導いた接続
4. **比喩・類似由来** — 類似・アナロジーから導いた接続
5. **語感・形状由来** — 音韻・形状・印象から導いた接続
6. **複数AI一致由来** — 複数のAIモデルが同意した接続（補助資料のみ）
7. **解釈者由来** — スウェーデンボルグ等の解釈者に基づく接続（補助資料のみ）
8. **AI対話由来** — AI対話ログから得た着想（補助資料のみ）

> **注意**: 類型 6・7・8 は補助資料であり、`verified/` 昇格の直接根拠にはなりません。

---

## First Run 自己点検チェックリスト

セットアップ後、以下の3項目を確認してください。

### 1. 配管確認
- [ ] すべてのフォルダが作成されているか
- [ ] README.md・schema 4ファイル・templates 3ファイルが存在するか
- [ ] `.gitkeep` により空フォルダが git 管理されているか

### 2. 門確認
- [ ] `schema/adoption-gate.md` に candidates / provisional / confirmed の昇格条件が明確に分かれているか
- [ ] **AI外部直接確認が provisional の必須条件**として明文化されているか
- [ ] AI同意・AI確信度が昇格根拠にならないことが明記されているか

### 3. 歪み確認
- [ ] `templates/provisional-template.md` に確認来歴欄が設けられているか
- [ ] `schema/lint-rules.md` に raw 参照なし候補の検出ルールがあるか
- [ ] lint では捕らえない判断（Swedenborg 発想を scripture 参照で偽装する件等）が人間の裁定に残ると明記されているか

---

*このVaultは Obsidian で開いてご使用ください。Vaultルートはこのファイルと同じディレクトリです。*
