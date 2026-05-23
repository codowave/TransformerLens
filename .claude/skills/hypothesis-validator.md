# hypothesis-validator

**目的**: 仮説を `research/observations/` と `research/verified/` の実績データと照合し、
支持・反証・未確認のいずれかを判定する。

## 照合手順

1. 仮説の**検証可能な予測**を列挙（テストできない主張は除外）
2. 各予測に対し、既存エントリで支持/反証/関連なしを判定
3. 判定根拠となるエントリを具体的に引用
4. 総合判定を下す

## 判定基準

| 判定 | 条件 |
|------|------|
| SUPPORTED | 予測の>50%が実データで支持、反証なし |
| PARTIALLY_SUPPORTED | 支持あり、かつ反証あり |
| CONTRADICTED | 主要予測が実データと矛盾 |
| INSUFFICIENT_DATA | 関連する観察データが3件未満 |

## 出力形式

```
仮説: [仮説の要約]
判定: SUPPORTED | PARTIALLY_SUPPORTED | CONTRADICTED | INSUFFICIENT_DATA

検証可能な予測:
1. [予測1] → [支持/反証/未確認]: [根拠エントリ名]
2. [予測2] → ...

結論: [判定理由1文]
推奨次アクション: [観察すべきデータ or 移動先ディレクトリ]
```

## 使用例

```
/hypothesis-validator

仮説:
[仮説テキスト]

既存エントリ（参照用）:
[observations/ や verified/ の内容]
```
