"""Pipeline tests on a small synthetic frame (no network)."""
import pandas as pd
import pytest

import build_data as b


def fake_source(last=2025, drop=None):
    rows = []
    codes = list(b.COUNTRIES) + ["WLD", "ARB", "USA"]
    for i, code in enumerate(codes):
        for y in range(1955, last + 1):
            if drop and code == drop[0] and y in drop[1]:
                continue
            rows.append((code, code, y, 1000 * (i + 1) * (1.02 ** (y - 1955))))
    return pd.DataFrame(rows, columns=["name", "code", "year", "value"])


def test_to_wide_keeps_only_needed_codes_and_years():
    w = b.to_wide(fake_source())
    assert w.index.min() == b.FIRST_YEAR
    assert "USA" not in w.columns
    assert set(b.COUNTRIES) <= set(w.columns) and {"WLD", "ARB", "GCC"} <= set(w.columns)


def test_gcc_is_sum_of_six_and_never_partial():
    df = fake_source(drop=("QAT", {1970}))
    w = b.to_wide(df)
    assert w.loc[1980, "GCC"] == pytest.approx(w.loc[1980, b.GCC].sum())
    assert pd.isna(w.loc[1970, "GCC"])


def test_latest_complete_year_ignores_partial_last_year():
    df = fake_source(last=2026)
    df = df[~((df.code == "SOM") & (df.year == 2026))]
    assert b.latest_complete_year(b.to_wide(df)) == 2025


def test_missing_code_raises():
    df = fake_source()
    with pytest.raises(ValueError):
        b.to_wide(df[df.code != "SAU"])


def test_summary_and_findings_handle_late_series():
    df = fake_source(drop=("PSE", set(range(1955, 1990))))
    w = b.to_wide(df)
    s = b.summarise(w, 2025).set_index("code")
    assert pd.isna(s.loc["PSE", "times_bigger_since_1960"])
    assert s.loc["SAU", "times_bigger_since_1960"] == pytest.approx(1.02 ** 65, rel=1e-3)
    assert s.loc[list(b.COUNTRIES), "share_of_arab_total_pct"].sum() == pytest.approx(100, abs=0.05)
    assert "PSE" not in b.full_series_countries(w, 2025)
    text = " ".join(b.findings(w, s.reset_index(), 2025))
    assert "21 Arab League countries" in text and "Palestine" in text
