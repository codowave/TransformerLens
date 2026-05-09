"""
correspondence_lookup.py — スウェーデンボルグ著作の内意照合レイヤー

三状態を厳密に区別する:
  found       : インデックスに当該節の記述が存在する
  not_found   : インデックスを探索した結果、対応記述なし
  unavailable : インデックス自体がその節・著作をカバーしていない

not_found と unavailable を混同してはならない。
「見つからない」と「調べられていない」は異なる事実である。
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

INDEX_PATH = Path(__file__).parent / "correspondence_index.json"

_COVERED_WORKS: frozenset[str] = frozenset()
_INDEX_BY_REF: dict[str, list[dict]] = {}
_INDEX_LOADED = False


def _load_index() -> None:
    global _INDEX_BY_REF, _COVERED_WORKS, _INDEX_LOADED
    if _INDEX_LOADED:
        return
    if not INDEX_PATH.exists():
        log.warning("correspondence_index.json not found at %s", INDEX_PATH)
        _INDEX_LOADED = True
        return

    with open(INDEX_PATH, encoding="utf-8") as f:
        data = json.load(f)

    _COVERED_WORKS = frozenset(data.get("works_indexed", []))
    for entry in data.get("entries", []):
        for ref in entry.get("bible_refs", []):
            _INDEX_BY_REF.setdefault(ref, []).append(entry)
    _INDEX_LOADED = True


@lru_cache(maxsize=256)
def lookup_correspondence(ref: str) -> dict:
    """Return Swedenborg passages corresponding to a Bible reference.

    Args:
        ref: OSIS reference string, e.g. "Gen.3.5", "John.17.3"

    Returns:
        {
            "status":    "found" | "not_found" | "unavailable",
            "reference": ref,
            "sources":   [{"work", "section", "text", "match_type", "note"}, ...]
        }

    Status semantics:
        found       — at least one indexed paragraph explicitly covers this ref
        not_found   — index covers the relevant work/book but has no entry for ref
        unavailable — index has not been built for this work/book range
    """
    _load_index()

    if not _INDEX_LOADED or not _COVERED_WORKS:
        return {"status": "unavailable", "reference": ref, "sources": []}

    matches = _INDEX_BY_REF.get(ref, [])
    if matches:
        sources = [
            {
                "work":       e["work"],
                "section":    f"{e['work']} {e['section']}",
                "text":       e.get("text", ""),
                "match_type": e.get("match_type", "direct"),
                "note":       e.get("note", ""),
                "keywords":   e.get("keywords", []),
            }
            for e in matches
        ]
        return {"status": "found", "reference": ref, "sources": sources}

    # Determine whether this ref falls within an indexed book range.
    # If the book belongs to a covered work, return not_found; otherwise unavailable.
    book = ref.split(".")[0] if "." in ref else ref
    covered = _ref_is_covered(book)
    status = "not_found" if covered else "unavailable"
    return {"status": status, "reference": ref, "sources": []}


def _ref_is_covered(book: str) -> bool:
    """Return True only if the index actually contains at least one entry for this book.

    This is conservative by design: returning not_found when we haven't done a
    thorough search is misleading. Only books that genuinely appear in the index
    can produce a not_found verdict; everything else is unavailable.
    """
    _load_index()
    return any(
        ref.split(".")[0] == book
        for ref in _INDEX_BY_REF
    )


def build_correspondence_context(ref: str) -> str:
    """Format a correspondence lookup result as a prompt-injectable text block.

    Returns empty string when nothing useful can be injected (unavailable with
    no sources), so callers can safely skip injection.
    """
    result = lookup_correspondence(ref)
    status = result["status"]

    if status == "unavailable" and not result["sources"]:
        return ""

    lines = [f"【verified_correspondence_context — {ref}】"]
    lines.append(f"  照合状態: {status}")

    if status == "found":
        for src in result["sources"]:
            lines.append(f"  ◆ {src['section']}  [{src['match_type']}]")
            if src["keywords"]:
                lines.append(f"    keywords: {', '.join(src['keywords'])}")
            if src["text"]:
                lines.append(f"    本文要約: {src['text']}")
            if src["note"]:
                lines.append(f"    注記: {src['note']}")
    elif status == "not_found":
        lines.append("  インデックスに直接対応する記述なし（索引カバー済み範囲内）")
    else:
        lines.append("  この節の索引は未整備（unavailable）")

    return "\n".join(lines)
