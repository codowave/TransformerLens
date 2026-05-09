"""
biblical_lexicon.py — 原語照合レイヤー コアモジュール

第一作業原理: 露頭の同定は、まず原語の確認から始まる。
翻訳の語の「雰囲気」で原語を推測せず、ヘブライ語・ギリシャ語本文を直接照合する。

データソース:
  Hebrew: openscriptures/morphhb (OSIS XML, CC BY 4.0)
  Greek:  morphgnt/sblgnt (plain text) + morphgnt/morphgnt (morphology)
  Strong's: openscriptures/strongs (Public Domain)
"""

from __future__ import annotations

import json
import logging
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths — override via environment variables
# ---------------------------------------------------------------------------
DATA_ROOT    = Path(__file__).parent
REPO_ROOT    = DATA_ROOT.parent
MORPHHB_PATH = Path(os.environ.get("MORPHHB_PATH",
                    str(REPO_ROOT / "data" / "morphhb" / "wlc")))
SBLGNT_PATH  = Path(os.environ.get("SBLGNT_PATH",
                    str(REPO_ROOT / "data" / "sblgnt")))
MORPHGNT_PATH = Path(os.environ.get("MORPHGNT_PATH",
                     str(REPO_ROOT / "data" / "morphgnt")))
STRONGS_HEB  = DATA_ROOT / "strongs_hebrew.json"
STRONGS_GRK  = DATA_ROOT / "strongs_greek.json"

OSIS_NS = "http://www.bibletechnologies.net/2003/OSIS/namespace"

# ---------------------------------------------------------------------------
# OSIS book-name → file name mapping (morphhb uses these names)
# ---------------------------------------------------------------------------
HEB_BOOKS = [
    "Gen","Exod","Lev","Num","Deut","Josh","Judg","Ruth",
    "1Sam","2Sam","1Kgs","2Kgs","1Chr","2Chr","Ezra","Neh","Esth",
    "Job","Ps","Prov","Eccl","Song","Isa","Jer","Lam","Ezek","Dan",
    "Hos","Joel","Amos","Obad","Jonah","Mic","Nah","Hab","Zeph",
    "Hag","Zech","Mal",
]

GRK_BOOKS = [
    "Matt","Mark","Luke","John","Acts","Rom","1Cor","2Cor","Gal",
    "Eph","Phil","Col","1Thess","2Thess","1Tim","2Tim","Titus",
    "Phlm","Heb","Jas","1Pet","2Pet","1John","2John","3John","Jude","Rev",
]

# MorphGNT uses zero-padded book numbers; build a map
_MORPHGNT_BOOK_NUM: dict[str, str] = {
    b: f"{i+40:02d}" for i, b in enumerate(GRK_BOOKS)
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class Word:
    surface:   str
    strongs:   list[str]     = field(default_factory=list)
    translit:  str           = ""
    morph:     str           = ""
    lemma_raw: str           = ""


@dataclass
class Verse:
    ref:      str
    language: str            # "Hebrew" or "Greek"
    words:    list[Word]     = field(default_factory=list)


# ---------------------------------------------------------------------------
# Strong's dictionary (lazy-loaded)
# ---------------------------------------------------------------------------
_strongs_heb: dict | None = None
_strongs_grk: dict | None = None


def _load_strongs_heb() -> dict:
    global _strongs_heb
    if _strongs_heb is None:
        if STRONGS_HEB.exists():
            with open(STRONGS_HEB, encoding="utf-8") as f:
                _strongs_heb = json.load(f)
        else:
            log.warning("strongs_hebrew.json not found at %s", STRONGS_HEB)
            _strongs_heb = {}
    return _strongs_heb


def _load_strongs_grk() -> dict:
    global _strongs_grk
    if _strongs_grk is None:
        if STRONGS_GRK.exists():
            with open(STRONGS_GRK, encoding="utf-8") as f:
                _strongs_grk = json.load(f)
        else:
            log.warning("strongs_greek.json not found at %s", STRONGS_GRK)
            _strongs_grk = {}
    return _strongs_grk


def lookup_word(strongs_id: str) -> dict:
    """Return the Strong's dictionary entry for a given ID (e.g. 'H3045', 'G1097')."""
    sid = strongs_id.upper()
    if sid.startswith("H"):
        entry = _load_strongs_heb().get(sid) or _load_strongs_heb().get(strongs_id)
    elif sid.startswith("G"):
        entry = _load_strongs_grk().get(sid) or _load_strongs_grk().get(strongs_id)
    else:
        entry = None
    if entry is None:
        raise KeyError(f"Strong's ID not found: {strongs_id}")
    return entry


# ---------------------------------------------------------------------------
# Lemma parsing helpers
# ---------------------------------------------------------------------------
_STRONGS_RE = re.compile(r"strong:([HG]\d+[a-z]?)", re.IGNORECASE)


def _strongs_from_lemma(lemma_attr: str) -> list[str]:
    """Extract all Strong's IDs from a morphhb lemma attribute.

    Handles:
      "strong:H3045"
      "b/strong:H7225"           ← prefix + strong
      "strong:H853 strong:H8064" ← space-separated compound
    """
    return [m.group(1).upper() for m in _STRONGS_RE.finditer(lemma_attr)]


def _translit_for(strongs_list: list[str], language: str) -> str:
    """Return the best available transliteration string for a word.

    The Hebrew dictionary uses 'xlit'; the Greek dictionary uses 'translit'.
    """
    db = _load_strongs_heb() if language == "Hebrew" else _load_strongs_grk()
    for sid in strongs_list:
        entry = db.get(sid.upper()) or db.get(sid)
        if entry:
            return entry.get("xlit") or entry.get("translit") or ""
    return ""


# ---------------------------------------------------------------------------
# Hebrew parsing (morphhb OSIS XML)
# ---------------------------------------------------------------------------
def _parse_hebrew_verse(xml_path: Path, ref: str) -> Verse:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    ns   = {"o": OSIS_NS}

    verse_el = root.find(f".//o:verse[@osisID='{ref}']", ns)
    if verse_el is None:
        raise KeyError(f"Verse not found in morphhb: {ref}")

    words: list[Word] = []
    for w_el in verse_el.findall(f"o:w", ns):
        surface   = "".join(w_el.itertext()).strip()
        lemma_raw = w_el.get("lemma", "")
        morph     = w_el.get("morph", "")
        strongs   = _strongs_from_lemma(lemma_raw)
        translit  = _translit_for(strongs, "Hebrew")
        words.append(Word(
            surface=surface,
            strongs=strongs,
            translit=translit,
            morph=morph,
            lemma_raw=lemma_raw,
        ))

    return Verse(ref=ref, language="Hebrew", words=words)


# ---------------------------------------------------------------------------
# Greek parsing (MorphGNT TSV format)
# ---------------------------------------------------------------------------
# MorphGNT line format (space-separated):
#   BCVWP POS Parse Strongs Lemma Form Word
# Example:
#   400101010 CONJ ---- G2532 καί Καὶ Καὶ
def _parse_greek_verse_morphgnt(book: str, ref: str) -> Verse:
    book_num = _MORPHGNT_BOOK_NUM.get(book)
    if book_num is None:
        raise KeyError(f"Unknown Greek book: {book}")

    # MorphGNT files are named like "01-Mt-morphgnt.txt"
    candidates = list(MORPHGNT_PATH.glob(f"{book_num}-*-morphgnt.txt"))
    if not candidates:
        candidates = list(MORPHGNT_PATH.glob(f"{book_num}*.txt"))
    if not candidates:
        raise FileNotFoundError(
            f"MorphGNT file not found for {book} in {MORPHGNT_PATH}"
        )

    _, chap, vnum = ref.split(".")
    # BCV prefix in MorphGNT: book(2) + chap(2) + verse(2) = 6 digits (padded)
    # Actually MorphGNT uses BCVWP where B=2, C=2, V=2, W=2, P=1 total 9 chars
    target_prefix = f"{book_num}{int(chap):02d}{int(vnum):02d}"

    words: list[Word] = []
    with open(candidates[0], encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 7:
                continue
            bcvwp, pos, parse, strongs_raw, lemma, form, word_text = parts[:7]
            if not bcvwp.startswith(target_prefix):
                continue
            sid = strongs_raw.upper() if strongs_raw.startswith("G") else ""
            translit = ""
            if sid:
                entry = _load_strongs_grk().get(sid)
                if entry:
                    translit = entry.get("xlit") or ""
            words.append(Word(
                surface=word_text,
                strongs=[sid] if sid else [],
                translit=translit,
                morph=f"{pos} {parse}".strip(),
                lemma_raw=lemma,
            ))

    if not words:
        raise KeyError(f"Verse not found in MorphGNT: {ref}")
    return Verse(ref=ref, language="Greek", words=words)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
@lru_cache(maxsize=512)
def lookup_verse(ref: str) -> Verse:
    """Return a Verse with full word-level Strong's annotation.

    ref must be OSIS format, e.g. "Gen.3.5", "John.17.3".
    Raises FileNotFoundError if the underlying data is not present.
    """
    parts = ref.split(".")
    if len(parts) != 3:
        raise ValueError(f"Expected OSIS ref (Book.chap.verse), got: {ref!r}")
    book = parts[0]

    # Hebrew
    heb_file = MORPHHB_PATH / f"{book}.xml"
    if heb_file.exists():
        return _parse_hebrew_verse(heb_file, ref)

    # Greek via MorphGNT
    if book in GRK_BOOKS and MORPHGNT_PATH.exists():
        try:
            return _parse_greek_verse_morphgnt(book, ref)
        except FileNotFoundError:
            pass

    raise FileNotFoundError(
        f"No morphological data for {ref!r}. "
        f"Ensure MORPHHB_PATH or MORPHGNT_PATH points to the data."
    )


def verify_verse(ref: str, strongs_id: str) -> dict:
    """Return whether a Strong's ID appears in a verse.

    Returns a three-state result — callers MUST check "status", not just "contains":

        status="found"       contains=True   — word confirmed present
        status="not_found"   contains=False  — word confirmed absent (data was available)
        status="unavailable" contains=None   — morphological data not present; absence
                                               cannot be asserted

    Conflating "not_found" and "unavailable" via contains=False would cause
    downstream injection to tell Claude a word is absent when the data simply
    isn't loaded — this is the canonical Codex P1 bug this function prevents.
    """
    sid = strongs_id.upper()
    try:
        verse = lookup_verse(ref)
    except FileNotFoundError as exc:
        return {
            "status": "unavailable",
            "contains": None,
            "ref": ref,
            "strongs": sid,
            "occurrences": 0,
            "reason": "morphhb_not_available",
            "error": str(exc),
        }
    except (KeyError, ValueError) as exc:
        return {
            "status": "unavailable",
            "contains": None,
            "ref": ref,
            "strongs": sid,
            "occurrences": 0,
            "reason": "ref_not_found",
            "error": str(exc),
        }

    matching = [
        w for w in verse.words if sid in [s.upper() for s in w.strongs]
    ]
    found = len(matching) > 0
    return {
        "status": "found" if found else "not_found",
        "contains": found,
        "ref": ref,
        "strongs": sid,
        "language": verse.language,
        "occurrences": len(matching),
        "words": [
            {"surface": w.surface, "translit": w.translit, "morph": w.morph}
            for w in matching
        ],
    }


def search_by_strongs(strongs_id: str, max_results: int = 50) -> list[dict]:
    """Return all verses in the Hebrew corpus that contain a Strong's ID.

    Note: Full-corpus scan is expensive (~1-2 s first call). Results are
    not cached at this level; wrap in an endpoint-level cache if needed.
    """
    sid = strongs_id.upper()
    if not sid.startswith("H"):
        raise NotImplementedError(
            "search_by_strongs currently supports Hebrew only (H-numbers)."
        )

    if not MORPHHB_PATH.exists():
        raise FileNotFoundError(f"morphhb data not found at {MORPHHB_PATH}")

    results: list[dict] = []
    ns = {"o": OSIS_NS}

    for book in HEB_BOOKS:
        xml_file = MORPHHB_PATH / f"{book}.xml"
        if not xml_file.exists():
            continue
        try:
            tree = ET.parse(xml_file)
        except ET.ParseError as exc:
            log.warning("XML parse error in %s: %s", xml_file, exc)
            continue

        for verse_el in tree.getroot().findall(".//o:verse", ns):
            osis_id = verse_el.get("osisID", "")
            for w_el in verse_el.findall("o:w", ns):
                lemma_raw = w_el.get("lemma", "")
                found = [s for s in _strongs_from_lemma(lemma_raw)
                         if s.upper() == sid]
                if found:
                    surface = "".join(w_el.itertext()).strip()
                    results.append({
                        "ref": osis_id,
                        "surface": surface,
                        "morph": w_el.get("morph", ""),
                    })
                    if len(results) >= max_results:
                        return results
    return results
