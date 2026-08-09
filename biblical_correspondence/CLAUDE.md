# CLAUDE.md — biblical_correspondence/

このディレクトリで作業する際のガイド。See the repo-root `CLAUDE.md` for how this fits alongside the vendored `transformer_lens/` library, which this file does not cover. `research_os/` の `textual_comparison` タスクはこのディレクトリの `correspondence/correspondence_index.json` を検索対象にする（`research_os/CLAUDE.md` 参照）。

コードコメント・docstring・READMEを含め、このディレクトリ配下は日本語で書く。

## What this is

独立した FastAPI アプリ（own `requirements.txt`、poetry プロジェクトの一部ではない）。Claude API を使ったチャット UI（`app.py`）と、ヘブライ語・ギリシャ語原典（Strong's番号）および相応辞典を検索する `lexicon_router` サブAPIを提供する日本語 PWA。

```shell
cd biblical_correspondence
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-api-key"
python app.py   # serves on localhost:8000
```

テスト実行：

```shell
cd biblical_correspondence && pytest tests/test_lexicon_health.py -v
```

外部データ（`morphhb`/`morphgnt`、`scripts/bootstrap_morph_data.sh` で別途クローン）が一切無い状態でも全テストが通るよう設計されている。

## 三状態規約（critical convention）

**この節は要約であり、規約の正はコードとテストにある。** 実装を変更した際にこの節が古くなっていたら、テストの方を書き換えて要約に合わせるのではなく、この節をコードに合わせて直すこと。

この三状態は次の2つの関数の契約であり、このディレクトリの全エンドポイントに一般化できる規約ではない：`verify_verse`（原語照合）と `lookup_correspondence`（相応索引検索）。

- `/api/lexicon/health` は別の契約を持つ——`morphhb`/`morphgnt` は `available`/`missing`、`verify_verse_status` は `operational`/`degraded` を返す（`TestHealthEndpoint` が固定）。
- `lookup_word`（Strong's 辞書引き）も別の契約——見つかればエントリの dict、無ければ `KeyError` を送出する（`TestLookupWord.test_unknown_id_raises_keyerror` が固定）。

これらを三状態規約に合わせて「直す」と、上記の固定テストと矛盾する。三状態は `verify_verse` と `lookup_correspondence` の2関数に限定して適用すること：

| status | 意味 |
|---|---|
| `found` | 照合済み、存在する |
| `not_found` | 照合済み、不在と確認された |
| `unavailable` | 照合していない — 元データ（`morphhb`/`morphgnt`）が未配置、または参照が索引に無い |

`unavailable` は `contains: null`（または同等の非 boolean 値）としてシリアライズされなければならない。`contains: false` にしてはならない——「照合できなかった」を「照合した結果、無かった」に潰すことは、コードベース内で **"Codex P1" regression** と呼ばれている既知の不具合クラス。

正の所在（実装 / 固定テスト）：

- `biblical_correspondence/lexicon/biblical_lexicon.py` — `verify_verse`, `lookup_word`
- `biblical_correspondence/correspondence/correspondence_lookup.py` — `lookup_correspondence`（モジュール docstring 自体に三状態の定義がある）
- `biblical_correspondence/tests/test_lexicon_health.py` — `TestVerseVerifyUnavailable` / `TestVerseVerifyBadRef` / `TestCorrespondenceLookup` / `TestHealthEndpoint` が、この規約を回帰的に固定している

このサブツリーの照合・検証系コードを触るときは、三状態の返り値の形を保ち、データ欠如による例外を静かに false negative へ変換しないこと。

`biblical_lexicon` モジュールは特に「外部アンカー」として存在する——原語に関する主張を、LLM の記憶による「それっぽさ」ではなく、`morphhb`/`morphgnt` の実テキスト照合で答えるため。`biblical_correspondence/lexicon/README.md` に、記憶に頼った結果 Strong's 番号の帰属を誤った実例（`Hos 4:1`）が記録されている。
