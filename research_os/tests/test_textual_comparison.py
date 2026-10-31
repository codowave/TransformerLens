"""textual_comparison の判定が「語彙の数」でなく「照合済みの反証」に基づくことを固定する。"""

from __future__ import annotations

import pytest

from research_os.tasks import textual_comparison as tc

# スウェーデンボルグの基本語彙を多く含むが、反証注記のない項目
VOCAB_HEAVY = {
    "text": "The influx of love and will, heat and light, by degree and order, "
            "into the reception and affection of the mind.",
    "keywords": ["influx", "love", "light"],
}


def _entry(i: int, **extra) -> dict:
    e = {"id": f"X.{i}", "work": "X", "section": i, **VOCAB_HEAVY}
    e.update(extra)
    return e


def _challenge(i: int, verified=...) -> dict:
    e = _entry(i, falsification_relevance="fp-2", falsification_direction="challenges")
    if verified is not ...:
        e["verified"] = verified
    return e


def _run(monkeypatch, entries: list[dict]) -> tc.TextualComparisonResult:
    monkeypatch.setattr(tc, "_load_index", lambda: {"entries": entries})
    return tc.run({}, mode="falsification", focus_fp="fp-2")


def test_vocabulary_alone_never_falsifies(monkeypatch):
    """基本語彙だけの項目がいくら多くても falsified にならない（旧実装の欠陥）。"""
    result = _run(monkeypatch, [_entry(i) for i in range(100)])
    assert result.verdict == tc.TCVerdict.SURVIVES
    assert result.challenges == []
    assert len(result.leads) == 100


def test_growing_the_index_does_not_move_the_verdict(monkeypatch):
    """索引を増やしても、照合済みの反証が増えない限り判定は動かない。"""
    base = [_challenge(0, verified=False)] + [_entry(i) for i in range(1, 25)]
    small = _run(monkeypatch, base).verdict
    big = _run(monkeypatch, base + [_entry(i) for i in range(25, 500)]).verdict
    assert small == big == tc.TCVerdict.INCONCLUSIVE


@pytest.mark.parametrize("verified", [False, None, ...])
def test_unconfirmed_challenges_are_inconclusive(monkeypatch, verified):
    """verified が false・null・キーなしの反証項目は、何件あっても falsified にしない。"""
    entries = [_challenge(i, verified=verified) for i in range(10)] + [_entry(i) for i in range(10, 30)]
    result = _run(monkeypatch, entries)
    assert result.verdict == tc.TCVerdict.INCONCLUSIVE
    assert result.confirmed_challenges == []


def test_missing_verified_is_unknown_not_confirmed():
    """三状態：キーなし・null は unknown。true と同一視しない。"""
    assert tc._verified_state({}) == "unknown"
    assert tc._verified_state({"verified": None}) == "unknown"
    assert tc._verified_state({"verified": False}) == "unverified"
    assert tc._verified_state({"verified": True}) == "confirmed"


def test_one_confirmed_challenge_falsifies_even_in_small_index(monkeypatch):
    """反例は1件で足りる。照合済みなら索引が薄くても falsified。"""
    result = _run(monkeypatch, [_challenge(0, verified=True)])
    assert result.verdict == tc.TCVerdict.FALSIFIED
    assert [a.entry_id for a in result.confirmed_challenges] == ["X.0"]


def test_thin_index_without_challenges_cannot_claim_absence(monkeypatch):
    """反証注記なし・索引が薄い場合は survives でなく inconclusive。"""
    result = _run(monkeypatch, [_entry(i) for i in range(5)])
    assert result.verdict == tc.TCVerdict.INCONCLUSIVE


def test_real_index_is_not_falsified_by_keywords():
    """実際の索引：照合済み（verified: true）の反証項目がない間は falsified にならない。"""
    entries = tc._load_index().get("entries", [])
    if not entries:
        pytest.skip("correspondence_index.json が見つからない")
    result = tc.run({}, mode="falsification", focus_fp="fp-2")
    if not any(e.get("verified") is True and tc._is_annotated_challenge(e, "fp-2") for e in entries):
        assert result.verdict != tc.TCVerdict.FALSIFIED
