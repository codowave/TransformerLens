"""
lexicon_router.py — 原語照合 FastAPI ルーター

エンドポイント:
  GET /api/lexicon/verse/{ref}          節の完全な原語解析
  GET /api/lexicon/verify/{ref}/{strongs}  節にStrong'sが実在するか検証
  GET /api/lexicon/search/{strongs}     全出現箇所（Hナンバーのみ）
  GET /api/lexicon/word/{strongs}       Strong's辞書エントリ
"""

from fastapi import APIRouter, HTTPException
from .biblical_lexicon import (
    lookup_verse,
    verify_verse,
    search_by_strongs,
    lookup_word,
)

router = APIRouter(tags=["lexicon"])


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
