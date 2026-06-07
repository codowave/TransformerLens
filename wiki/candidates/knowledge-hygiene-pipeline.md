---
stage: candidates
created: 2026-06-07
fact-status: candidate
claim-type: hypothesis
connection-source: [本文文脈由来]
connection-type: []
promotion:
  embodied_pass: null
  paper_checks:
    - lint論理一貫性（M-01/C-03/V-01 等のルールが互いに矛盾しないこと）
    - テンプレート完全性（3ステージの必須欄が過不足なく定義されていること）
    - 昇格条件の明文化（adoption-gate.md の3ステージが明確に分かれていること）
    - claim-type × connection-source の直交性が schema に反映されていること
    - lint-rules が密マッピングでなく疎な禁止リストになっていること
---

# 候補: Knowledge Hygiene Pipeline

> **ステージ**: `wiki/candidates/` — 未検証の方法論候補

> [!WARNING] 昇格ブロック
> `promotion.embodied_pass: null` の間は provisional 以上へ昇格しない。
> paper_checks の通過は必要条件だが十分条件ではない。

> [!NOTE] なぜ embodied 不足に気づきにくいか
> このエントリは yada/qanah のような原語・本文接続ではなく**方法論候補**である。
> 方法論は紙上での論理一貫性を示すことが容易なため、「実運用での摩擦」が未確認のまま
> 昇格条件を通過しているように見えやすい。他案件への適用実績がないまま confirmed に
> 昇格することが最大のリスク。

---

## 接続候補

**A**: Knowledge Hygiene Pipeline（本 Vault の運用方法論）  
**B**: biblical-correspondence-dictionary の長期的信頼性  
**接続の要旨**: このパイプライン（candidates → provisional → confirmed の3ステージ昇格、
lint_vault.py による構造監査、claim-type × connection-source の直交管理）が、
聖書的照合辞典の接続品質を長期的に保つ方法論として機能するという仮説。

---

## 根拠になった本文・語・経験

- `schema/adoption-gate.md` → 3ステージ昇格条件の定義
- `schema/lint-rules.md` → 構造監査ルールの定義
- `templates/candidates-template.md` → 接続候補の記録形式
- `templates/provisional-template.md` → 確認来歴の記録形式
- `templates/confirmed-template.md` → 再検証ログの記録形式
- `lint_vault.py` → 実装済みの構造チェッカー
- `tests/test_lint_vault.py` → テスト8件（A–H）による挙動確認

---

## なぜこの接続を生成したか

| 類型 | 該当 | raw/ 参照パス |
|---|---|---|
| 原語由来 | ☐ | |
| 本文文脈由来 | ☑ | （schema/ 以下の定義ファイル群） |
| 現場経験由来 | ☐ | （実運用前のため未記入） |
| 比喩・類似由来 | ☐ | |
| 語感・形状由来 | ☐ | |
| 複数AI一致由来 | ☐ | （補助資料のみ） |
| 解釈者由来 | ☐ | （補助資料のみ） |
| AI対話由来 | ☐ | （補助資料のみ） |

---

## 主張の種類（claim-type）

- **理由**: このパイプラインが長期的に機能するかどうかは、実運用を経なければ検証できない。
  設計上の論理一貫性は確認可能だが、「現場摩擦の少なさ」「他案件への適用可能性」は
  まだ未確認。現時点では `hypothesis` とする。

---

## paper_checks（紙上で確認できる項目）

以下は資料・コード・テストを読むことで確認できる。`embodied_pass` とは独立。

- [ ] lint-rules.md のルールが互いに矛盾していないこと
- [ ] adoption-gate.md の3ステージ昇格条件が明確に分かれていること
- [ ] claim-type × connection-source の直交性が schema に反映されていること
- [ ] テスト8件（A–H）が設計意図と一致していること
- [ ] M-01 が密マッピングでなく疎な禁止リストになっていること

---

## embodied_pass の条件（現在: null）

以下のいずれかの実績が記録されるまで `embodied_pass: null` のまま昇格しない:

- **他案件適用**: yada/qanah 以外の接続候補を2件以上このパイプラインで処理し、
  摩擦・欠落・フォーマット崩れが記録されていること
- **provisional 実昇格**: candidates → provisional の実昇格を1件以上完了していること
  （AI外部直接確認を含む）
- **lint 実稼働**: 実ノートに対して lint_vault.py が正しく鳴り・正しく黙ったことを
  確認できていること（テスト標本 D–H のような「良いノートを落とさない」確認を含む）

`embodied_pass` が埋まった時点で `raw/field-notes/` にその記録を作成し、
provisional テンプレートに転記する。

---

## 採択禁止理由に該当する点

- [x] 比喩の美しさ・一貫性・深さ感のみを根拠にしていないか → **注意**: パイプラインの「エレガントさ」や「整合感」は採択根拠にできない。
- [ ] 複数AIの同意のみを根拠にしていないか
- [ ] AIの確信度のみを根拠にしていないか
- [ ] 解釈者由来のみを根拠にしていないか
- [ ] AI対話ログのみを根拠にしていないか

**該当する禁止根拠**: 設計の美しさ・論理的一貫性は `paper_checks` の対象であり、
`embodied_pass` の代替にはならない。

---

## 次の検証手順

1. `paper_checks` の5項目を自分で通読し、チェックを埋める
2. 実ノート（yada/qanah 以外）を2件このパイプラインで処理する
3. 摩擦・欠落・フォーマット崩れを `raw/field-notes/` に記録する
4. provisional 実昇格を1件完了する
5. `embodied_pass` を埋め、provisional テンプレートに確認来歴を転記する

---

*このファイルは `templates/candidates-template.md` を参考に作成されました。*
