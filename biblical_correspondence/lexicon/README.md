# biblical_lexicon — 原語照合レイヤー

## 第一作業原理

> **露頭の同定は、まず原語の確認から始まる。**

翻訳（英語・日本語）の語の「雰囲気」で原語を推測してはならない。
ヘブライ語本文の yada（H3045）が使われているかどうかは、日本語訳の「知る」という語の存在ではなく、
ヘブライ語本文の yada そのものの出現で判定する。

このモジュールは Claude の応答の**外部アンカー**として機能する。
本文照合済みの情報を Claude へのプロンプトに注入し、記憶による原語の誤帰属を構造的に防ぐ。

---

## ファイル構成

```
lexicon/
├── __init__.py
├── biblical_lexicon.py    # コアモジュール（本文照合・Strong's照会）
├── lexicon_router.py      # FastAPI ルーター
├── build_first_node.py    # 第一ノード (yada) の検証スクリプト
├── first_node_yada.json   # 本文照合済み第一ノードデータ
├── strongs_hebrew.json    # Strong's ヘブライ語辞書（8674エントリ）
├── strongs_greek.json     # Strong's ギリシャ語辞書（5523エントリ）
└── README.md
```

外部データ（リポジトリには含まない、`data/` にクローン）:
```
data/
├── morphhb/               # openscriptures/morphhb (Hebrew, OSIS XML, CC BY 4.0)
├── sblgnt/                # morphgnt/sblgnt (Greek text)
└── morphgnt/              # morphgnt/morphgnt (Greek morphology with Strong's)
```

---

## セットアップ

```bash
# 外部データのクローン
cd /path/to/biblical_correspondence
mkdir -p data && cd data
git clone --depth 1 https://github.com/openscriptures/morphhb.git
git clone --depth 1 https://github.com/morphgnt/sblgnt.git
git clone --depth 1 https://github.com/morphgnt/morphgnt.git
cd ..

# 第一ノード検証
python lexicon/build_first_node.py
```

環境変数でパスを上書き可能:
```bash
export MORPHHB_PATH=/custom/path/to/morphhb/wlc
export MORPHGNT_PATH=/custom/path/to/morphgnt
export SBLGNT_PATH=/custom/path/to/sblgnt
```

---

## API エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/lexicon/verse/{ref}` | 節の完全な原語解析 |
| GET | `/api/lexicon/verify/{ref}/{strongs}` | 節に Strong's が実在するか検証 |
| GET | `/api/lexicon/search/{strongs}` | 全出現箇所（H番号のみ） |
| GET | `/api/lexicon/word/{strongs}` | Strong's 辞書エントリ |

### サニティチェック

```bash
# Gen 3:5 に yada (H3045) が存在する → true
curl localhost:8000/api/lexicon/verify/Gen.3.5/H3045

# ヤコブ改名 (Gen 32:29) に yada は存在しない → false（重要）
curl localhost:8000/api/lexicon/verify/Gen.32.29/H3045
```

---

## 発見事項（本文照合で判明）

### Gen 4:1 — yada と qanah の隣接

アダムが エバを `yada`（H3045）した直後、エバが産んだ子を `qanah`（H7069, 得た・創造した）と呼ぶ。
人類史の最初の親子誕生の瞬間に「知る」と「得る」が本文上で隣接している。
連想ベースの解析では絶対に見つからない。本文を実際に見るとしか見つからない相応。

### Hos 4:1 — H3045 と H1847 の区別

別セッションの Claude が記憶で「Hos 4:1 = H3045 の欠如」と帰属したが、
本文照合で **H3045 は無く、中心語は H1847 (da'ath, 名詞化された知識)** であることが判明。

ホセアの嘆きは二重構造——動詞的な `yada`（通過して知る）も、
名詞化された `da'ath`（情報として持てる知識）も、**両方とも無い**。

**第一作業原理が Claude 自身の出力に対してガードをかけた最初の事例。**

---

## ライセンス

→ `ATTRIBUTIONS.md` 参照
