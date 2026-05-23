#!/usr/bin/env bash
# bootstrap_morph_data.sh — morphhb / morphgnt データ配置スクリプト
#
# 使い方:
#   cd biblical_correspondence
#   bash scripts/bootstrap_morph_data.sh
#
# データが存在しなくても /api/lexicon/health は動く（unavailable を返す）。
# このスクリプトは「unavailable → available」に切り替えたいときだけ実行する。
#
# 前提: git, curl が使えること

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$APP_DIR/data"

info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*"; }
ok()    { echo "[OK]    $*"; }
fail()  { echo "[ERROR] $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# morphhb (Hebrew OT — openscriptures/morphhb)
# ---------------------------------------------------------------------------
MORPHHB_DEST="$DATA_DIR/morphhb/wlc"
MORPHHB_REPO="https://github.com/openscriptures/morphhb.git"
MORPHHB_SUBDIR="wlc"

bootstrap_morphhb() {
    if [[ -d "$MORPHHB_DEST" && -n "$(ls -A "$MORPHHB_DEST"/*.xml 2>/dev/null)" ]]; then
        ok "morphhb already present at $MORPHHB_DEST"
        return 0
    fi

    info "Cloning morphhb (sparse — wlc/ only) ..."
    mkdir -p "$DATA_DIR/morphhb"
    TMPDIR_HEB="$(mktemp -d)"
    trap 'rm -rf "$TMPDIR_HEB"' EXIT

    # Sparse clone to avoid downloading the entire history
    git clone --depth 1 --filter=blob:none --sparse "$MORPHHB_REPO" "$TMPDIR_HEB/morphhb"
    (
        cd "$TMPDIR_HEB/morphhb"
        git sparse-checkout set "$MORPHHB_SUBDIR"
    )

    cp -r "$TMPDIR_HEB/morphhb/$MORPHHB_SUBDIR" "$MORPHHB_DEST"
    ok "morphhb installed to $MORPHHB_DEST"
    trap - EXIT
    rm -rf "$TMPDIR_HEB"
}

# ---------------------------------------------------------------------------
# morphgnt (Greek NT — morphgnt/morphgnt)
# ---------------------------------------------------------------------------
MORPHGNT_DEST="$DATA_DIR/morphgnt"
MORPHGNT_REPO="https://github.com/morphgnt/morphgnt.git"

bootstrap_morphgnt() {
    if [[ -d "$MORPHGNT_DEST" && -n "$(ls -A "$MORPHGNT_DEST"/*.txt 2>/dev/null)" ]]; then
        ok "morphgnt already present at $MORPHGNT_DEST"
        return 0
    fi

    info "Cloning morphgnt ..."
    mkdir -p "$DATA_DIR"
    TMPDIR_GRK="$(mktemp -d)"
    trap 'rm -rf "$TMPDIR_GRK"' EXIT

    git clone --depth 1 "$MORPHGNT_REPO" "$TMPDIR_GRK/morphgnt"
    cp -r "$TMPDIR_GRK/morphgnt" "$MORPHGNT_DEST"
    ok "morphgnt installed to $MORPHGNT_DEST"
    trap - EXIT
    rm -rf "$TMPDIR_GRK"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
echo "=== Biblical morphological data bootstrap ==="
echo "    Target: $DATA_DIR"
echo ""

bootstrap_morphhb
bootstrap_morphgnt

echo ""
echo "=== Done ==="
echo ""
echo "ヘルスチェック確認:"
echo "  curl http://localhost:8000/api/lexicon/health"
echo ""
echo "morphhb が available になっていれば原語照合が有効になります。"
