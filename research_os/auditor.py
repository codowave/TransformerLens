"""
AI生成コンテンツの品質監査。
6つの欠陥カテゴリをClaude APIで検出し、構造化レポートを返す。
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import anthropic

_AUDIT_SYSTEM = """\
あなたは批判的思考の専門家で、AIが生成したテキストの論理的欠陥を検出する監査官です。
感情や好意を排除し、構造的な問題のみを報告してください。
褒めたり励ましたりしないでください。欠陥がなければ「欠陥なし」と報告してください。"""

_AUDIT_PROMPT = """\
以下のテキストを監査し、JSON形式のみで結果を返せ。余分なテキスト不要。

検出項目（各項目: found=true/false, severity=low/medium/high, evidence=該当箇所の引用）:

1. logical_leap: 論理飛躍（結論が前提から導けない）
2. circular_reasoning: 再帰的自己正当化（AだからA）
3. rhetorical_disguise: 美しいだけの文章（言い換えによる新規性の偽装）
4. missing_evidence: 根拠欠落（assertionに出典・実験・観察なし）
5. over_personification: 過剰人格化（AIが感情・記憶・経験を主張）
6. consistency_drift: 長期整合性崩壊（内部で前後矛盾）

出力JSON:
{
  "source": "<出所>",
  "audited_at": "<ISO日時>",
  "overall_quality": "high|medium|low|critical",
  "defects": {
    "logical_leap": {"found": bool, "severity": "...", "evidence": "..."},
    "circular_reasoning": {"found": bool, "severity": "...", "evidence": "..."},
    "rhetorical_disguise": {"found": bool, "severity": "...", "evidence": "..."},
    "missing_evidence": {"found": bool, "severity": "...", "evidence": "..."},
    "over_personification": {"found": bool, "severity": "...", "evidence": "..."},
    "consistency_drift": {"found": bool, "severity": "...", "evidence": "..."}
  },
  "summary": "<総評100文字以内>"
}

監査対象テキスト:
"""

_SEVERITY_ICON = {"low": "⚠", "medium": "⚠⚠", "high": "🔴", None: ""}
_QUALITY_ICON = {"high": "✓", "medium": "△", "low": "✗", "critical": "✗✗"}


def _format_report(result: dict) -> str:
    lines = [
        f"# 監査レポート",
        f"出所: {result.get('source', '?')}",
        f"日時: {result.get('audited_at', '?')}",
        f"総合品質: {_QUALITY_ICON.get(result.get('overall_quality'), '')} {result.get('overall_quality', '?').upper()}",
        "",
        "## 検出欠陥",
    ]
    defects = result.get("defects", {})
    found_any = False
    for key, label in [
        ("logical_leap", "論理飛躍"),
        ("circular_reasoning", "再帰的自己正当化"),
        ("rhetorical_disguise", "新規性の偽装"),
        ("missing_evidence", "根拠欠落"),
        ("over_personification", "過剰人格化"),
        ("consistency_drift", "整合性崩壊"),
    ]:
        d = defects.get(key, {})
        if d.get("found"):
            found_any = True
            sev = d.get("severity")
            evidence = d.get("evidence", "")
            lines.append(f"### {_SEVERITY_ICON.get(sev, '')} {label} [{sev}]")
            if evidence:
                lines.append(f"> {evidence}")
            lines.append("")
    if not found_any:
        lines.append("欠陥なし — テキストは構造的に健全です。")
    lines += ["", "## 総評", result.get("summary", "")]
    return "\n".join(lines)


def audit_file(file: Path, source: str = "unknown", out: Path | None = None) -> None:
    if not file.exists():
        print(f"エラー: ファイルが見つかりません: {file}", file=sys.stderr)
        sys.exit(1)

    text = file.read_text(encoding="utf-8")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("エラー: ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=_AUDIT_SYSTEM,
        messages=[{"role": "user", "content": _AUDIT_PROMPT + text}],
    )
    raw = msg.content[0].text.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            print(f"監査失敗: 予期しない応答:\n{raw}", file=sys.stderr)
            sys.exit(1)
        result = json.loads(m.group())

    result["source"] = source
    result["audited_at"] = datetime.now().isoformat(timespec="seconds")

    report = _format_report(result)

    if out:
        out.write_text(report, encoding="utf-8")
        print(f"監査レポート書き込み完了: {out}")
    else:
        print(report)
