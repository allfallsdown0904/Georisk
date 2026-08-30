from app.data_loader import load_countries, load_risk_indicators

REQUIRED_COUNTRY_FIELDS = {"code", "name_zh", "name_en", "region"}
REQUIRED_INDICATOR_FIELDS = {
    "country_code",
    "dimension",
    "indicator",
    "value",
    "score",
    "evidence",
    "source",
}


def test_countries_loaded():
    countries = load_countries()
    assert len(countries) >= 3
    for c in countries:
        assert REQUIRED_COUNTRY_FIELDS <= c.keys()


def test_indicators_loaded():
    rows = load_risk_indicators()
    assert len(rows) >= 5
    for r in rows:
        assert REQUIRED_INDICATOR_FIELDS <= r.keys()
        assert 0 <= float(r["score"]) <= 100


def test_indicators_filter_by_country():
    rows = load_risk_indicators("KZ")
    assert rows
    assert all(r["country_code"] == "KZ" for r in rows)
