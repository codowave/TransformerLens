"""
inbox のノートを内容に基づいて分類し、YAML front-matter を付与して適切なディレクトリへ移動する。
Claude API を使って分類を行う（ANTHROPIC_API_KEY 必須）。
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import anthropic

RESEARCH_ROOT = Path("research")

STATUS_DIR_MAP = {
    "hypothesis": "hypotheses",
    "observation": "observations",
    "verified": "verified",
    "contradiction": "contradictions",
    "comparison": "ai-comparisons",
    "phase-transition": "phase-transitions",
}

_CLASSIFY_PROMPT = """\
以下の研究ノートを読み、JSON のみで分類結果を返せ。余分なテキストは一切不要。

分類ルール:
- "hypothesis": 検証前の仮説・推測
- "observation": 実験・観察の記録（事実ベース）
- "verified": 複数の根拠で確認済みの知見
- "contradiction": 既存知見との矛盾・反証
- "comparison": 複数AIの応答比較
- "phase-transition": 思考の座標が変わった転換点

出力形式（JSON のみ）:
{
  "status": "<上記のいずれか>",
  "tags": ["タグ1", "タグ2"],
  "summary": "<30文字以内の要約>",
  "confidence": 0.0〜1.0
}

ノート:
"""


def _strip_existing_frontmatter(text: str) -> tuple[dict, str]:
    """既存の YAML front-matter を除去して本文と front-matter dictを返す。"""
    fm: dict = {}
    body = text
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            fm_block = text[3:end].strip()
            body = text[end + 3:].strip()
            for line in fm_block.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    fm[k.strip()] = v.strip()
    return fm, body


def _build_frontmatter(
    existing: dict,
    status: str,
    tags: list[str],
    summary: str,
    source: str,
    entry_id: str,
) -> str:
    fm = {
        "id": existing.get("id", entry_id),
        "date": existing.get("date", str(date.today())),
        "source": existing.get("source", source),
        "status": status,
        "tags": tags,
        "summary": summary,
    }
    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(v)}]")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def _next_id(status: str) -> str:
    prefix = {
        "hypothesis": "hyp",
        "observation": "obs",
        "verified": "ver",
        "contradiction": "con",
        "comparison": "cmp",
        "phase-transition": "pht",
    }.get(status, "unk")
    target_dir = RESEARCH_ROOT / STATUS_DIR_MAP[status]
    existing = list(target_dir.glob(f"{prefix}-*.md"))
    nums = []
    for f in existing:
        m = re.search(r"-(\d+)\.md$", f.name)
        if m:
            nums.append(int(m.group(1)))
    next_num = max(nums, default=0) + 1
    return f"{prefix}-{next_num:03d}"


def classify_file(file: Path, source: str = "human", dry_run: bool = False) -> None:
    if not file.exists():
        print(f"エラー: ファイルが見つかりません: {file}", file=sys.stderr)
        sys.exit(1)

    text = file.read_text(encoding="utf-8")
    existing_fm, body = _strip_existing_frontmatter(text)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("エラー: ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": _CLASSIFY_PROMPT + body}],
    )
    raw = msg.content[0].text.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # JSON ブロックを抽出
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            print(f"分類失敗: 予期しない応答:\n{raw}", file=sys.stderr)
            sys.exit(1)
        result = json.loads(m.group())

    status: str = result.get("status", "hypothesis")
    tags: list[str] = result.get("tags", [])
    summary: str = result.get("summary", "")
    confidence: float = result.get("confidence", 0.0)

    if status not in STATUS_DIR_MAP:
        print(f"警告: 不明なステータス '{status}'、hypothesis として扱います")
        status = "hypothesis"

    entry_id = _next_id(status)
    fm_text = _build_frontmatter(existing_fm, status, tags, summary, source, entry_id)
    new_content = fm_text + "\n\n" + body

    target_dir = RESEARCH_ROOT / STATUS_DIR_MAP[status]
    target_path = target_dir / f"{entry_id}.md"

    print(f"分類結果: {status} (信頼度: {confidence:.0%})")
    print(f"タグ: {', '.join(tags)}")
    print(f"要約: {summary}")
    print(f"移動先: {target_path}")

    if dry_run:
        print("\n--- dry-run: 以下の内容を書き込み予定 ---")
        print(new_content)
        return

    target_path.write_text(new_content, encoding="utf-8")
    file.unlink()
    print(f"完了: {file} → {target_path}")
