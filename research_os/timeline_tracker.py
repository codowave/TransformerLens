"""
research/ 全体のエントリを時系列に並べ、思考の座標変化（phase-transition）を検出する。
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import anthropic

RESEARCH_ROOT = Path("research")

_TIMELINE_SYSTEM = """\
あなたは研究の時系列を分析し、思考の転換点を特定する研究史家です。
価値判断ではなく、立場の変化・視点の移動を客観的に記述してください。"""

_TIMELINE_PROMPT = """\
以下の研究エントリを時系列順に読み、思考の変遷と転換点をJSONのみで返せ。

出力JSON:
{
  "phases": [
    {
      "phase_id": "phase-001",
      "date_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
      "dominant_stance": "この期間の主要な立場・前提",
      "key_entries": ["ファイル名1", "ファイル名2"],
      "transition_trigger": "次のフェーズへの転換をもたらしたエントリまたは出来事"
    }
  ],
  "total_entries": <数>,
  "summary": "<研究全体の方向性と変遷の総評100文字以内>"
}

研究エントリ（時系列順）:
"""


def _load_chronological() -> list[dict]:
    """全エントリを date フィールドで時系列ソート。"""
    entries = []
    for subdir in ["hypotheses", "observations", "verified", "contradictions",
                   "phase-transitions"]:
        d = RESEARCH_ROOT / subdir
        if not d.exists():
            continue
        for md in d.glob("*.md"):
            if md.name == ".gitkeep":
                continue
            text = md.read_text(encoding="utf-8")
            entry_date = ""
            if text.startswith("---"):
                end = text.find("---", 3)
                if end != -1:
                    for line in text[3:end].splitlines():
                        if line.startswith("date:"):
                            entry_date = line.partition(":")[2].strip()
            entries.append({
                "file": f"{subdir}/{md.name}",
                "date": entry_date,
                "content": text[:500],
            })

    entries.sort(key=lambda e: (e["date"] or "9999-99-99"))
    return entries


def _format_timeline(result: dict) -> str:
    lines = [
        "# 時系列整合レポート",
        f"総エントリ数: {result.get('total_entries', 0)}",
        "",
        "## フェーズ遷移",
    ]
    for p in result.get("phases", []):
        dr = p.get("date_range", {})
        lines += [
            f"### {p.get('phase_id')} ({dr.get('start', '?')} 〜 {dr.get('end', '?')})",
            f"**主要立場**: {p.get('dominant_stance', '')}",
            f"**主要エントリ**: {', '.join(p.get('key_entries', []))}",
        ]
        if p.get("transition_trigger"):
            lines.append(f"**転換トリガー**: {p.get('transition_trigger')}")
        lines.append("")
    lines += ["## 総評", result.get("summary", "")]
    return "\n".join(lines)


def generate_timeline(out: Path | None = None) -> None:
    entries = _load_chronological()
    if not entries:
        print("エントリが見つかりません。")
        return

    entries_text = "\n\n".join(
        f"[{e['date'] or '不明'} | {e['file']}]\n{e['content']}" for e in entries
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("エラー: ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_TIMELINE_SYSTEM,
        messages=[{"role": "user", "content": _TIMELINE_PROMPT + entries_text}],
    )
    raw = msg.content[0].text.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            print(f"タイムライン生成失敗:\n{raw}", file=sys.stderr)
            sys.exit(1)
        result = json.loads(m.group())

    result["total_entries"] = len(entries)
    report = _format_timeline(result)

    if out:
        out.write_text(report, encoding="utf-8")
        print(f"タイムライン書き込み完了: {out}")
    else:
        # research/timeline/ に自動保存
        from datetime import date
        auto_out = RESEARCH_ROOT / "timeline" / f"timeline-{date.today()}.md"
        auto_out.write_text(report, encoding="utf-8")
        print(report)
        print(f"\n自動保存: {auto_out}")
