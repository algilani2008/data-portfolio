"""Unit tests for build_data.py. They use small made-up frames and need no network."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_data as bd  # noqa: E402


def frame(rows):
    return pd.DataFrame(rows, columns=["country", "iso_code", "year", "electricity_generation",
                                       "low_carbon_electricity", "population"])


def test_select_keeps_listed_countries_and_world_from_start_year():
    df = frame([
        ["Saudi Arabia", "SAU", 2010, 200.0, 0.0, 1],
        ["Saudi Arabia", "SAU", 1999, 100.0, 0.0, 1],
        ["France", "FRA", 2010, 500.0, 0.0, 1],
        ["World", None, 2010, 20000.0, 0.0, 1],
    ])
    out = bd.select(df)
    assert sorted(out["code"]) == ["SAU", "WLD"]
    assert out["year"].min() >= bd.START_YEAR


def test_end_year_ignores_a_year_only_few_countries_report():
    codes = list(bd.COUNTRIES)
    rows = [[c, c, 2023, 1.0, 0.0, 1] for c in codes]
    rows += [[c, c, 2024, 1.0, 0.0, 1] for c in codes[:-2]]  # 20 of 22
    rows += [[c, c, 2025, 1.0, 0.0, 1] for c in codes[:6]]   # 6 of 22
    df = frame(rows)
    df["code"] = df["iso_code"]
    assert bd.end_year(df) == 2024


def test_end_year_raises_when_nothing_qualifies():
    df = frame([["Oman", "OMN", 2020, 1.0, 0.0, 1]])
    df["code"] = df["iso_code"]
    with pytest.raises(ValueError):
        bd.end_year(df)


def test_series_keeps_gaps_and_never_fills_them():
    df = pd.DataFrame({"code": ["OMN", "OMN"], "year": [2000, 2002], "x": [1.234, float("nan")]})
    assert bd.series(df, "OMN", "x", [2000, 2001, 2002], 2) == [1.23, None, None]


def test_series_handles_a_column_missing_from_the_source():
    df = pd.DataFrame({"code": ["OMN"], "year": [2000]})
    assert bd.series(df, "OMN", "absent", [2000, 2001], 2) == [None, None]


def test_clean_returns_integers_at_zero_decimals():
    assert bd.clean(12.6, 0) == 13 and isinstance(bd.clean(12.6, 0), int)
    assert bd.clean(float("nan"), 2) is None


def test_arab_total_excludes_world_and_countries_without_data():
    df = frame([
        ["Oman", "OMN", 2024, 100.0, 10.0, 5],
        ["Qatar", "QAT", 2024, 100.0, 30.0, 3],
        ["Comoros", "COM", 2024, None, None, 1],
        ["World", None, 2024, 1000.0, 400.0, 100],
    ])
    df["code"] = df["iso_code"].fillna(bd.WORLD)
    out = bd.arab_total(df, 2024)
    assert out["countries"] == 2
    assert out["generation_twh"] == 200.0
    assert out["low_carbon_share_pct"] == 20.0
    assert out["population"] == 8
