#!/usr/bin/env python3
"""
build_first_node.py — 第一ノード (yada / H3045) の検証スクリプト

morphhb データが配置された後に実行し、本文照合で
first_node_yada.json の内容を再検証できる。

使用例:
  cd biblical_correspondence
  python lexicon/build_first_node.py
"""

import json
import sys
from pathlib import Path

# パッケージルートを sys.path に追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from lexicon.biblical_lexicon import verify_verse, lookup_verse, MORPHHB_PATH


def run_checks() -> bool:
    print("=== 第一ノード (yada / H3045) 本文照合チェック ===\n")
    ok = True

    checks = [
        # (ref,          strongs,  expected_contains, description)
        ("Gen.3.5",   "H3045", True,  "エデンの誘惑: yada が存在するはず"),
        ("Gen.4.1",   "H3045", True,  "アダムとエバ: yada が存在するはず"),
        ("Gen.32.29", "H3045", False, "ヤコブ改名: yada は存在しないはず"),
        ("Hos.4.1",   "H3045", False, "ホセア: H3045 ではなく H1847 のはず"),
        ("Hos.4.1",   "H1847", True,  "ホセア: H1847 (da'ath) が存在するはず"),
    ]

    for ref, sid, expected, desc in checks:
        result = verify_verse(ref, sid)
        actual = result.get("contains", False)
        status = "✓ PASS" if actual == expected else "✗ FAIL"
        if actual != expected:
            ok = False
        print(f"{status}  {ref} / {sid}  ({desc})")
        if actual != expected:
            print(f"       expected={expected}, got={actual}")
            print(f"       detail: {result}")
        print()

    # Gen.4.1 の隣接語チェック (yada → qanah)
    print("--- Gen.4.1 隣接語チェック ---")
    try:
        verse = lookup_verse("Gen.4.1")
        strongs_seq = [w.strongs for w in verse.words if w.strongs]
        flat = [s for group in strongs_seq for s in group]
        print(f"Strong's sequence: {flat[:10]} ...")

        yada_idx  = next((i for i, g in enumerate(strongs_seq) if "H3045" in g), None)
        qanah_idx = next((i for i, g in enumerate(strongs_seq) if "H7069" in g), None)

        if yada_idx is not None and qanah_idx is not None:
            print(f"  yada  (H3045) at word index {yada_idx}")
            print(f"  qanah (H7069) at word index {qanah_idx}")
            gap = abs(qanah_idx - yada_idx)
            print(f"  隣接距離: {gap} 語")
            if gap <= 5:
                print("  ✓ PASS: yada と qanah が近接して出現 (人類史最初の親子の瞬間)")
            else:
                print("  ✗ FAIL: 想定より離れている")
        else:
            missing = []
            if yada_idx is None:  missing.append("H3045")
            if qanah_idx is None: missing.append("H7069")
            print(f"  ✗ FAIL: {missing} が見つからなかった")
            ok = False
    except Exception as e:
        print(f"  ERROR: {e}")
        ok = False

    print()
    print("=== 結果:", "全チェック通過 ✓" if ok else "失敗あり ✗", "===")
    return ok


if __name__ == "__main__":
    if not MORPHHB_PATH.exists():
        print(f"ERROR: morphhb データが見つかりません: {MORPHHB_PATH}")
        print("  data/ ディレクトリに morphhb を git clone してください:")
        print("  cd data && git clone --depth 1 https://github.com/openscriptures/morphhb.git")
        sys.exit(1)

    success = run_checks()
    sys.exit(0 if success else 1)
