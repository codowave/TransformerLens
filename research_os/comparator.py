"""
複数AI（Claude/GPT/Gemini/Grok）の応答を比較分析する。

ai-comparisons/ 内のファイル形式:
---
question: 比較する質問
---
## Claude
応答テキスト

## GPT
応答テキスト

## Gemini
応答テキスト
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import anthropic

_COMPARE_SYSTEM = """\
あなたは複数のAIシステムの応答を中立的に比較分析する専門家です。
どのAIが「正しい」かを決めるのではなく、各応答の構造的特徴を記述してください。"""

_COMPARE_PROMPT = """\
以下の質問に対する複数AIの応答を比較し、JSONのみで返せ。

評価観点:
- core_claim: 主張の核心（1文）
- evidence_type: 根拠の種類（実験的/論理的/権威引用/なし）
- novelty: 新規性（genuine/rephrasing/none）
- hidden_assumption: 危険な前提・隠れた仮定（あれば記述）
- quality: high|medium|low

出力JSON:
{
  "question": "<元の質問>",
  "comparison": {
    "<AI名>": {
      "core_claim": "...",
      "evidence_type": "...",
      "novelty": "...",
      "hidden_assumption": "...",
      "quality": "..."
    }
  },
  "synthesis": "<各AI応答の総合的所見100文字以内>",
  "recommended_followup": "<次に問うべき問い>"
}

比較対象:
"""


def _parse_comparison_file(text: str) -> tuple[str, dict[str, str]]:
    """front-matter から質問を、## AI名 セクションから応答を抽出する。"""
    question = ""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            fm_block = text[3:end]
            for line in fm_block.splitlines():
                if line.startswith("question:"):
                    question = line.partition(":")[2].strip()
            text = text[end + 3:].strip()

    responses: dict[str, str] = {}
    sections = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    for i in range(1, len(sections), 2):
        ai_name = sections[i].strip()
        content = sections[i + 1].strip() if i + 1 < len(sections) else ""
        if content:
            responses[ai_name] = content

    return question, responses


def _format_comparison_table(result: dict) -> str:
    comparison = result.get("comparison", {})
    ai_names = list(comparison.keys())

    lines = [
        "# AI比較分析",
        f"質問: {result.get('question', '?')}",
        "",
    ]

    if ai_names:
        header = "| 観点 | " + " | ".join(ai_names) + " |"
        sep = "|------|" + "|------|" * len(ai_names)
        lines += [header, sep]
        for col_key, col_label in [
            ("core_claim", "主張の核心"),
            ("evidence_type", "根拠の種類"),
            ("novelty", "新規性"),
            ("hidden_assumption", "危険な前提"),
            ("quality", "品質"),
        ]:
            row = f"| {col_label} |"
            for ai in ai_names:
                val = comparison.get(ai, {}).get(col_key, "-")
                row += f" {val} |"
            lines.append(row)

    lines += [
        "",
        f"**総合所見**: {result.get('synthesis', '')}",
        f"**次の問い**: {result.get('recommended_followup', '')}",
    ]
    return "\n".join(lines)


def compare_ai_responses(file: Path, out: Path | None = None) -> None:
    if not file.exists():
        print(f"エラー: ファイルが見つかりません: {file}", file=sys.stderr)
        sys.exit(1)

    text = file.read_text(encoding="utf-8")
    question, responses = _parse_comparison_file(text)

    if not responses:
        print("エラー: 比較する応答が見つかりません。## AI名 形式で応答を追加してください。",
              file=sys.stderr)
        sys.exit(1)

    content = f"質問: {question}\n\n"
    for ai_name, response in responses.items():
        content += f"[{ai_name}の応答]\n{response}\n\n"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("エラー: ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=_COMPARE_SYSTEM,
        messages=[{"role": "user", "content": _COMPARE_PROMPT + content}],
    )
    raw = msg.content[0].text.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            print(f"比較失敗: 予期しない応答:\n{raw}", file=sys.stderr)
            sys.exit(1)
        result = json.loads(m.group())

    result["question"] = question or result.get("question", "?")
    report = _format_comparison_table(result)

    if out:
        out.write_text(report, encoding="utf-8")
        print(f"比較レポート書き込み完了: {out}")
    else:
        print(report)
