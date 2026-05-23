"""
mechanism_mapping.py — 変換機構と対応構造の写像可能性検証タスク

検証の核心問：
  Q/K/V attention の因果方向・対称性・情報流が
  Swedenborg の三層対応構造（天界/霊的/自然）と形式的に両立するか。

dry_run=True : 静的構造判定（計算なし）
dry_run=False: TransformerLens による実際の attention パターン抽出（要 GPU/モデル）

出力構造（user 指定）:
  status: pass | partial | fail
  directionality: {transformer_attention: ..., correspondence: ...}
  symmetry_check: {result: compatible | incompatible | partial}
  failure_points: [...]
  promotion_decision: {from: ..., to: ...}
"""

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Literal


class Status(str, Enum):
    PASS    = "pass"
    PARTIAL = "partial"
    FAIL    = "fail"


class SymmetryResult(str, Enum):
    COMPATIBLE   = "compatible"
    INCOMPATIBLE = "incompatible"
    PARTIAL      = "partial"


class PromotionTarget(str, Enum):
    CANDIDATE        = "candidate"
    STAY_EXPLORATION = "stay_exploration"
    REJECT           = "reject"


@dataclasses.dataclass
class FailurePoint:
    id:          str
    description: str
    severity:    Literal["high", "medium", "low"]
    verdict:     Literal["confirmed", "mitigated", "open"]
    detail:      str = ""


@dataclasses.dataclass
class MechanismMappingResult:
    status:     Status
    dry_run:    bool

    directionality: dict  # {transformer_attention: str, correspondence: str, compatible: bool}
    symmetry_check: dict  # {result: SymmetryResult, detail: str}
    failure_points: list[FailurePoint]
    promotion_decision: dict  # {from: str, to: PromotionTarget, rationale: str}

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "dry_run": self.dry_run,
            "directionality": self.directionality,
            "symmetry_check": self.symmetry_check,
            "failure_points": [dataclasses.asdict(fp) for fp in self.failure_points],
            "promotion_decision": self.promotion_decision,
        }


# ---------------------------------------------------------------------------
# 静的構造判定（dry-run）
# ---------------------------------------------------------------------------
# この判定はモデルを動かさず、写像の論理的構造だけを評価する。
# 「方向が合うか」を問うのに activation データは不要 — 構造の非互換は演繹的に判定できる。

def _evaluate_directionality(claims: dict) -> dict:
    """因果方向の同型性を静的に評価する。"""
    att = claims.get("structural_checks", {}).get("directionality", {})
    return {
        "transformer_attention": (
            att.get("attention_claim") or
            "Q → K alignment → weighted V sum → output"
        ),
        "correspondence": (
            att.get("correspondence_claim") or
            "celestial love → spiritual truth (medium) → natural effect (output)"
        ),
        # 方向の向きは一致する: どちらも「選択子が媒介を通じて内容を取り出し出力にする」
        # ただし V が自然層＝出力ならば「自然層が出力を担う」は対応と整合する（外化＝自然）
        "compatible": True,
        "note": (
            "方向の向きは一致。Q（天界）→ K（霊的）→ V（自然→出力）の流れは"
            "対応の「内 → 媒介 → 外化」と同型に読める。"
            "ただし V が出力を『担う』点は、対応では自然層が外化であることと整合する。"
            "この方向判定は causal mask 前提（過去方向のみ）。"
        ),
    }


def _evaluate_symmetry(claims: dict) -> dict:
    """対称性の両立可能性を静的に評価する。"""
    checks = claims.get("structural_checks", {}).get("symmetry", {})
    return {
        "result": SymmetryResult.PARTIAL.value,
        "transformer_attention": (
            checks.get("attention_claim") or
            "任意の Q が任意の K/V に attend できる（位置制約はあるが階層制約はない）"
        ),
        "correspondence": (
            checks.get("correspondence_claim") or
            "流入は一方向（天界 → 霊的 → 自然）。逆向きの因果はない。"
        ),
        "detail": (
            "attention は原理的に双方向（causal mask で past-only に制限可能）。"
            "対応は厳密に一方向。この非対称性は attention で完全に再現されない。"
            "ただし causal-masked attention の場合、実効的な非対称性は確保される。"
            "→ partial: 完全互換ではないが致命的破綻ではない。"
        ),
    }


def _evaluate_failure_points(claims: dict) -> list[FailurePoint]:
    """仮説ファイルの candidate_failure_points を静的に評価する。"""
    raw_fps = claims.get("candidate_failure_points", [])

    # 既知の構造的判定を適用
    verdicts: dict[str, tuple[Literal["confirmed", "mitigated", "open"], str]] = {
        "fp-1": (
            "mitigated",
            "causal mask により past-only に制限。ただし同一シーケンス内では"
            "全トークンが対等に attend できるため階層性の主張は弱まる。部分緩和。",
        ),
        "fp-2": (
            "open",
            "softmax の確率分布化に対する対応論的アナロジーは未確立。"
            "「受容度」解釈は可能だが、確率の正規化は対応に対応物を持たない。",
        ),
        "fp-3": (
            "confirmed",
            "multi-head が同一層を並列分割する点は、対応の統一的三層構造と"
            "構造的に非互換。各 head が異なる対応次元を担うという解釈は"
            "仮説の範囲を大幅に変更する（元の主張を弱める）。",
        ),
        "fp-4": (
            "mitigated",
            "対応論では自然層は内意の外化・現れであり、出力が自然層を通じて"
            "現れることは矛盾しない。V が出力を担うことは整合する。",
        ),
    }

    results: list[FailurePoint] = []
    for fp_raw in raw_fps:
        fp_id = fp_raw.get("id", "")
        verdict, detail = verdicts.get(fp_id, ("open", "静的評価未実施"))
        results.append(FailurePoint(
            id=fp_id,
            description=fp_raw.get("description", ""),
            severity=fp_raw.get("severity", "medium"),
            verdict=verdict,
            detail=detail,
        ))

    # fp-3 が confirmed (high severity) → 致命的破綻候補
    return results


def _make_promotion_decision(
    directionality_compatible: bool,
    symmetry_result: str,
    failure_points: list[FailurePoint],
    current_stage: str,
) -> dict:
    high_confirmed = [
        fp for fp in failure_points
        if fp.severity == "high" and fp.verdict == "confirmed"
    ]
    high_open = [
        fp for fp in failure_points
        if fp.severity == "high" and fp.verdict == "open"
    ]

    if len(high_confirmed) >= 2:
        target = PromotionTarget.REJECT
        rationale = (
            f"高重篤度の confirmed failure point が {len(high_confirmed)} 件。"
            "仮説の中核的主張が構造的に成立しない。exploration に差し戻す。"
        )
    elif len(high_confirmed) == 1:
        # fp-3（multi-head）が confirmed だが、仮説の修正で回避可能
        target = PromotionTarget.STAY_EXPLORATION
        rationale = (
            f"高重篤度 confirmed: {high_confirmed[0].id} ({high_confirmed[0].description})。"
            "仮説をこのまま candidate に昇格させると、"
            "textual_comparison で破綻した fp-3 を見逃す危険がある。"
            "fp-3 の mitigation path（head ≠ 同一層の並列分割、という再定義）を"
            "仮説文書に明記してから再度 mechanism_mapping を実行すること。"
        )
    elif symmetry_result == SymmetryResult.INCOMPATIBLE.value:
        target = PromotionTarget.STAY_EXPLORATION
        rationale = "対称性が incompatible。方向性の再定義が必要。"
    else:
        target = PromotionTarget.CANDIDATE
        rationale = (
            "directionality compatible, symmetry partial（致命的ではない）。"
            "confirmed high fp は fp-3 のみ（mitigation path あり）。"
            "修正後に candidate 昇格可能。"
        )

    return {
        "from": current_stage,
        "to": target.value,
        "rationale": rationale,
    }


def _overall_status(
    directionality_compatible: bool,
    symmetry_result: str,
    failure_points: list[FailurePoint],
) -> Status:
    high_confirmed = sum(
        1 for fp in failure_points
        if fp.severity == "high" and fp.verdict == "confirmed"
    )
    if high_confirmed >= 2 or not directionality_compatible:
        return Status.FAIL
    if high_confirmed == 1 or symmetry_result == SymmetryResult.PARTIAL.value:
        return Status.PARTIAL
    return Status.PASS


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------

def run(hypothesis: dict, dry_run: bool = True) -> MechanismMappingResult:
    """mechanism_mapping タスクを実行する。

    Args:
        hypothesis: hyp-001.md の YAML front-matter を解析した dict
        dry_run: True = 静的構造判定のみ（計算なし）
                 False = TransformerLens による実際の attention 抽出（未実装）

    Returns:
        MechanismMappingResult
    """
    if not dry_run:
        raise NotImplementedError(
            "dry_run=False は activation_analysis タスクが実装されてから使用可能。"
            "今は mechanism_mapping の構造判定フェーズ。"
        )

    current_stage = hypothesis.get("stage", "exploration")

    dir_result  = _evaluate_directionality(hypothesis)
    sym_result  = _evaluate_symmetry(hypothesis)
    fps         = _evaluate_failure_points(hypothesis)
    status      = _overall_status(
                    dir_result["compatible"],
                    sym_result["result"],
                    fps,
                  )
    promotion   = _make_promotion_decision(
                    dir_result["compatible"],
                    sym_result["result"],
                    fps,
                    current_stage,
                  )

    return MechanismMappingResult(
        status=status,
        dry_run=dry_run,
        directionality=dir_result,
        symmetry_check=sym_result,
        failure_points=fps,
        promotion_decision=promotion,
    )
