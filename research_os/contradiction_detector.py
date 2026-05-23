"""
research/ 配下の複数ディレクトリを横断して矛盾する主張のペアを検出する。
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import anthropic

_DETECT_SYSTEM = """\
あなたは論理的整合性の監査官です。研究ノートのリストを読み、
互いに矛盾する主張のペアを特定してください。感情的な評価は不要です。"""

_DETECT_PROMPT = """\
以下の研究ノートリストを読み、矛盾ペアをJSONのみで返せ。余分なテキスト不要。

矛盾の定義: 一方が真なら他方が偽にならざるを得ない主張のペア。
（視点の違い・補完関係は矛盾ではない）

出力JSON:
{
  "contradictions": [
    {
      "entry_a": "<ファイル名>",
      "claim_a": "<主張の要約>",
      "entry_b": "<ファイル名>",
      "claim_b": "<主張の要約>",
      "severity": "low|medium|high",
      "explanation": "<矛盾の説明50文字以内>"
    }
  ],
  "total_entries_checked": <数>,
  "contradiction_count": <数>
}

研究ノートリスト:
"""


def _load_entries(dirs: list[Path]) -> list[dict]:
    entries = []
    for d in dirs:
        if not d.exists():
            continue
        for md in sorted(d.glob("*.md")):
            if md.name == ".gitkeep":
                continue
            text = md.read_text(encoding="utf-8")
            entries.append({"file": md.name, "dir": d.name, "content": text[:800]})
    return entries


def _format_report(result: dict) -> str:
    lines = [
        "# 矛盾検出レポート",
        f"検査エントリ数: {result.get('total_entries_checked', 0)}",
        f"矛盾ペア数: {result.get('contradiction_count', 0)}",
        "",
    ]
    contradictions = result.get("contradictions", [])
    if not contradictions:
        lines.append("矛盾なし — 検査したエントリ間に論理的矛盾は見つかりませんでした。")
    else:
        for i, c in enumerate(contradictions, 1):
            sev_icon = {"low": "⚠", "medium": "⚠⚠", "high": "🔴"}.get(c.get("severity", ""), "")
            lines += [
                f"## {i}. {sev_icon} [{c.get('severity', '?').upper()}]",
                f"**{c.get('entry_a')}**: {c.get('claim_a')}",
                f"**{c.get('entry_b')}**: {c.get('claim_b')}",
                f"→ {c.get('explanation')}",
                "",
            ]
    return "\n".join(lines)


def detect_contradictions(dirs: list[Path], out: Path | None = None) -> None:
    entries = _load_entries(dirs)
    if len(entries) < 2:
        print("矛盾検出には2つ以上のエントリが必要です。")
        return

    entries_text = "\n\n".join(
        f"[{e['dir']}/{e['file']}]\n{e['content']}" for e in entries
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("エラー: ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_DETECT_SYSTEM,
        messages=[{"role": "user", "content": _DETECT_PROMPT + entries_text}],
    )
    raw = msg.content[0].text.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            print(f"検出失敗: 予期しない応答:\n{raw}", file=sys.stderr)
            sys.exit(1)
        result = json.loads(m.group())

    result["total_entries_checked"] = len(entries)
    report = _format_report(result)

    if out:
        out.write_text(report, encoding="utf-8")
        print(f"矛盾レポート書き込み完了: {out}")
    else:
        print(report)

    # 矛盾が検出された場合、contradictions/ に自動保存
    if result.get("contradictions") and not out:
        from datetime import date
        auto_out = Path("research/contradictions") / f"detected-{date.today()}.md"
        auto_out.write_text(report, encoding="utf-8")
        print(f"自動保存: {auto_out}")
