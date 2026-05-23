"""
verify.py — `research_os verify` コマンド

仮説ファイル（YAML front-matter 付き .md）を読み込み、
指定タスクで検証を実行して結果を YAML 形式で出力する。
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


def _parse_hypothesis(path: Path) -> dict:
    """YAML front-matter（--- ... ---）を解析する。"""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path}: YAML front-matter が見つからない（--- で始まること）")

    # 2番目の --- を探す
    end = text.index("---", 3)
    front = text[3:end].strip()
    return yaml.safe_load(front)


def _to_yaml(data: dict, indent: int = 0) -> str:
    """dict を人間が読みやすい YAML 文字列に変換する。"""
    return yaml.dump(
        data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        indent=2,
    )


def run_verify(hyp_path: str, task: str, dry_run: bool,
               mode: str = "falsification", focus: str | None = None) -> None:
    path = Path(hyp_path)
    if not path.exists():
        print(f"[ERROR] 仮説ファイルが見つからない: {hyp_path}", file=sys.stderr)
        sys.exit(1)

    try:
        hypothesis = _parse_hypothesis(path)
    except Exception as exc:
        print(f"[ERROR] front-matter 解析失敗: {exc}", file=sys.stderr)
        sys.exit(1)

    hyp_id = hypothesis.get("id", path.stem)
    print(f"# research_os verify — {hyp_id}")
    print(f"# task: {task}  dry_run: {dry_run}")
    print(f"# stage: {hypothesis.get('stage', 'unknown')}")
    print()

    if task == "mechanism_mapping":
        from research_os.tasks.mechanism_mapping import run as mm_run
        try:
            result = mm_run(hypothesis, dry_run=dry_run)
        except NotImplementedError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            sys.exit(1)
        print(_to_yaml(result.to_dict()))

    elif task == "textual_comparison":
        from research_os.tasks.textual_comparison import run as tc_run
        focus_fp = focus or "fp-2"
        try:
            result = tc_run(hypothesis, mode=mode, focus_fp=focus_fp)
        except NotImplementedError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            sys.exit(1)
        print(_to_yaml(result.to_dict()))

    else:
        print(f"[ERROR] 未知のタスク: {task!r}", file=sys.stderr)
        print("利用可能なタスク: mechanism_mapping, textual_comparison, activation_analysis",
              file=sys.stderr)
        sys.exit(1)
