import pytest

from app.risk.scoring import build_profile, score_to_level

COUNTRIES = ["KZ", "NG", "RS"]


@pytest.mark.parametrize("code", COUNTRIES)
def test_profile_shape(code):
    profile = build_profile(code)
    assert profile.country_code == code
    assert 0 <= profile.overall_score <= 100
    assert profile.overall_level in {"低", "中", "高"}
    assert len(profile.dimensions) >= 3
    for d in profile.dimensions:
        assert 0 <= d.score <= 100
        assert d.level in {"低", "中", "高"}
        assert d.evidence


def test_unknown_country_raises():
    with pytest.raises(KeyError):
        build_profile("XX")


def test_score_to_level():
    assert score_to_level(20) == "低"
    assert score_to_level(55) == "中"
    assert score_to_level(85) == "高"
