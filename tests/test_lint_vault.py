"""
tests/test_lint_vault.py — lint_vault.py のテスト標本

テスト分類:
  - 異常系3件 (A/B/C): それぞれ特定エラー・警告が必ず出ること
  - 正常系3件 (D/E/F): 良いノートを誤検出しないこと
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from lint_vault import (
    check_candidates,
    check_confirmed,
    detect_multiline_connection_source,
    parse_frontmatter,
)

# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def issues_for_content(content: str, checker=check_candidates) -> list[str]:
    path = Path("test_file.md")
    fm = parse_frontmatter(content)
    return checker(path, content, fm)


def issue_codes(issues: list[str]) -> list[str]:
    """各 issue 先頭の [CODE] 部分を抽出する。例: '[R-02 🔴 Error]'"""
    codes = []
    for issue in issues:
        m = re.match(r"\[([^\]]+)\]", issue)
        if m:
            codes.append(m.group(1).split()[0])  # "R-02" だけ取り出す
    return codes


# ---------------------------------------------------------------------------
# 異常系
# ---------------------------------------------------------------------------

CASE_A = """\
---
stage: candidates
fact-status: candidate
claim-type: hypothesis
connection-source:
  - 本文文脈由来
  - AI対話由来
---

# テスト候補A

接続テキスト。
"""


def test_A_multiline_yaml_is_error():
    """A: 複数行YAML形式の connection-source は R-02 Error になること"""
    issues = detect_multiline_connection_source(CASE_A, Path("test_A.md"))
    assert len(issues) == 1, f"Expected 1 R-02 error, got: {issues}"
    assert "R-02" in issues[0]
    assert "インラインリスト" in issues[0]


CASE_B = """\
---
stage: candidates
fact-status: candidate
claim-type: fact
connection-source: [本文文脈由来, AI対話由来]
---

# テスト候補B

raw/scripture/genesis/001.md の接続。
raw/ai-dialogues/2026-05-30-claude-genesis.md も参照。
"""


def test_B_fact_with_auxiliary_source_is_warning():
    """B: claim-type=fact に AI対話由来（補助資料源）が含まれると M-01 要確認が出ること。
    raw 参照は揃えているので C-03 は出ない。M-01 のみが出ること。
    """
    issues = issues_for_content(CASE_B)
    codes = issue_codes(issues)
    assert "M-01" in codes, f"Expected M-01 warning, got: {issues}"
    non_m01_red = [i for i in issues if "🔴" in i and "M-01" not in i]
    assert non_m01_red == [], f"Unexpected 🔴 errors other than M-01: {non_m01_red}"


CASE_C = """\
---
stage: confirmed
fact-status: confirmed
claim-type: hypothesis
connection-source: [原語由来]
---

# テスト候補C

## 確認来歴

- **内容そのもの**:
- **仮説としての位置づけ**:
- **解釈としての位置づけ**:
- **適用可能性**:
"""


def test_C_confirmed_hypothesis_with_empty_history_fields():
    """C: claim-type=hypothesis + fact-status=confirmed で確認来歴フィールドが空のとき P-02 エラーが出ること"""
    issues = issues_for_content(CASE_C, checker=check_confirmed)
    codes = issue_codes(issues)
    assert "P-02" in codes, f"Expected P-02 error for empty history fields, got: {issues}"
    # 「確認の対象は何か」未記入の強化メッセージが含まれること
    assert any("何が confirmed" in i for i in issues), (
        f"Expected 'confirmed hypothesis' specific message, got: {issues}"
    )


# ---------------------------------------------------------------------------
# 正常系（良いノートを落とさないか）
# ---------------------------------------------------------------------------

CASE_D = """\
---
stage: candidates
fact-status: candidate
claim-type: hypothesis
connection-source: [原語由来, 本文文脈由来]
---

# 正常候補D

raw/strongs/H3045.md と raw/scripture/genesis/004.md を参照した接続。
"""


def test_D_clean_candidate_no_issues():
    """D: 適切な candidates ファイルは issue なし"""
    issues = issues_for_content(CASE_D)
    assert issues == [], f"Expected no issues, got: {issues}"


CASE_E = """\
---
stage: candidates
fact-status: candidate
claim-type: interpretation
connection-source: [解釈者由来]
---

# 正常候補E（解釈者由来 × interpretation）

raw/swedenborg/ac/1234.md に基づく解釈候補。
"""


def test_E_interpreter_source_with_interpretation_no_spurious_warning():
    """E: connection-source=[解釈者由来] + claim-type=interpretation は M-01 を出さない（claim-type が fact でないため）"""
    issues = issues_for_content(CASE_E)
    m01_issues = [i for i in issues if "M-01" in i]
    assert m01_issues == [], f"Expected no M-01 for non-fact claim-type, got: {m01_issues}"


CASE_F = """\
---
stage: candidates
fact-status: candidate
claim-type: metaphor
connection-source: [本文文脈由来]
---

# 正常候補F（本文文脈由来 × metaphor）

raw/scripture/isaiah/055.md の本文から見いだした比喩的接続。
"""


def test_F_scripture_source_with_metaphor_no_issues():
    """F: connection-source=[本文文脈由来] + claim-type=metaphor は issue なし"""
    issues = issues_for_content(CASE_F)
    assert issues == [], f"Expected no issues, got: {issues}"


# ---------------------------------------------------------------------------
# 境界正常系（鳴りそうで鳴ってはいけない）
# ---------------------------------------------------------------------------

CASE_G = """\
---
stage: confirmed
fact-status: confirmed
claim-type: hypothesis
connection-source: [原語由来]
---

# テストG（confirmed hypothesis — 入れ子リスト形式、正しく記入済み）

raw/strongs/H3045.md への参照。

## 確認来歴

    - **確認者**: 山田太郎
    - **確認日時**: 2026-06-01
    - **AIを経由しない直接確認の種類**: 原語辞典（BDB）の直接参照
    - **確認の対象は何か**: 仮説としての位置づけ（BDDでの語義幅がこの仮説を支持することを確認）

## 再検証ログ

再検証 #1 実施: 2026-06-15 / 結果: 支持 / 矛盾: なし
"""


def test_G_confirmed_hypothesis_with_nested_list_history_no_error():
    """G: claim-type=hypothesis + confirmed、確認来歴が入れ子リスト形式で正しく記入済み → Error なし
    get_history_field_value がインデント付きリスト形式を正しく拾うことを確認する。
    """
    issues = issues_for_content(CASE_G, checker=check_confirmed)
    p02_issues = [i for i in issues if "P-02" in i]
    assert p02_issues == [], (
        f"Expected no P-02 errors for properly filled nested list history, got: {p02_issues}"
    )


CASE_H = """\
---
stage: confirmed
fact-status: confirmed
claim-type: hypothesis
connection-source: [原語由来]
---

# テストH（confirmed hypothesis — 「確認の対象は何か」が N/A）

raw/strongs/H3045.md への参照。

## 確認来歴

    - **確認者**: 山田太郎
    - **確認日時**: 2026-06-01
    - **AIを経由しない直接確認の種類**: 原語辞典（BDB）の直接参照
    - **確認の対象は何か**: N/A（この接続に適用可能性は該当しないと判断）

## 再検証ログ

再検証 #1 実施: 2026-06-15 / 結果: 支持 / 矛盾: なし
"""


def test_H_na_in_confirmation_target_is_not_empty_error():
    """H: 「確認の対象は何か」の値が N/A のとき P-02 未記入エラーにならないこと。
    N/A は「該当なしと判断済み」を意味するため、未記入扱いにしない。
    """
    issues = issues_for_content(CASE_H, checker=check_confirmed)
    p02_issues = [i for i in issues if "P-02" in i]
    assert p02_issues == [], (
        f"Expected no P-02 errors for N/A value in confirmation target, got: {p02_issues}"
    )
