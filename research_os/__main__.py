"""
research_os __main__.py — CLI エントリポイント

使い方:
  python -m research_os verify <hyp_path> --task <task> [--dry-run]

例:
  python -m research_os verify research/hypotheses/hyp-001.md \\
      --task mechanism_mapping --dry-run
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m research_os",
        description="仮説検証オペレーティングシステム",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # verify サブコマンド
    v = sub.add_parser("verify", help="仮説ファイルに対して検証タスクを実行する")
    v.add_argument("hypothesis", help="仮説ファイルのパス（例: research/hypotheses/hyp-001.md）")
    v.add_argument("--task", required=True,
                   choices=["mechanism_mapping", "textual_comparison", "activation_analysis"],
                   help="実行する検証タスク")
    v.add_argument("--dry-run", action="store_true",
                   help="計算を伴う処理をスキップし、静的構造判定のみ実行する")
    v.add_argument("--mode", default="falsification",
                   choices=["falsification", "support"],
                   help="textual_comparison のスキャンモード（default: falsification）")
    v.add_argument("--focus", default=None,
                   help="textual_comparison でフォーカスする failure point ID（例: fp-2）")

    args = parser.parse_args()

    if args.command == "verify":
        from research_os.verify import run_verify
        run_verify(
            args.hypothesis,
            task=args.task,
            dry_run=args.dry_run,
            mode=args.mode,
            focus=args.focus,
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
