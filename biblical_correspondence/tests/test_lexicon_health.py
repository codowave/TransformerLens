"""
test_lexicon_health.py — データ未配置状態での安全性を固定するテスト

設計原則:
  morphhb / morphgnt が存在しなくても、全エンドポイントが適切に
  "unavailable" を返し、クラッシュしないことを確認する。

  「データなし」は「故障」ではない — この区別をテストで固定する。
"""

import json
import os
import sys
from pathlib import Path

import pytest

# biblical_correspondence パッケージをパスに追加
_BC_DIR = Path(__file__).parent.parent
if str(_BC_DIR) not in sys.path:
    sys.path.insert(0, str(_BC_DIR))

# morphhb / morphgnt が存在しない状態に設定（CI でも確実に unavailable になる）
os.environ.setdefault("MORPHHB_PATH", str(_BC_DIR / "data" / "__nonexistent_morphhb__"))
os.environ.setdefault("MORPHGNT_PATH", str(_BC_DIR / "data" / "__nonexistent_morphgnt__"))

from lexicon.biblical_lexicon import verify_verse, lookup_word  # noqa: E402
from correspondence.correspondence_lookup import lookup_correspondence  # noqa: E402


# ---------------------------------------------------------------------------
# verify_verse — 三状態の unavailable パス
# ---------------------------------------------------------------------------

class TestVerseVerifyUnavailable:
    """morphhb 未配置時に verify_verse が unavailable を正しく返すことを固定する。"""

    def test_returns_dict(self):
        result = verify_verse("Gen.3.5", "H3045")
        assert isinstance(result, dict)

    def test_status_is_unavailable(self):
        result = verify_verse("Gen.3.5", "H3045")
        assert result["status"] == "unavailable", (
            f"expected 'unavailable', got {result['status']!r}\n"
            "Codex P1: FileNotFoundError を not_found に変換してはならない"
        )

    def test_contains_is_none(self):
        """unavailable のとき contains は None であること（False ではない）。"""
        result = verify_verse("Gen.3.5", "H3045")
        assert result["contains"] is None, (
            f"expected None, got {result['contains']!r}\n"
            "contains=False は『照合済みの不在』を意味する。"
            "データ未配置を False で返すと『不在』と誤解される（Codex P1 バグ）。"
        )

    def test_does_not_raise(self):
        """FileNotFoundError が外側に漏れないこと。"""
        for ref, sid in [("Gen.3.5", "H3045"), ("John.17.3", "G1097"), ("Ps.23.1", "H7462")]:
            result = verify_verse(ref, sid)
            assert "status" in result

    def test_unavailable_for_greek_ref(self):
        result = verify_verse("John.17.3", "G1097")
        assert result["status"] == "unavailable"
        assert result["contains"] is None

    def test_reason_field_present(self):
        result = verify_verse("Gen.3.5", "H3045")
        assert "reason" in result
        assert result["reason"] in ("morphhb_not_available", "ref_not_found")


# ---------------------------------------------------------------------------
# verify_verse — ref フォーマットエラー
# ---------------------------------------------------------------------------

class TestVerseVerifyBadRef:
    def test_invalid_ref_format_returns_unavailable(self):
        result = verify_verse("not-a-ref", "H3045")
        assert result["status"] == "unavailable"
        assert result["contains"] is None

    def test_two_part_ref_returns_unavailable(self):
        result = verify_verse("Gen.3", "H3045")
        assert result["status"] == "unavailable"


# ---------------------------------------------------------------------------
# lookup_word — Strong's 辞書（データ有り前提、strongs_*.json は同梱）
# ---------------------------------------------------------------------------

class TestLookupWord:
    def test_h3045_yada(self):
        entry = lookup_word("H3045")
        assert isinstance(entry, dict)
        # 辞書エントリに lemma または translit などの何らかのテキストフィールドがある
        assert any(k in entry for k in ("lemma", "translit", "xlit", "strongs", "def"))

    def test_unknown_id_raises_keyerror(self):
        with pytest.raises(KeyError):
            lookup_word("H99999")

    def test_case_insensitive(self):
        upper = lookup_word("H3045")
        lower = lookup_word("h3045")
        assert upper == lower


# ---------------------------------------------------------------------------
# correspondence_lookup — 三状態
# ---------------------------------------------------------------------------

class TestCorrespondenceLookup:
    def test_gen_3_5_found(self):
        result = lookup_correspondence("Gen.3.5")
        assert result["status"] == "found"
        assert len(result["sources"]) > 0

    def test_gen_1_1_not_found(self):
        """Gen は索引済み（エントリあり）だが 1.1 はない → not_found。"""
        result = lookup_correspondence("Gen.1.1")
        assert result["status"] == "not_found"

    def test_john_17_3_unavailable(self):
        """John はインデックス未整備 → unavailable。not_found ではない。"""
        result = lookup_correspondence("John.17.3")
        assert result["status"] == "unavailable", (
            f"expected 'unavailable', got {result['status']!r}\n"
            "John に索引エントリがないなら not_found ではなく unavailable でなければならない。"
        )

    def test_sources_list_present(self):
        result = lookup_correspondence("Gen.3.5")
        assert isinstance(result["sources"], list)
        src = result["sources"][0]
        assert "work" in src
        assert "text" in src

    def test_unavailable_has_empty_sources(self):
        # Acts はインデックス未整備（エントリなし）→ unavailable
        result = lookup_correspondence("Acts.2.1")
        assert result["status"] == "unavailable"
        assert result["sources"] == []


# ---------------------------------------------------------------------------
# health エンドポイント（FastAPI TestClient）
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    """実際の HTTP レスポンスを検証する。"""

    @pytest.fixture(scope="class")
    def client(self):
        from fastapi.testclient import TestClient
        import sys as _sys

        # ANTHROPIC_API_KEY がないと app.py がモジュールレベルで RuntimeError を上げる。
        # テスト用にダミーキーを設定（実際の API は呼ばれない）。
        os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-dummy-key-for-health-check")

        if "app" in _sys.modules:
            del _sys.modules["app"]
        _sys.path.insert(0, str(_BC_DIR))
        import app as _app
        return TestClient(_app.app)

    def test_health_returns_200(self, client):
        resp = client.get("/api/lexicon/health")
        assert resp.status_code == 200

    def test_health_has_required_keys(self, client):
        data = client.get("/api/lexicon/health").json()
        assert "morphhb" in data
        assert "morphgnt" in data
        assert "correspondence_index" in data
        assert "verify_verse_status" in data

    def test_health_morphhb_missing(self, client):
        data = client.get("/api/lexicon/health").json()
        # データ未配置環境では missing
        assert data["morphhb"]["status"] == "missing"

    def test_health_verify_degraded_when_no_data(self, client):
        data = client.get("/api/lexicon/health").json()
        assert data["verify_verse_status"] == "degraded"

    def test_health_correspondence_entry_count(self, client):
        data = client.get("/api/lexicon/health").json()
        count = data["correspondence_index"]["entry_count"]
        assert isinstance(count, int)
        assert count >= 18, f"expected ≥18 entries, got {count}"

    def test_health_note_field(self, client):
        """note フィールドに『故障ではない』旨が含まれること。"""
        data = client.get("/api/lexicon/health").json()
        assert "note" in data
        assert "故障" in data["note"]
