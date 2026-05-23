"""
textual_comparison.py — 相応論テキストとの照合タスク

mode="falsification":
  「この対応を支持する記述探し」ではなく
  「この対応を壊す記述・非対称性・階層差を探す」。

  探索の順序:
  1. focus_fp に関連するキーワードを correspondence_index から抽出
  2. 各エントリを falsification 観点でスキャン
     — 対応論が「確率的・量的・水平的」な処理を明示的に否定しているか
     — 対応の階層性・一方向性・非還元性を強調する記述があるか
  3. スキャン結果を verdict に分類:
       challenges  — 仮説の主張を直接脅かす記述
       neutral     — 関連するが脅かさない
       irrelevant  — 関係なし
  4. 総合判定: falsified / inconclusive / survives

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


class TCVerdict(str, Enum):
    FALSIFIED    = "falsified"    # テキストが仮説の中核主張を否定する
    INCONCLUSIVE = "inconclusive" # 脅かすが決定的でない
    SURVIVES     = "survives"     # 反証見つからず（非存在の主張ではない）


@dataclasses.dataclass
class EntryAnalysis:
    entry_id:     str
    work_section: str
    text_excerpt: str
    keywords:     list[str]
    classification: Literal["challenges", "neutral", "irrelevant"]
    challenge_reason: str = ""


@dataclasses.dataclass
class TextualComparisonResult:
    mode:     str
    focus_fp: str
    focus_description: str

    index_coverage: dict  # {entry_count, works_indexed, coverage_note}
    search_terms:   list[str]

    challenges:  list[EntryAnalysis]
    neutral:     list[EntryAnalysis]

    verdict:     TCVerdict
    verdict_rationale: str

    epistemic_note: str  # インデックス未整備の場合の unavailable 注記

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "focus_fp": self.focus_fp,
            "focus_description": self.focus_description,
            "index_coverage": self.index_coverage,
            "search_terms": self.search_terms,
            "challenges": [dataclasses.asdict(e) for e in self.challenges],
            "neutral": [dataclasses.asdict(e) for e in self.neutral],
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

FP2_CHALLENGE_KEYWORDS = {
    # これらのキーワードが「量的でない」「秩序的」「構造的」な文脈で使われると challenges
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


def _classify_entry_fp2(entry: dict, mode: str) -> EntryAnalysis:
    """fp-2 falsification の観点でエントリを分類する。"""
    text     = entry.get("text", "").lower()
    keywords = [k.lower() for k in entry.get("keywords", [])]
    all_text = text + " " + " ".join(keywords)

    # challenge キーワードが本文に含まれるか
    hit_reasons: list[str] = []
    for kw, reason in FP2_CHALLENGE_KEYWORDS.items():
        if kw in all_text:
            hit_reasons.append(f"[{kw}] {reason}")

    if not hit_reasons:
        classification  = "irrelevant"
        challenge_reason = ""
    elif len(hit_reasons) >= 2:
        # 複数の challenge キーワードが当たる = より強い challenges 候補
        classification   = "challenges"
        challenge_reason = "; ".join(hit_reasons[:3])
    else:
        # 1件 = neutral（判断保留）
        classification   = "neutral"
        challenge_reason = hit_reasons[0]

    excerpt = entry.get("text", "")[:200] + ("..." if len(entry.get("text", "")) > 200 else "")

    return EntryAnalysis(
        entry_id=entry.get("id", ""),
        work_section=f"{entry.get('work', '')} {entry.get('section', '')}",
        text_excerpt=excerpt,
        keywords=entry.get("keywords", []),
        classification=classification,
        challenge_reason=challenge_reason,
    )


def _make_verdict(
    challenges: list[EntryAnalysis],
    neutral:    list[EntryAnalysis],
    coverage:   dict,
    focus_fp:   str,
) -> tuple[TCVerdict, str]:
    """falsification 判定を返す。"""
    n_challenges = len(challenges)
    n_neutral    = len(neutral)
    entry_count  = coverage.get("entry_count", 0)

    if entry_count < 20:
        # インデックスが薄すぎて falsification の根拠として不十分
        return (
            TCVerdict.INCONCLUSIVE,
            f"インデックスのエントリ数が {entry_count} 件と少なく、"
            "反証検索の網羅性が低い。"
            f"challenges={n_challenges}, neutral={n_neutral} だが、"
            "これは「反証がない」ではなく「探せていない」。"
            "correspondence_index を拡充（PR #9 相当）してから再実行すること。"
        )

    if n_challenges == 0:
        return (
            TCVerdict.SURVIVES,
            f"インデックス {entry_count} 件中 {focus_fp} を直接脅かすエントリなし。"
            "ただし survives ≠ 支持確認。索引が薄い可能性は常にある。"
        )
    elif n_challenges <= 2:
        return (
            TCVerdict.INCONCLUSIVE,
            f"{n_challenges} 件の challenges エントリ。決定的ではないが要精査。"
            "challenges エントリの原典（AC/HH/DLW）を直接確認し、"
            "文脈が fp-2 の破綻を示すか判断すること。"
        )
    else:
        return (
            TCVerdict.FALSIFIED,
            f"{n_challenges} 件の challenges エントリ。"
            "対応論が量的正規化と質的に異なる構造を持つことが複数箇所で示唆される。"
            "fp-2 は confirmed failure point として hyp-001 を stay_candidate に戻す必要がある。"
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

    # 全エントリを fp-2 falsification 観点で分類
    analyses = [_classify_entry_fp2(e, mode) for e in entries]

    challenges = [a for a in analyses if a.classification == "challenges"]
    neutral    = [a for a in analyses if a.classification == "neutral"]

    verdict, rationale = _make_verdict(challenges, neutral, coverage, focus_fp)

    epistemic_note = (
        "このスキャンは correspondence_index.json（現在 {} 件）のみを対象とする。\n"
        "インデックス外の AC/HH/DLW 記述は照合されていない。\n"
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
        neutral=neutral,
        verdict=verdict,
        verdict_rationale=rationale,
        epistemic_note=epistemic_note,
    )
