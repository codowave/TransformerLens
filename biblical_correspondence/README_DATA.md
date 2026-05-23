# データ配置ガイド

## 重要: データなし ≠ 故障

`/api/lexicon/health` が `"morphhb": {"status": "missing"}` を返しても、
アプリケーションは**正常に動作している**。

データが未配置の場合、原語照合層は `"unavailable"` を返す。
これは「照合できない」状態であり、「語が存在しない」という主張ではない。

```json
{
  "status": "unavailable",
  "contains": null,
  "reason": "morphhb_not_available"
}
```

`contains: null` （`false` ではない）であることに注意。
`false` は「照合済みの不在」を意味する（Codex P1 原則）。

---

## 三状態の意味

| status | contains | 意味 |
|---|---|---|
| `found` | `true` | 語が当該節に存在（morphhb で照合済み） |
| `not_found` | `false` | 語が当該節に不在（morphhb で照合済み） |
| `unavailable` | `null` | morphhb 未配置 — 存在/不在を断定できない |

**`unavailable` を `not_found` と混同してはならない。**
「調べられなかった」と「調べた結果なかった」は異なる事実。

---

## データ配置手順（任意）

原語照合を有効にする場合のみ実行する。

```bash
cd biblical_correspondence
bash scripts/bootstrap_morph_data.sh
```

スクリプトは以下を行う:
1. `openscriptures/morphhb` を `data/morphhb/wlc/` にスパースクローン
2. `morphgnt/morphgnt` を `data/morphgnt/` にクローン

完了後、ヘルスチェックで確認:

```bash
curl http://localhost:8000/api/lexicon/health
```

期待される出力（データ配置後）:

```json
{
  "morphhb": {"status": "available", "xml_files": 39},
  "morphgnt": {"status": "available", "txt_files": 27},
  "verify_verse_status": "operational",
  "verify_verse_detail": "Gen.3.5/H3045 → found ✓"
}
```

---

## ライセンス

| データ | ライセンス |
|---|---|
| morphhb (openscriptures/morphhb) | CC BY 4.0 |
| morphgnt (morphgnt/morphgnt) | CC BY-SA 3.0 |
| Strong's dictionary | Public Domain |

これらのデータはリポジトリに含まれていない。
`bootstrap_morph_data.sh` が各リポジトリから取得する。

---

## データなしでの動作確認

```bash
cd biblical_correspondence
pytest tests/test_lexicon_health.py -v
```

全テストはデータ未配置の状態で通過するよう設計されている。
`unavailable` が正しく返ることを固定している。
