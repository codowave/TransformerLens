"""
research/ 全体のエントリから用語を自動抽出し、辞典を生成・更新する。
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import anthropic

RESEARCH_ROOT = Path("research")
GLOSSARY_DIR = RESEARCH_ROOT / "glossary"

_GLOSSARY_SYSTEM = """\
あなたは研究文書から専門用語を抽出し、簡潔な定義を付与する辞典編集者です。"""

_GLOSSARY_PROMPT = """\
以下の研究ノート群から重要な専門用語を抽出し、JSONのみで返せ。

抽出基準:
- 繰り返し登場する概念
- 独自定義が必要な術語
- 文脈によって意味が変わりうる用語

出力JSON:
{
  "terms": [
    {
      "term": "用語名",
      "definition": "定義（50文字以内）",
      "related": ["関連用語1", "関連用語2"],
      "first_seen": "<最初に登場したファイル名>",
      "category": "theoretical|empirical|methodological|other"
    }
  ]
}

研究ノート群:
"""


def _load_all_entries() -> list[dict]:
    entries = []
    for subdir in ["hypotheses", "observations", "verified", "phase-transitions"]:
        d = RESEARCH_ROOT / subdir
        if not d.exists():
            continue
        for md in sorted(d.glob("*.md")):
            if md.name == ".gitkeep":
                continue
            text = md.read_text(encoding="utf-8")
            entries.append({"file": f"{subdir}/{md.name}", "content": text[:600]})
    return entries


def _load_existing_glossary() -> dict:
    gfile = GLOSSARY_DIR / "glossary.json"
    if gfile.exists():
        return json.loads(gfile.read_text(encoding="utf-8"))
    return {"terms": []}


def build_glossary(out: Path | None = None) -> None:
    entries = _load_all_entries()
    if not entries:
        print("エントリが見つかりません。research/ 配下にノートを追加してください。")
        return

    entries_text = "\n\n".join(
        f"[{e['file']}]\n{e['content']}" for e in entries
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("エラー: ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_GLOSSARY_SYSTEM,
        messages=[{"role": "user", "content": _GLOSSARY_PROMPT + entries_text}],
    )
    raw = msg.content[0].text.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            print(f"辞典生成失敗:\n{raw}", file=sys.stderr)
            sys.exit(1)
        result = json.loads(m.group())

    # 既存辞典とマージ
    existing = _load_existing_glossary()
    existing_terms = {t["term"]: t for t in existing.get("terms", [])}
    for new_term in result.get("terms", []):
        existing_terms[new_term["term"]] = new_term
    merged = {"terms": sorted(existing_terms.values(), key=lambda t: t["term"])}

    output_dir = out or GLOSSARY_DIR
    if isinstance(output_dir, Path) and output_dir.suffix == "":
        output_dir.mkdir(parents=True, exist_ok=True)
        json_out = output_dir / "glossary.json"
        md_out = output_dir / "glossary.md"
    else:
        json_out = output_dir
        md_out = output_dir.with_suffix(".md")

    json_out.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdownも生成
    md_lines = ["# 用語辞典", ""]
    for t in merged["terms"]:
        md_lines += [
            f"## {t['term']}",
            f"{t.get('definition', '')}",
            f"- カテゴリ: {t.get('category', '?')}",
            f"- 初出: {t.get('first_seen', '?')}",
        ]
        if t.get("related"):
            md_lines.append(f"- 関連: {', '.join(t['related'])}")
        md_lines.append("")
    md_out.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"用語辞典更新: {len(merged['terms'])} 語")
    print(f"  JSON: {json_out}")
    print(f"  Markdown: {md_out}")
