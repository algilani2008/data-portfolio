"""Offline tests for water.py and for the generated results (if build.py has run)."""
import json
import math
import sys
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import water  # noqa: E402

RESULTS = HERE / "results"


def long(rows):
    return pd.DataFrame(rows, columns=["geo", "time", "value"])


def test_22_arab_league_countries_with_both_names():
    assert len(water.ARAB_COUNTRIES) == 22
    assert all(en and ar for en, ar in water.ARAB_COUNTRIES.values())
    assert set(water.GCC) <= set(water.ARAB_COUNTRIES)


@pytest.mark.parametrize(
    "pct,label",
    [(0, "No stress"), (24.9, "No stress"), (25, "Low"), (60, "Medium"),
     (99.9, "High"), (100, "Critical"), (3850, "Critical")],
)
def test_stress_class_boundaries(pct, label):
    assert water.stress_class(pct) == label


@pytest.mark.parametrize(
    "m3,label",
    [(0, "Absolute scarcity"), (499, "Absolute scarcity"), (500, "Scarcity"),
     (1000, "Stress"), (1700, "No stress"), (50000, "No stress")],
)
def test_falkenmark_boundaries(m3, label):
    assert water.falkenmark_class(m3) == label


def test_classify_nan_is_none():
    assert water.stress_class(float("nan")) is None
    assert water.falkenmark_class(None) is None


def test_latest_observation_detects_carried_forward_values():
    s = long([
        ("aaa", 2015, 10.0), ("aaa", 2016, 12.0), ("aaa", 2017, 12.0), ("aaa", 2018, 12.0),
        ("bbb", 2015, 5.0), ("bbb", 2016, 6.0),
        ("ccc", 2016, 7.0), ("ccc", 2017, float("nan")),
    ])
    out = water.latest_observation(s).set_index("geo")
    assert out.loc["aaa", "value"] == 12.0
    assert out.loc["aaa", "latest_year"] == 2018
    assert out.loc["aaa", "last_changed_year"] == 2016
    assert out.loc["bbb", "last_changed_year"] == 2016
    # NaN rows are ignored, not treated as the latest value
    assert out.loc["ccc", "latest_year"] == 2016


def test_latest_observation_all_constant_series():
    s = long([("aaa", y, 3.0) for y in range(2000, 2005)])
    out = water.latest_observation(s).iloc[0]
    assert out["last_changed_year"] == 2000 and out["latest_year"] == 2004


def test_per_capita_recompute():
    res = long([("aaa", 2020, 2.4)])        # 2.4 billion m3
    pop = long([("aaa", 2020, 32_000_000)])  # 32 million people
    out = water.per_capita(res, pop)
    assert out.iloc[0]["value"] == pytest.approx(75.0)


def test_per_capita_skips_zero_population():
    out = water.per_capita(long([("aaa", 2020, 1.0)]), long([("aaa", 2020, 0)]))
    assert out.empty


def test_change_table_ratio_and_missing_years():
    s = long([("aaa", 1962, 1000.0), ("aaa", 2022, 100.0), ("bbb", 2022, 50.0)])
    t = water.change_table(s, 1962, 2022)
    assert list(t.index) == ["aaa"]  # bbb lacks 1962
    assert t.loc["aaa", "ratio"] == pytest.approx(0.1)


def test_count_by_class():
    counts = water.count_by_class(pd.Series([10, 30, 150, 400, float("nan")]), water.stress_class)
    assert counts == {"No stress": 1, "Low": 1, "Critical": 2}


def test_multiple_of_renewable():
    assert water.multiple_of_renewable(23.38, 2.4) == pytest.approx(9.7417, rel=1e-3)
    with pytest.raises(ValueError):
        water.multiple_of_renewable(1.0, 0.0)


# ---- checks on the committed example output (skipped if build.py has not been run)
needs_results = pytest.mark.skipif(not (RESULTS / "metadata.json").exists(),
                                   reason="run build.py first")


@needs_results
def test_results_cover_all_countries_and_classes_are_consistent():
    df = pd.read_csv(RESULTS / "water_stress_latest.csv")
    assert len(df) == 22
    # values are rounded to 0.1 in the CSV, so re-classifying them must give the stored class
    assert (df["value"].map(water.stress_class) == df["class"]).all()
    assert (df["last_changed_year"] <= df["latest_year"]).all()


@needs_results
def test_sector_shares_consistent_or_flagged():
    df = pd.read_csv(RESULTS / "withdrawals_by_sector.csv")
    total = df[["agriculture", "industry", "domestic"]].sum(axis=1)
    ok = df["consistent"].astype(bool)
    assert ((total[ok] - 100).abs() <= 1.5).all()
    # any row flagged inconsistent must be named in the findings, not silently used
    text = (RESULTS / "findings.md").read_text(encoding="utf-8")
    for name in df.loc[~ok, "name_en"]:
        assert name in text.split("Left out because")[1]


@needs_results
def test_metadata_pins_source_and_checks_pass():
    meta = json.loads((RESULTS / "metadata.json").read_text(encoding="utf-8"))
    assert len(meta["commit"]) == 40
    assert "CC BY 4.0" in meta["license"]
    assert all(len(v["sha256"]) == 64 for v in meta["indicators"].values())
    assert meta["per_capita_recompute_median_rel_diff"] < 0.01
    for png in ["water_stress_ranking.png", "water_per_person.png",
                "withdrawals_by_sector.png", "saudi_withdrawals.png"]:
        assert (RESULTS / png).stat().st_size > 10_000


@needs_results
def test_findings_numbers_present():
    text = (RESULTS / "findings.md").read_text(encoding="utf-8")
    assert "Saudi Arabia" in text and "nan" not in text.lower().replace("financ", "")
    assert not math.isnan(float(pd.read_csv(RESULTS / "saudi_withdrawals.csv")["withdrawals_bn_m3"].iloc[-1]))
