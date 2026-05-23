"""
python -m research_os <subcommand> [args]
"""

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="research_os",
        description="AI Research OS — 状態・記憶・監査の運用系",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # classify
    p_cls = sub.add_parser("classify", help="inboxのノートを分類・front-matter付与して移動")
    p_cls.add_argument("file", type=Path, help="対象ファイル（.md）")
    p_cls.add_argument("--source", default="human",
                       choices=["human", "claude", "gpt", "gemini", "grok"],
                       help="コンテンツの出所")
    p_cls.add_argument("--dry-run", action="store_true", help="移動せず分類結果だけ表示")

    # audit
    p_aud = sub.add_parser("audit", help="AI生成コンテンツの品質監査")
    p_aud.add_argument("file", type=Path, help="監査対象ファイル")
    p_aud.add_argument("--source", default="unknown",
                       choices=["human", "claude", "gpt", "gemini", "grok", "unknown"],
                       help="コンテンツの出所")
    p_aud.add_argument("--out", type=Path, default=None,
                       help="監査レポート出力先（省略時: stdout）")

    # contradict
    p_con = sub.add_parser("contradict", help="ディレクトリ横断の矛盾検出")
    p_con.add_argument("dirs", nargs="*", type=Path,
                       help="検索対象ディレクトリ（省略時: research/全体）")
    p_con.add_argument("--out", type=Path, default=None,
                       help="矛盾レポート出力先")

    # compare
    p_cmp = sub.add_parser("compare", help="複数AI応答の比較分析")
    p_cmp.add_argument("file", type=Path, help="比較ファイル（ai-comparisons/内の.md）")
    p_cmp.add_argument("--out", type=Path, default=None,
                       help="比較表出力先")

    # timeline
    p_tl = sub.add_parser("timeline", help="時系列整合サマリー生成")
    p_tl.add_argument("--out", type=Path, default=None,
                       help="タイムライン出力先")

    # glossary
    p_gl = sub.add_parser("glossary", help="用語辞典の自動生成・更新")
    p_gl.add_argument("--out", type=Path, default=None,
                       help="辞典出力先（省略時: research/glossary/）")

    # verify
    p_vfy = sub.add_parser("verify", help="仮説の検証タスクを実行")
    p_vfy.add_argument("file", type=Path, help="検証対象仮説ファイル（.md）")
    p_vfy.add_argument("--task",
                        choices=["textual_comparison", "mechanism_mapping"],
                        required=True,
                        help="実行する検証タスク")
    p_vfy.add_argument("--source", default="biblical_correspondence",
                        help="照合ソース（デフォルト: biblical_correspondence）")
    p_vfy.add_argument("--dry-run", action="store_true",
                        help="候補抽出のみ。採択・書き込みなし")
    p_vfy.add_argument("--out", type=Path, default=None,
                        help="結果出力先（--dry-run 時は無視）")

    args = parser.parse_args()

    if args.cmd == "classify":
        from research_os.classifier import classify_file
        classify_file(args.file, source=args.source, dry_run=args.dry_run)

    elif args.cmd == "audit":
        from research_os.auditor import audit_file
        audit_file(args.file, source=args.source, out=args.out)

    elif args.cmd == "contradict":
        from research_os.contradiction_detector import detect_contradictions
        research_root = Path("research")
        dirs = args.dirs if args.dirs else [
            research_root / "hypotheses",
            research_root / "observations",
            research_root / "verified",
        ]
        detect_contradictions(dirs, out=args.out)

    elif args.cmd == "compare":
        from research_os.comparator import compare_ai_responses
        compare_ai_responses(args.file, out=args.out)

    elif args.cmd == "timeline":
        from research_os.timeline_tracker import generate_timeline
        generate_timeline(out=args.out)

    elif args.cmd == "glossary":
        from research_os.glossary_builder import build_glossary
        build_glossary(out=args.out)

    elif args.cmd == "verify":
        from research_os.verifier import verify_hypothesis
        verify_hypothesis(
            args.file,
            task=args.task,
            source=args.source,
            dry_run=args.dry_run,
            out=args.out,
        )


if __name__ == "__main__":
    main()
