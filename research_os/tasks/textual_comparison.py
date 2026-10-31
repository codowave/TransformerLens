"""
textual_comparison.py — 相応論テキストとの照合タスク

mode="falsification":
  「この対応を支持する記述探し」ではなく
  「この対応を壊す記述・非対称性・階層差を探す」。

  判定の二段構え（2026-10-31 改訂）:
  1. 候補（lead）— キーワード一致は「読むべき項目」を挙げるだけ。判定には使わない。
     influx / love / will / light 等はスウェーデンボルグの基本語彙そのものなので、
     一致数は「反証の強さ」ではなく「スウェーデンボルグらしさ」を測ってしまう。
  2. 反証（challenge）— 索引エントリに人が付けた注記
     falsification_relevance == focus_fp かつ falsification_direction == "challenges"
     のものだけを反証項目として扱う。さらに verified の三状態で分ける:
       verified: true   → 原典照合済み（confirmed）
       verified: false  → 未照合と明示（unverified）
       verified: なし   → 照合状態不明（unknown）。true と同一視しない

  総合判定:
    falsified    — 原典照合済みの反証項目が1件以上ある（反例は1件で足りる）
    inconclusive — 反証項目はあるが照合済みでない／索引が薄く不在を言えない
    survives     — 反証項目なし、かつ索引が一定以上（非存在の主張ではない）

  判定は件数の閾値に依存しない。索引を拡充しても、照合済みの反証項目が
  増えない限り判定は動かない（旧実装は「challenges ≥ 3」の絶対数で
  falsified を返したため、索引を増やすほど中身と無関係に反証へ寄った）。

mode="support" は探索燃料としては有効だが検証本筋では使わない。
"""

from __future__ import annotations

import dataclasses
import json
import logging
from enum import Enum
from pathlib import Path
from typing import Literal

log = logging.getLogger(__name__)

_INDEX_PATH = Path(__file__).parent.parent.parent / "biblical_correspondence" / "correspondence" / "correspondence_index.json"

# 不在（survives）を言うのに最低限必要な索引の件数。反証（falsified）には使わない。
MIN_ENTRIES_FOR_ABSENCE = 20


class TCVerdict(str, Enum):
    FALSIFIED    = "falsified"    # 原典照合済みの記述が仮説の中核主張を否定する
    INCONCLUSIVE = "inconclusive" # 脅かす候補はあるが照合済みでない／索引が薄い
    SURVIVES     = "survives"     # 反証見つからず（非存在の主張ではない）


VerifiedState = Literal["confirmed", "unverified", "unknown"]


@dataclasses.dataclass
class EntryAnalysis:
    entry_id:     str
    work_section: str
    text_excerpt: str
    keywords:     list[str]
    classification: Literal["challenges", "lead", "irrelevant"]
    challenge_reason: str = ""
    verified_state: VerifiedState = "unknown"


@dataclasses.dataclass
class TextualComparisonResult:
    mode:     str
    focus_fp: str
    focus_description: str

    index_coverage: dict  # {entry_count, works_indexed, coverage_note}
    search_terms:   list[str]

    challenges:  list[EntryAnalysis]   # 人の注記で反証方向とされた項目（照合状態つき）
    leads:       list[EntryAnalysis]   # キーワード一致のみ。読むべき候補で、判定に使わない

    verdict:     TCVerdict
    verdict_rationale: str

    epistemic_note: str  # インデックス未整備の場合の unavailable 注記

    @property
    def confirmed_challenges(self) -> list[EntryAnalysis]:
        return [a for a in self.challenges if a.verified_state == "confirmed"]

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "focus_fp": self.focus_fp,
            "focus_description": self.focus_description,
            "index_coverage": self.index_coverage,
            "search_terms": self.search_terms,
            "challenges": [dataclasses.asdict(e) for e in self.challenges],
            "leads": [dataclasses.asdict(e) for e in self.leads],
            "verdict": self.verdict.value,
            "verdict_rationale": self.verdict_rationale,
            "epistemic_note": self.epistemic_note,
        }


# ---------------------------------------------------------------------------
# fp-2 の falsification 検索定義
# ---------------------------------------------------------------------------
# fp-2: softmax の確率分布化 — Swedenborg に確率的媒介の概念はない
# リスク: 量的正規化が霊的秩序をアナロジカルに模倣しているという主張
#
# 反証となる記述の特徴:
#   A) 対応が「量的グラデーション」を否定する（all-or-nothing な構造）
#   B) 流入が「確率的」ではなく「秩序的・構造的」であることを明示する
#   C) 自然的事物が内的実在の「写し」であり、「近似」ではないことを強調する
#   D) 愛/意志が「方向性」であり「確率分布」ではないことを示す

FP2_SEARCH_TERMS = [
    "probability", "gradation", "degree", "weight", "proportion",
    "influx", "order", "reception", "love", "will", "affection",
    "spiritual ordering", "normalization", "measure", "quantitative",
    "heat", "light", "correspondence", "mediation",
]

# 読むべき候補（lead）を挙げるための語。判定には使わない。
FP2_CHALLENGE_KEYWORDS = {
    "influx": "流入の秩序性・構造性は softmax の確率的正規化と質的に異なる可能性",
    "order": "対応の秩序は量的グラデーションではなく質的階層",
    "reception": "受容は確率的重み付けではなく器の質による",
    "love": "愛は方向性であり確率分布ではない",
    "will": "意志は選好分布ではなく志向性",
    "affection": "affection は attention score の確率的アナロジーと構造的に異なる",
    "degree": "degrees of influx は連続的グラデーションか段階的不連続か",
    "heat": "天界の heat（愛）は強度グラデーションを持つ — softmax との類似と差異",
    "light": "天界の light（真理）の gradation は attention weight の gradation と同型か",
}


def _load_index() -> dict:
    if not _INDEX_PATH.exists():
        return {}
    with open(_INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def _verified_state(entry: dict) -> VerifiedState:
    """verified の三状態。キーがない・null を true と同一視しない。"""
    v = entry.get("verified")
    if v is True:
        return "confirmed"
    if v is False:
        return "unverified"
    return "unknown"


def _is_annotated_challenge(entry: dict, focus_fp: str) -> bool:
    return (
        entry.get("falsification_relevance") == focus_fp
        and entry.get("falsification_direction") == "challenges"
    )


def _classify_entry_fp2(entry: dict, mode: str, focus_fp: str = "fp-2") -> EntryAnalysis:
    """fp-2 falsification の観点でエントリを分類する。

    challenges — 人の注記で反証方向とされた項目
    lead       — 注記はないがキーワードに一致した項目（読む候補）
    irrelevant — どちらでもない
    """
    text     = entry.get("text", "").lower()
    keywords = [k.lower() for k in entry.get("keywords", [])]
    all_text = text + " " + " ".join(keywords)

    hit_reasons = [
        f"[{kw}] {reason}"
        for kw, reason in FP2_CHALLENGE_KEYWORDS.items()
        if kw in all_text
    ]

    if _is_annotated_challenge(entry, focus_fp):
        classification   = "challenges"
        challenge_reason = entry.get("note", "") or "; ".join(hit_reasons[:3])
    elif hit_reasons:
        classification   = "lead"
        challenge_reason = "; ".join(hit_reasons[:3])
    else:
        classification   = "irrelevant"
        challenge_reason = ""

    excerpt = entry.get("text", "")[:200] + ("..." if len(entry.get("text", "")) > 200 else "")

    return EntryAnalysis(
        entry_id=entry.get("id", ""),
        work_section=f"{entry.get('work', '')} {entry.get('section', '')}",
        text_excerpt=excerpt,
        keywords=entry.get("keywords", []),
        classification=classification,
        challenge_reason=challenge_reason,
        verified_state=_verified_state(entry),
    )


def _make_verdict(
    challenges: list[EntryAnalysis],
    leads:      list[EntryAnalysis],
    coverage:   dict,
    focus_fp:   str,
) -> tuple[TCVerdict, str]:
    """falsification 判定を返す。件数の閾値には依存しない。"""
    confirmed   = [a for a in challenges if a.verified_state == "confirmed"]
    unconfirmed = [a for a in challenges if a.verified_state != "confirmed"]
    entry_count = coverage.get("entry_count", 0)

    if confirmed:
        ids = ", ".join(a.entry_id for a in confirmed)
        return (
            TCVerdict.FALSIFIED,
            f"原典照合済みの反証項目 {len(confirmed)} 件（{ids}）。"
            f"これらが {focus_fp} の中核主張を否定するという注記に基づく。"
            "反例は1件で足りるため、件数や索引の大きさには依存しない。"
        )

    if unconfirmed:
        detail = ", ".join(f"{a.entry_id}({a.verified_state})" for a in unconfirmed)
        return (
            TCVerdict.INCONCLUSIVE,
            f"反証方向の注記がある項目 {len(unconfirmed)} 件はいずれも原典未照合"
            f"（{detail}）。原典（AC/HH/DLW）で照合し verified: true に"
            "昇格するまで falsified とは判定しない。"
            f"キーワード一致の候補 {len(leads)} 件は判定に使っていない。"
        )

    if entry_count < MIN_ENTRIES_FOR_ABSENCE:
        return (
            TCVerdict.INCONCLUSIVE,
            f"インデックスのエントリ数が {entry_count} 件と少なく、"
            "反証の不在を言える網羅性がない。"
            "これは「反証がない」ではなく「探せていない」。"
        )

    return (
        TCVerdict.SURVIVES,
        f"インデックス {entry_count} 件中、{focus_fp} への反証注記を持つ項目なし。"
        "ただし survives ≠ 支持確認。索引が薄い可能性は常にある。"
        f"キーワード一致の候補 {len(leads)} 件は未読なら読む価値がある。"
    )


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------

def run(
    hypothesis: dict,
    mode:       str = "falsification",
    focus_fp:   str = "fp-2",
) -> TextualComparisonResult:
    """textual_comparison タスクを実行する。

    Args:
        hypothesis: hyp-001.md の YAML front-matter
        mode: "falsification" のみ実装（"support" は探索燃料用で検証本筋では非推奨）
        focus_fp: 今回フォーカスする failure point ID

    Returns:
        TextualComparisonResult
    """
    if mode != "falsification":
        raise NotImplementedError(
            f"mode={mode!r} は未実装。"
            "textual_comparison は falsification モードで使用すること。"
            "support モードは探索燃料としては有効だが検証本筋では危険。"
        )
    if focus_fp != "fp-2":
        raise NotImplementedError(
            f"focus_fp={focus_fp!r} の textual_comparison は未実装。"
            "現在は fp-2（softmax 確率分布化）のみ対応。"
        )

    # fp-2 の説明を仮説文書から取得
    fps_raw   = hypothesis.get("candidate_failure_points", [])
    fp2_raw   = next((f for f in fps_raw if f.get("id") == "fp-2"), {})
    focus_desc = fp2_raw.get("description", "softmax の確率分布化 — Swedenborg に確率的媒介の概念はない")

    # インデックス読み込み
    index_data  = _load_index()
    entries     = index_data.get("entries", [])
    coverage    = {
        "entry_count":   len(entries),
        "works_indexed": index_data.get("works_indexed", []),
        "coverage_note": index_data.get("coverage_note", ""),
    }

    analyses = [_classify_entry_fp2(e, mode, focus_fp) for e in entries]

    challenges = [a for a in analyses if a.classification == "challenges"]
    leads      = [a for a in analyses if a.classification == "lead"]

    verdict, rationale = _make_verdict(challenges, leads, coverage, focus_fp)

    epistemic_note = (
        "このスキャンは correspondence_index.json（現在 {} 件）のみを対象とする。\n"
        "インデックス外の AC/HH/DLW 記述は照合されていない。\n"
        "反証判定は人が付けた反証注記と verified の状態だけに基づき、\n"
        "キーワード一致（leads）は読む候補の提示に留める。\n"
        "'survives' は「索引の範囲内で反証が見つからなかった」であり、\n"
        "「スウェーデンボルグが softmax アナロジーを否定していない」ではない。"
    ).format(len(entries))

    return TextualComparisonResult(
        mode=mode,
        focus_fp=focus_fp,
        focus_description=focus_desc,
        index_coverage=coverage,
        search_terms=FP2_SEARCH_TERMS,
        challenges=challenges,
        leads=leads,
        verdict=verdict,
        verdict_rationale=rationale,
        epistemic_note=epistemic_note,
    )
