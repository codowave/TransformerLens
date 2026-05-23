"""
lexicon_router.py — 原語照合 FastAPI ルーター

エンドポイント:
  GET /api/lexicon/health               データ配置状態のヘルスチェック
  GET /api/lexicon/verse/{ref}          節の完全な原語解析
  GET /api/lexicon/verify/{ref}/{strongs}  節にStrong'sが実在するか検証
  GET /api/lexicon/search/{strongs}     全出現箇所（Hナンバーのみ）
  GET /api/lexicon/word/{strongs}       Strong's辞書エントリ
"""

import json

from fastapi import APIRouter, HTTPException
from .biblical_lexicon import (
    lookup_verse,
    verify_verse,
    search_by_strongs,
    lookup_word,
    MORPHHB_PATH,
    MORPHGNT_PATH,
    STRONGS_HEB,
    STRONGS_GRK,
)

router = APIRouter(tags=["lexicon"])


@router.get("/health")
async def get_health():
    """データ配置状態を返す。

    データが未配置でも 200 を返す — unavailable は故障ではなく「データ未配置」の状態。
    呼び出し元は status フィールドで "operational" / "degraded" を判断すること。

    verify_verse_status:
      operational — morphhb が存在し、サニティチェック（Gen.3.5/H3045）が found を返す
      degraded    — morphhb 未配置（unavailable を返す正常動作）
    """
    from pathlib import Path

    # morphhb: wlc/ 配下に .xml ファイルが1つ以上あれば available
    morphhb_xml_count = len(list(MORPHHB_PATH.glob("*.xml"))) if MORPHHB_PATH.exists() else 0
    morphhb_status = "available" if morphhb_xml_count > 0 else "missing"

    # morphgnt: .txt ファイルが1つ以上あれば available
    morphgnt_txt_count = len(list(MORPHGNT_PATH.glob("*.txt"))) if MORPHGNT_PATH.exists() else 0
    morphgnt_status = "available" if morphgnt_txt_count > 0 else "missing"

    # correspondence_index のエントリ数
    corr_index_path = Path(__file__).parent.parent / "correspondence" / "correspondence_index.json"
    corr_entry_count = 0
    corr_index_error: str | None = None
    if corr_index_path.exists():
        try:
            with open(corr_index_path, encoding="utf-8") as f:
                corr_entry_count = len(json.load(f).get("entries", []))
        except json.JSONDecodeError as exc:
            corr_index_error = f"JSON parse error: {exc}"
            log.error("correspondence_index.json parse failed: %s", exc)
        except OSError as exc:
            corr_index_error = f"file read error: {exc}"
            log.error("correspondence_index.json read failed: %s", exc)

    # verify_verse サニティチェック（データがある場合のみ意味を持つ）
    verify_status = "degraded"
    verify_detail = "morphhb missing — verify_verse returns unavailable (expected behavior)"
    if morphhb_status == "available":
        probe = verify_verse("Gen.3.5", "H3045")
        if probe.get("status") == "found":
            verify_status = "operational"
            verify_detail = "Gen.3.5/H3045 → found ✓"
        else:
            verify_status = "degraded"
            verify_detail = f"Gen.3.5/H3045 returned {probe.get('status')!r} (expected 'found')"

    return {
        "morphhb": {
            "status": morphhb_status,
            "path": str(MORPHHB_PATH),
            "xml_files": morphhb_xml_count,
        },
        "morphgnt": {
            "status": morphgnt_status,
            "path": str(MORPHGNT_PATH),
            "txt_files": morphgnt_txt_count,
        },
        "correspondence_index": {
            "entry_count": corr_entry_count,
            **({"error": corr_index_error} if corr_index_error else {}),
        },
        "verify_verse_status": verify_status,
        "verify_verse_detail": verify_detail,
        "note": (
            "morphhb/morphgnt missing は故障ではない。"
            "scripts/bootstrap_morph_data.sh を実行するとデータが配置される。"
            "データ未配置時、verify_verse は unavailable を返す（正しい動作）。"
        ),
    }


@router.get("/verse/{ref:path}")
async def get_verse(ref: str):
    """節の完全な原語解析を返す。ref は OSIS 形式（例: Gen.3.5）。"""
    try:
        verse = lookup_verse(ref)
    except FileNotFoundError as exc:
        raise HTTPException(404, detail=str(exc))
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, detail=str(exc))
    return {
        "ref": verse.ref,
        "language": verse.language,
        "words": [
            {
                "surface":   w.surface,
                "strongs":   w.strongs,
                "translit":  w.translit,
                "morph":     w.morph,
            }
            for w in verse.words
        ],
    }


@router.get("/verify/{ref:path}/{strongs}")
async def get_verify(ref: str, strongs: str):
    """節に指定 Strong's ID が実在するか検証する。

    重要サニティチェック:
      /verify/Gen.3.5/H3045   → contains: true  （yadaはEdenaのエピソードにある）
      /verify/Gen.32.29/H3045 → contains: false  （ヤコブ改名にyadaは無い）
    """
    return verify_verse(ref, strongs)


@router.get("/search/{strongs}")
async def get_search(strongs: str, max_results: int = 50):
    """Strong's ID が出現する全節を返す（ヘブライ語のみ）。"""
    try:
        results = search_by_strongs(strongs, max_results=max_results)
    except NotImplementedError as exc:
        raise HTTPException(501, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(503, detail=str(exc))
    return {"strongs": strongs.upper(), "count": len(results), "results": results}


@router.get("/word/{strongs}")
async def get_word(strongs: str):
    """Strong's 辞書エントリを返す。"""
    try:
        return lookup_word(strongs)
    except KeyError:
        raise HTTPException(404, detail=f"Strong's ID not found: {strongs}")
