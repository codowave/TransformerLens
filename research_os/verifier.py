"""
仮説の検証タスクを実行する。

対応タスク:
  textual_comparison  : biblical_correspondence 辞典との照合
  mechanism_mapping   : Attention の Q/K/V → Swedenborg 構造への写像分析
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Literal

DICT_PATH = Path("biblical_correspondence/data/dictionary.json")

# Attention機構の概念 → 相応辞典で探すべき語の優先候補マップ
# キー: Attentionの構造的役割, 値: (検索語リスト, 探索理由)
_ATTENTION_SEARCH_MAP: dict[str, tuple[list[str], str]] = {
    "perception / understanding": (
        ["目", "光", "顔"],
        "Attentionの Query は「何を求めるか」を決定する。相応では目・光が知性・理解を表す",
    ),
    "reception / input": (
        ["耳", "水", "手"],
        "Key/Value は「受け取るもの」。相応では耳が順従・受容、水が真理の流入を表す",
    ),
    "affection / weighting": (
        ["愛", "心臓・心", "火"],
        "softmax による重み付けは「何に引きつけられるか」の選好。相応では愛・情愛が重みを決める",
    ),
    "influx / information flow": (
        ["光", "水", "風"],
        "情報の流れ（influx）。相応では光・水・風が高次から低次への流入を表す",
    ),
    "order / structure": (
        ["道・道路", "安息日", "山"],
        "Transformerの層構造・階層。相応では道が秩序・真理の系列、山が高次状態を表す",
    ),
    "output / expression": (
        ["手", "口（関連）", "足"],
        "Attention出力の行使。相応では手が能力・実行、足が下位の自然的行為を表す",
    ),
}

StatusType = Literal["candidate_matches_found", "no_matches", "unavailable"]


def _load_dictionary() -> list[dict]:
    if not DICT_PATH.exists():
        return []
    with open(DICT_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("entries", [])


def _search_entry(entries: list[dict], words: list[str]) -> list[dict]:
    """辞典エントリから指定語に完全一致するものを返す。"""
    result = []
    for w in words:
        for e in entries:
            if e["word"] == w and e not in result:
                result.append(e)
    return result


def _confidence_for_role(role: str, entry: dict) -> str:
    """役割と辞典エントリの内容から信頼度を推定。"""
    spiritual = entry.get("spiritual", "")
    high_keywords = ["理解", "知性", "真理", "愛", "流入", "知覚", "受容", "秩序"]
    medium_keywords = ["光", "水", "霊", "内的", "外的", "上", "下"]
    score = sum(1 for k in high_keywords if k in spiritual) * 2
    score += sum(1 for k in medium_keywords if k in spiritual)
    if score >= 4:
        return "high"
    elif score >= 2:
        return "medium"
    return "low"


def _run_textual_comparison(dry_run: bool) -> dict:
    entries = _load_dictionary()
    if not entries:
        return {"verification_task": "textual_comparison", "status": "unavailable",
                "reason": f"辞典データが見つかりません: {DICT_PATH}"}

    matches = []
    for role, (search_words, reason) in _ATTENTION_SEARCH_MAP.items():
        found = _search_entry(entries, search_words)
        for entry in found:
            matches.append({
                "attention_concept": role,
                "swedenborg_term": entry["word"],
                "literal": entry["literal"],
                "spiritual": entry["spiritual"],
                "value_shift": entry.get("value_shift", ""),
                "reference": entry.get("reference", ""),
                "confidence": _confidence_for_role(role, entry),
                "reason": reason,
            })

    status: StatusType = "candidate_matches_found" if matches else "no_matches"
    return {
        "verification_task": "textual_comparison",
        "hypothesis": "hyp-001",
        "source": "biblical_correspondence/data/dictionary.json",
        "status": status,
        "match_count": len(matches),
        "matches": matches,
        "note": "直接対応語は存在しない。身体・自然・概念カテゴリの間接類比として候補を抽出。採択はまだしない。",
    }


_MECHANISM_SYSTEM = """\
あなたは構造的類比の厳密な審査官です。
「対応している」という結論に向かって論証するのではなく、
構造的差異を先に列挙し、その後で残存する類比の価値を評価してください。
表面的な類似を深い同一性と混同しないでください。
概念の格下げ（Correspondenceを計算的重み付けに還元すること）は誤りとして明示してください。"""

_MECHANISM_PROMPT = """\
Transformer の Attention 機構とスウェーデンボルグの「相応の原理」の構造的対応を、
以下の3つの判定軸で厳密に評価し、JSONのみで返せ。余分なテキスト不要。

## 判定軸（必須評価）

### 1. directionality（方向性）
- Attention: bidirectional / all-to-all（全トークンが全トークンに注目できる）
- Correspondence: higher_to_lower / asymmetric（霊的→自然的の一方向流入）
- これは構造的差異か、それとも視点の違いにすぎないか？

### 2. hierarchy（階層構造）
- Attention heads: parallel within same layer（同一層内で並列処理）
- Correspondence layers: vertical ontological hierarchy（存在論的な縦の階層）
- Transformerの「層の深さ」は Swedenborg の「霊的世界の高さ」と対応するか？

### 3. reduction_risk（還元リスク）
- Correspondenceを「計算的重み付け」に還元することは、概念の格下げか？
- softmax の確率分布は「愛の秩序」の数学的アナログか、それとも別物か？

## 各コンポーネントの写像

Q（Query）、K（Key）、V（Value）、softmax正規化、出力集約の5つについて、
最も近い Swedenborg 概念への写像を評価せよ。

## 出力 JSON

{
  "component_mappings": [
    {
      "attention_component": "Query | Key | Value | softmax | output",
      "swedenborg_analog": "<最も近い概念>",
      "confidence": "low|medium|high",
      "explanation": "<根拠50文字以内>",
      "counter_evidence": "<なぜこの写像が不完全か30文字以内>"
    }
  ],
  "risk_axes": {
    "directionality": {
      "risk": "high|medium|low",
      "verdict": "structural_difference|surface_similarity|genuine_analog",
      "explanation": "<差異の説明60文字以内>"
    },
    "hierarchy": {
      "risk": "high|medium|low",
      "verdict": "structural_difference|surface_similarity|genuine_analog",
      "explanation": "<差異の説明60文字以内>"
    },
    "reduction_risk": {
      "risk": "high|medium|low",
      "verdict": "reductive|metaphorical|structural",
      "explanation": "<判断根拠60文字以内>"
    }
  },
  "overall_verdict": "no_mapping|weak_analogy|partial_analogy|strong_analogy",
  "candidate_upgrade_condition": "<どの条件が満たされれば candidate 昇格できるか>",
  "structural_isomorphism_score": 0.0,
  "key_asymmetry": "<最も重要な構造的非対称性60文字以内>"
}
"""


def _run_mechanism_mapping(dry_run: bool) -> dict:
    """Q/K/V/softmax → Swedenborg 構造への写像を3軸で厳格評価（Claude API）。"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "verification_task": "mechanism_mapping",
            "status": "unavailable",
            "reason": "ANTHROPIC_API_KEY が設定されていません",
        }

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_MECHANISM_SYSTEM,
        messages=[{"role": "user", "content": _MECHANISM_PROMPT}],
    )
    raw = msg.content[0].text.strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(m.group()) if m else {"error": raw}

    verdict = result.get("overall_verdict", "unknown")
    status: StatusType = (
        "no_matches" if verdict == "no_mapping"
        else "candidate_matches_found"
    )

    return {
        "verification_task": "mechanism_mapping",
        "hypothesis": "hyp-001",
        "status": status,
        **result,
    }


def _format_yaml(data: dict, indent: int = 0) -> str:
    """シンプルなYAML風出力。"""
    lines = []
    pad = "  " * indent
    for k, v in data.items():
        if isinstance(v, list):
            if not v:
                lines.append(f"{pad}{k}: []")
            else:
                lines.append(f"{pad}{k}:")
                for item in v:
                    if isinstance(item, dict):
                        first = True
                        for ik, iv in item.items():
                            prefix = f"{pad}  - " if first else f"{pad}    "
                            if isinstance(iv, str) and "\n" in iv:
                                iv = iv.replace("\n", " ")
                            lines.append(f"{prefix}{ik}: {iv}")
                            first = False
                    else:
                        lines.append(f"{pad}  - {item}")
        elif isinstance(v, dict):
            lines.append(f"{pad}{k}:")
            lines.extend(_format_yaml(v, indent + 1).splitlines())
        else:
            lines.append(f"{pad}{k}: {v}")
    return "\n".join(lines)


TaskType = Literal["textual_comparison", "mechanism_mapping"]
ModeType = Literal["exploration", "falsification"]

_INTERPRETATION_NOTE = {
    "falsification": (
        "Correspondence matches are exploratory observations, not confirmation of the hypothesis. "
        "Some matches (e.g. influx asymmetry) may serve as counter-evidence."
    ),
    "exploration": (
        "Candidate matches extracted for further investigation. No adoption decision made."
    ),
}


def _build_observation_md(
    result: dict,
    hypothesis_id: str,
    task: TaskType,
    mode: ModeType,
) -> str:
    from datetime import date

    fm_lines = [
        "---",
        f"id: obs-001",
        f"date: {date.today()}",
        f"source: research_os/verify",
        f"status: observation",
        f"source_hypothesis: {hypothesis_id}",
        f"task: {task}",
        f"mode: {mode}",
        f"evidence_level: exploratory",
        f"adoption_status: not_adopted",
        f'interpretation_note: "{_INTERPRETATION_NOTE[mode]}"',
        "---",
    ]

    body_lines = [
        f"# 観察: {task} ({mode}モード)",
        "",
        f"仮説 `{hypothesis_id}` に対して `{task}` を `{mode}` モードで実行した結果。",
        "採択はしない。観察記録として保存する。",
        "",
        "## 結果",
        "",
    ]

    matches = result.get("matches", [])
    if matches:
        body_lines.append(f"候補マッチ数: {len(matches)}")
        body_lines.append("")
        for m in matches:
            conf = m.get("confidence", "?")
            conf_mark = {"high": "★★★", "medium": "★★☆", "low": "★☆☆"}.get(conf, conf)
            body_lines += [
                f"### {conf_mark} {m.get('swedenborg_term')} ← {m.get('attention_concept')}",
                f"- spiritual: {m.get('spiritual')}",
                f"- reason: {m.get('reason')}",
                f"- ref: {m.get('reference')}",
                "",
            ]

    body_lines += [
        "## 解釈上の注意",
        "",
        _INTERPRETATION_NOTE[mode],
        "",
        "### influx系エントリについて",
        "光・水・風の「高次→低次への伝達」は相応側の方向性の非対称性を示しており、",
        "双方向的な Attention 機構との差異として反証材料になり得る。",
    ]

    return "\n".join(fm_lines) + "\n\n" + "\n".join(body_lines)


def verify_hypothesis(
    file: Path,
    task: TaskType,
    source: str = "biblical_correspondence",
    mode: ModeType = "exploration",
    dry_run: bool = False,
    out: Path | None = None,
) -> None:
    if not file.exists():
        print(f"エラー: ファイルが見つかりません: {file}", file=sys.stderr)
        sys.exit(1)

    # 仮説IDを front-matter から取得
    text = file.read_text(encoding="utf-8")
    hypothesis_id = file.stem  # fallback
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                if line.startswith("id:"):
                    hypothesis_id = line.partition(":")[2].strip()

    if task == "textual_comparison":
        result = _run_textual_comparison(dry_run)
    elif task == "mechanism_mapping":
        result = _run_mechanism_mapping(dry_run)
    else:
        print(f"エラー: 未知のタスク: {task}", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        result["dry_run"] = True
        print(_format_yaml(result))
        return

    # 保存先が指定されている場合は observation Markdown として書き出す
    if out:
        obs_md = _build_observation_md(result, hypothesis_id, task, mode)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(obs_md, encoding="utf-8")
        print(f"観察記録を保存: {out}")
        print(f"adoption_status: not_adopted")
    else:
        print(_format_yaml(result))
