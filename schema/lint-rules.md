# Lint ルール（構造監査）

このファイルは Vault 内のファイル構造を監査するためのルールを定義します。  
**Lint は構造の問題を検出するものであり、接続の意味・真偽の判定は行いません。**

意味の判定は常に人間の裁定に委ねます。

---

## 検出レベル

| レベル | 意味 |
|---|---|
| 🔴 要注意 | 採択判断に重大な影響を与える構造的問題。優先的に対処する。 |
| 🟡 要確認 | 情報が不完全な可能性がある。確認を推奨する。 |

---

## Candidates ファイルのルール

### C-01 🔴 要注意：複数AI一致由来のみ
**条件**: 接続理由の類型が「複数AI一致由来」のみで、他の類型が一切ない。  
**検出**: `接続理由の類型` 欄に「複数AI一致由来」のみが記載されている。  
**理由**: 複数AIの同意は独立した検証にならない。他の根拠が存在しないことを明示する。

### C-02 🟡 要確認：raw 参照なし
**条件**: `raw/` 以下のファイルへの参照が一切ない。  
**検出**: `根拠になった本文・語・経験` 欄または `なぜこの接続を生成したか` 欄に `raw/` パスが含まれていない。  
**理由**: raw 参照なしは検証の起点が不明であることを示す。

### C-03 🔴 要注意：解釈者由来・AI対話由来で raw 参照が空
**条件**: 接続理由が「解釈者由来」または「AI対話由来」であるが、対応する raw 参照パスが空。  
**検出**: 類型に「解釈者由来」「AI対話由来」が含まれるが、`raw/swedenborg/` または `raw/ai-dialogues/` へのパスが記載されていない。  
**理由**: 解釈者・AI対話由来は補助資料としても、参照元が不明では追跡不能になる。

### C-04 🟡 要確認：ラベルと raw 参照パスの不整合
**条件**: 接続理由のラベルが示す出典と、実際に参照されている raw パスが一致していない。  
**検出パターン例**:
- 「本文文脈由来」なのに `raw/scripture/` への参照がない → 警告
- 「原語由来」なのに `raw/strongs/` への参照がない → 警告
- 「現場経験由来」なのに `raw/field-notes/` への参照がない → 警告

> **lint では捕らえない判断について**:  
> スウェーデンボルグ的発想を `raw/scripture/` 参照で偽装するケース（「本文文脈由来」と表示しながら実質は解釈者由来の推論である場合）は、  
> ファイル構造からは自動検出できません。この判断は人間の裁定に委ねます。

### C-05 🟡 要確認：本文文脈由来と解釈者由来の混在
**条件**: `connection-source` に「本文文脈由来」が含まれ、かつ `raw/swedenborg/` 等の解釈者資料への参照も含まれている。  
**検出**: frontmatter `connection-source` に「本文文脈由来」があり、本文参照欄に `raw/swedenborg/`（または `raw/articles/` 内の解釈者文献）のパスが存在する。  
**理由**: 本文由来と解釈者由来の混在は正当な場合もあるが、解釈者推論を本文由来として誤分類するリスクがある。人間による明示的な確認を促す。  
**推奨対応**: `claim-type: mixed` に変更し、それぞれの根拠を分けて記述する。

---

## Connection-Source × Claim-Type 整合性ルール

`connection-source` と `claim-type` は**直交軸**です。発生源が何であるかは主張型を一意に決定しません。

- `connection-source: [解釈者由来]` のとき `claim-type` は `hypothesis` にも `interpretation` にも `metaphor` にもなりえます。
- `connection-source: [本文文脈由来]` のとき `claim-type: metaphor` は正当です。
- `connection-source: [原語由来]` のとき `claim-type: hypothesis` は正当です。

lint が検出するのは「この組み合わせは**確実に問題**」という狭い禁止リストのみです。  
密なマッピング（○○由来なら○○型であるべき）は lint の責務外であり、人間の裁定に委ねます。

### M-01 🔴 要注意：独立検証不能な発生源のみで fact 主張
**条件**: `claim-type: fact` かつ `connection-source` が以下のいずれか**のみ**で構成される：
- `[解釈者由来]` のみ
- `[AI対話由来]` のみ
- `[複数AI一致由来]` のみ
- `[比喩・類似由来]` のみ
- `[語感・形状由来]` のみ

**検出**: `claim-type` が `fact` かつ `connection-source` の全要素が上記5種のいずれかに属し、それ以外の類型（原語由来・本文文脈由来・現場経験由来）が1つも含まれない。  
**理由**: これら5類型は `adoption-gate.md` に明記された採択禁止理由に該当する発生源であり、単独では「事実」主張を支えられない。他の類型が1つでも加わっている場合は警告しない。  
**許可される組み合わせの例（変更不要）**:
- `connection-source: [原語由来]` / `claim-type: hypothesis` → 許可
- `connection-source: [本文文脈由来]` / `claim-type: metaphor` → 許可
- `connection-source: [解釈者由来]` / `claim-type: hypothesis` → 許可
- `connection-source: [現場経験由来]` / `claim-type: application` → 許可
- `connection-source: [解釈者由来, 本文文脈由来]` / `claim-type: fact` → 許可（原語等との混在があるため）

### V-01 🔴 要注意：connection-source に claim-type 語彙が混入
**条件**: `connection-source` に `claim-type` の値（`fact` / `hypothesis` / `metaphor` / `interpretation` / `application` / `mixed`）が含まれている。  
**検出**: frontmatter の `connection-source` 配列の要素が上記英語値のいずれかと一致する。  
**理由**: `connection-source` の有効値は接続由来8類型（日本語）のみ。`interpretation` は `claim-type` の値であり `connection-source` には使わない。
  典型的な混入パターン:
  - `connection-source: interpretation` → 誤り。`connection-source: [解釈者由来]` かつ `claim-type: interpretation` が正しい
  - `connection-source: hypothesis` → 誤り。`claim-type: hypothesis` が正しい場所
**有効な connection-source 値**:
  `原語由来` / `本文文脈由来` / `現場経験由来` / `比喩・類似由来` / `語感・形状由来` / `複数AI一致由来` / `解釈者由来` / `AI対話由来`

### V-02 🔴 要注意：connection-source が配列でない
**条件**: `connection-source` が配列ではなくスカラー値（文字列・数値等）で記述されている。  
**検出**: frontmatter の `connection-source` が `[]` または `[...]` 形式でない。  
**例**:
  - `connection-source: 解釈者由来` → 誤り（スカラー）
  - `connection-source: [解釈者由来]` → 正しい（配列）

---

## Raw 参照形式のルール

### R-01 有効な raw/scripture/ 参照形式
`raw/scripture/` への参照は以下のいずれかの形式を有効とする：
- 章ファイル参照: `raw/scripture/{書名略語}/{章番号3桁}.md`  
  例: `raw/scripture/genesis/004.md`
- 章ファイル＋ヘッダーリンク（節参照）: `raw/scripture/{書名略語}/{章番号3桁}.md#{節識別子}`  
  例: `raw/scripture/genesis/004.md#1`

旧形式の節単位ファイルパス（例: `genesis/004-001.md`）は**無効**として警告する。

---

## Provisional / Confirmed ファイルのルール

### P-01 🔴 要注意：確認来歴欄が存在しない
**条件**: `wiki/verified/provisional/` または `wiki/verified/confirmed/` のファイルに「確認来歴」セクションがない。  
**検出**: ファイルに `確認来歴` という見出しが存在しない。  
**理由**: 確認来歴は provisional 以上の必須要件。欄が存在しない場合は昇格条件を満たしていない。

### P-02 🔴 要注意：確認来歴欄が空
**条件**: 「確認来歴」セクションはあるが、確認者・確認日時・確認種別が記入されていない。  
**検出**: `確認来歴` 見出し以降の内容が空または「未記入」のみ。  
**理由**: 空の確認来歴は AI 外部直接確認が行われていないことを示す。

### P-03 🔴 要注意（confirmed のみ）：再検証ログが存在しない
**条件**: `wiki/verified/confirmed/` のファイルに「再検証ログ」セクションがない、または空。  
**検出**: `再検証ログ` 見出しが存在しない、または内容が空。  
**理由**: confirmed への昇格には再検証の記録が必須。

---

## 適用範囲と限界

### Lint が検出できること
- テンプレート欄の欠如・空欄
- raw 参照パスの有無
- ラベルと参照パスの形式的な不整合

### Lint が検出できないこと（人間の裁定が必要）
- raw 参照の内容が実際に接続を支持しているかどうか
- 「本文文脈由来」と称しながら実質的に解釈者推論を使用しているケース
- 確認来歴の記録が実際の確認を反映しているかどうか
- 接続の意味的な正確性・深さ・妥当性

**Lint は構造の番人であり、意味の審判ではありません。**

---

*最終更新: セットアップ初期*
