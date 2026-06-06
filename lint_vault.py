#!/usr/bin/env python3
"""
lint_vault.py — Biblical Correspondence Dictionary Vault 構造監査ツール

使い方:
    python lint_vault.py [vault_root]

vault_root を省略するとカレントディレクトリをVaultルートとして使用します。
終了コード: 問題あり=1 / 問題なし=0
"""

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

PLACEHOLDERS = {
    "", "未記入", "後で", "要記入", "（後で）", "(後で)",
}

# TODO / TBD は大文字小文字を無視して未記入扱い（is_empty_or_placeholder 内で処理）

AUXILIARY_SOURCES = {
    "解釈者由来", "AI対話由来", "複数AI一致由来", "複数AI一致",
    "比喩・類似由来", "語感・形状由来",
}

CLAIM_TYPE_VOCAB = {
    "fact", "hypothesis", "metaphor", "interpretation", "application", "mixed",
}

# ファイル名の大文字小文字を問わず除外（テンプレート・スキーマ）
EXCLUDED_FILENAMES = {
    "lint-rules.md",
    "confirmed-template.md",
    "provisional-template.md",
    "candidates-template.md",
    "adoption-gate.md",
    "ingest-rules.md",
    "parallax.md",
}

# ---------------------------------------------------------------------------
# フロントマター解析（インラインリスト形式のみ対応）
# ---------------------------------------------------------------------------

def detect_multiline_connection_source(content: str, path: Path) -> list[str]:
    """フロントマター内で複数行リスト形式の connection-source を検出してエラーを返す。

    例（エラー対象）:
        connection-source:
          - 本文文脈由来
          - AI対話由来
    """
    issues: list[str] = []
    if not content.startswith("---"):
        return issues
    end = content.find("---", 3)
    if end == -1:
        return issues
    fm_block = content[3:end]
    lines = fm_block.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "connection-source:" or stripped.startswith("connection-source: ") and not stripped[len("connection-source:"):].strip().startswith("["):
            # 次の行が "  - " で始まるなら複数行リスト
            if i + 1 < len(lines) and re.match(r"^\s+-\s+", lines[i + 1]):
                issues.append(
                    f"[R-02 🔴 Error] {path}: connection-source が複数行リスト形式です。"
                    " インラインリスト形式で記述してください。"
                    " 例: connection-source: [本文文脈由来, AI対話由来]"
                )
    return issues


def parse_frontmatter(content: str) -> dict:
    """YAMLフロントマターを簡易パースする。
    connection-source は [a, b, c] 形式（インライン）のみ解析対象。
    複数行リストは detect_multiline_connection_source で別途エラーとして検出する。
    """
    fm: dict = {}
    if not content.startswith("---"):
        return fm
    end = content.find("---", 3)
    if end == -1:
        return fm
    for line in content[3:end].splitlines():
        if ":" not in line:
            continue
        key, _, raw_val = line.partition(":")
        key = key.strip()
        val = raw_val.strip()
        if val.startswith("[") and val.endswith("]"):
            fm[key] = [v.strip() for v in val[1:-1].split(",") if v.strip()]
        else:
            fm[key] = val
    return fm

# ---------------------------------------------------------------------------
# 確認来歴フィールド取得・空欄判定
# ---------------------------------------------------------------------------

def get_history_field_value(section: str, field: str):
    """確認来歴セクションから指定フィールドの値を返す。見つからなければ None。

    以下の2形式に対応する:
    - テーブル行:       | 確認者 | 山田太郎 |
    - インデント付きリスト:     - **確認者**: 山田太郎
    """
    escaped = re.escape(field)
    # テーブル形式
    m = re.search(rf"^\|\s*{escaped}\s*\|\s*(.*?)\s*\|", section, re.MULTILINE)
    if m:
        return m.group(1).strip()
    # インデント付きリスト形式: ^\s*-\s*\*\*field\*\*:\s*(.*)$
    m = re.search(rf"^\s*-\s*\*\*{escaped}\*\*:\s*(.*)$", section, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def is_empty_or_placeholder(value) -> bool:
    if value is None:
        return True
    normalized = value.strip().strip("。").strip("（").strip("）").strip()
    if normalized.upper() in {"TODO", "TBD"}:
        return True
    return normalized in PLACEHOLDERS


_STRONGS_RE = re.compile(r"^[HG]\d+$")


def check_strongs_format(path: Path, fm: dict) -> list[str]:
    """S-01: strongs フィールドの各要素が [HG]\\d+ 形式かを検査する。"""
    issues: list[str] = []
    strongs = fm.get("strongs")
    if strongs is None:
        return issues
    if isinstance(strongs, str):
        issues.append(
            f"[S-01 🟡 要確認] {path}: strongs がスカラーです。"
            " インラインリスト形式で記述してください。例: strongs: [H3045, H7069]"
        )
        return issues
    if isinstance(strongs, list):
        bad = [v for v in strongs if not _STRONGS_RE.match(str(v))]
        if bad:
            issues.append(
                f"[S-01 🟡 要確認] {path}: strongs の値 {bad} が [HG]\\d+ 形式ではありません。"
                " 例: H3045, G25"
            )
    return issues

# ---------------------------------------------------------------------------
# チェック関数
# ---------------------------------------------------------------------------

def check_candidates(path: Path, content: str, fm: dict) -> list[str]:
    issues: list[str] = []

    # R-02: 複数行 YAML リスト形式の検出
    issues += detect_multiline_connection_source(content, path)

    # S-01: strongs フォーマット検証
    issues += check_strongs_format(path, fm)

    sources = fm.get("connection-source", [])

    # V-02: connection-source がスカラー（配列でない）
    if isinstance(sources, str):
        issues.append(
            f"[V-02 🔴 要注意] {path}: connection-source がスカラー値です"
            f"（'{sources}'）。[...] 形式の配列で記述してください。"
        )
        sources = []  # 以降のチェックをスキップしない

    # V-01: connection-source に claim-type 語彙が混入
    if isinstance(sources, list):
        bad = [s for s in sources if s.lower() in CLAIM_TYPE_VOCAB]
        if bad:
            issues.append(
                f"[V-01 🔴 要注意] {path}: connection-source に claim-type の語彙"
                f" {bad} が混入しています。connection-source には日本語8類型を使用してください。"
            )

    # C-01: 複数AI一致由来のみ
    if isinstance(sources, list) and sources:
        if all(s in {"複数AI一致由来", "複数AI一致"} for s in sources):
            issues.append(
                f"[C-01 🔴 要注意] {path}: connection-source が「複数AI一致由来」のみです。"
            )

    # C-02: raw/ 参照なし
    if "raw/" not in content:
        issues.append(f"[C-02 🟡 要確認] {path}: raw/ への参照がありません。")

    # C-03: 解釈者由来・AI対話由来で raw 参照なし
    if isinstance(sources, list):
        if "解釈者由来" in sources and "raw/swedenborg/" not in content:
            issues.append(
                f"[C-03 🔴 要注意] {path}: 解釈者由来ですが raw/swedenborg/ への参照がありません。"
            )
        if "AI対話由来" in sources and "raw/ai-dialogues/" not in content:
            issues.append(
                f"[C-03 🔴 要注意] {path}: AI対話由来ですが raw/ai-dialogues/ への参照がありません。"
            )

    # C-04: ラベルと raw 参照パスの不整合
    if isinstance(sources, list):
        if "本文文脈由来" in sources and "raw/scripture/" not in content:
            issues.append(
                f"[C-04 🟡 要確認] {path}: 本文文脈由来ですが raw/scripture/ への参照がありません。"
            )
        if "原語由来" in sources and "raw/strongs/" not in content:
            issues.append(
                f"[C-04 🟡 要確認] {path}: 原語由来ですが raw/strongs/ への参照がありません。"
            )
        if "現場経験由来" in sources and "raw/field-notes/" not in content:
            issues.append(
                f"[C-04 🟡 要確認] {path}: 現場経験由来ですが raw/field-notes/ への参照がありません。"
            )

    # C-05: 本文文脈由来 + swedenborg 混在
    if isinstance(sources, list):
        if "本文文脈由来" in sources and "raw/swedenborg/" in content:
            issues.append(
                f"[C-05 🟡 要確認] {path}: 本文文脈由来と解釈者資料（raw/swedenborg/）が混在しています。"
            )

    # M-01: claim-type=fact + 補助資料源を「含む」
    claim_type = fm.get("claim-type", "")
    if claim_type == "fact" and isinstance(sources, list):
        aux_present = [s for s in sources if s in AUXILIARY_SOURCES]
        if aux_present:
            issues.append(
                f"[M-01 🟡 要確認] {path}: claim-type=fact ですが補助資料源"
                f" {aux_present} が含まれています。確認来歴で根拠の扱いを明記してください。"
            )

    return issues


def _check_history_fields(path: Path, content: str, fm: dict, required_fields: list[str]) -> list[str]:
    """確認来歴テーブルの必須フィールド空欄チェック（共通）"""
    issues: list[str] = []
    if "確認来歴" not in content:
        issues.append(f"[P-01 🔴 要注意] {path}: 「確認来歴」セクションがありません。")
        return issues

    m = re.search(r"## 確認来歴(.+?)(?=\n## |\Z)", content, re.DOTALL)
    if not m:
        return issues
    history_section = m.group(1)

    for field in required_fields:
        value = get_history_field_value(history_section, field)
        if is_empty_or_placeholder(value):
            issues.append(
                f"[P-02 🔴 要注意] {path}: 確認来歴の「{field}」が未記入またはプレースホルダーです。"
            )
    return issues


HISTORY_REQUIRED = [
    "確認者",
    "確認日時",
    "AIを経由しない直接確認の種類",
    "確認の対象は何か",
]


def check_provisional(path: Path, content: str, fm: dict) -> list[str]:
    issues: list[str] = []
    issues += _check_history_fields(path, content, fm, HISTORY_REQUIRED)
    issues += check_candidates(path, content, fm)
    return issues


def check_confirmed(path: Path, content: str, fm: dict) -> list[str]:
    issues: list[str] = []
    issues += _check_history_fields(path, content, fm, HISTORY_REQUIRED)

    # P-03: 再検証ログ
    if "再検証ログ" not in content:
        issues.append(f"[P-03 🔴 要注意] {path}: 「再検証ログ」セクションがありません。")
    else:
        m = re.search(r"## 再検証ログ(.+?)(?=\n## |\Z)", content, re.DOTALL)
        if m and not m.group(1).strip():
            issues.append(f"[P-03 🔴 要注意] {path}: 再検証ログが空です。")

    # hypothesis / interpretation + confirmed → 確認対象欄を厳しくチェック
    claim_type = fm.get("claim-type", "")
    if claim_type in {"hypothesis", "interpretation"}:
        m = re.search(r"## 確認来歴(.+?)(?=\n## |\Z)", content, re.DOTALL)
        if m:
            target = get_history_field_value(m.group(1), "確認の対象は何か")
            if is_empty_or_placeholder(target):
                issues.append(
                    f"[P-02 🔴 要注意] {path}: claim-type={claim_type} かつ"
                    " fact-status=confirmed ですが「確認の対象は何か」が未記入です。"
                    " 何が confirmed なのか（confirmed hypothesis / interpretation として"
                    " 保存する理由、適用限界など）を明記してください。"
                )

    issues += check_candidates(path, content, fm)
    return issues

# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def lint_vault(vault_root: Path) -> int:
    all_issues: list[str] = []

    checks = [
        (vault_root / "wiki" / "candidates",              check_candidates),
        (vault_root / "wiki" / "verified" / "provisional", check_provisional),
        (vault_root / "wiki" / "verified" / "confirmed",   check_confirmed),
    ]

    for directory, checker in checks:
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.md")):
            if path.name.lower() in EXCLUDED_FILENAMES:
                continue
            content = path.read_text(encoding="utf-8")
            fm = parse_frontmatter(content)
            all_issues += checker(path, content, fm)

    if all_issues:
        for issue in all_issues:
            print(issue)
        return 1

    print("✓ lint passed — 問題は検出されませんでした。")
    return 0


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    sys.exit(lint_vault(root))
