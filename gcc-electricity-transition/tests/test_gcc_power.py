"""Unit tests for gcc_power on a tiny hand-made frame (no network needed)."""
import math
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gcc_power as gp  # noqa: E402


def make_frame():
    rows = []
    for iso, country in [*gp.GCC.items(), (None, "World")]:
        for year, gen, lc, gas, oil, solar, nuc in [(2015, 100.0, 1.0, 60.0, 39.0, 1.0, 0.0),
                                                    (2024, 150.0, 31.0, 80.0, 39.0, 11.0, 20.0)]:
            rows.append({"country": country, "iso_code": iso, "year": year, "population": 1e6,
                         "electricity_generation": gen, "per_capita_electricity": gen * 1e3,
                         "carbon_intensity_elec": 500.0, "low_carbon_electricity": lc,
                         "low_carbon_share_elec": lc / gen * 100, "fossil_electricity": gen - lc,
                         "oil_share_elec": oil / gen * 100, "gas_share_elec": gas / gen * 100,
                         "solar_share_elec": solar / gen * 100, "nuclear_share_elec": nuc / gen * 100,
                         "gas_electricity": gas, "oil_electricity": oil, "solar_electricity": solar,
                         "nuclear_electricity": nuc})
    rows.append({"country": "Canada", "iso_code": "CAN", "year": 2024, "electricity_generation": 600.0})
    return pd.DataFrame(rows)


def test_select_keeps_only_gcc_and_world():
    df = gp.select(make_frame(), 2000, 2030)
    assert set(df["code"]) == set(gp.GCC) | {"WLD"}
    assert "Canada" not in set(df["country"])


def test_latest_common_year_ignores_partial_years():
    df = gp.select(make_frame(), 2000, 2030)
    extra = df[df["code"] == "QAT"].tail(1).assign(year=2025)
    df = pd.concat([df, extra])
    assert gp.latest_common_year(df) == 2024


def test_mix_shares_sum_to_100():
    df = gp.select(make_frame(), 2000, 2030)
    shares = gp.mix_shares(df, 2024)
    assert shares.sum(axis=1).round(1).eq(100.0).all()
    assert shares.at["SAU", "gas"] == pytest.approx(80 / 150 * 100, abs=0.01)


def test_cagr():
    assert gp.cagr(100, 121, 2) == pytest.approx(10.0)
    with pytest.raises(ValueError):
        gp.cagr(0, 10, 2)


def test_growth_met_by_low_carbon():
    df = gp.select(make_frame(), 2000, 2030)
    g = gp.growth_met_by_low_carbon(df, "SAU", 2015, 2024)
    assert g["added_twh"] == 50
    assert g["added_low_carbon_twh"] == 30
    assert g["low_carbon_share_of_growth_pct"] == 60.0


def test_growth_share_nan_when_no_growth():
    df = gp.select(make_frame(), 2000, 2030)
    df.loc[(df["code"] == "OMN") & (df["year"] == 2024), "electricity_generation"] = 100.0
    assert math.isnan(gp.growth_met_by_low_carbon(df, "OMN", 2015, 2024)["low_carbon_share_of_growth_pct"])


def test_summary_table_has_all_rows():
    df = gp.select(make_frame(), 2000, 2030)
    t = gp.summary_table(df, 2015, 2024, 2015)
    assert list(t["code"]) == [*gp.GCC, "WLD"]
    assert (t["low_carbon_share_pct_2024"] > t["low_carbon_share_pct_2015"]).all()


def test_committed_results_are_consistent():
    """The example output in results/ must agree with itself (shares sum to ~100)."""
    res = Path(__file__).resolve().parents[1] / "results"
    mixes = list(res.glob("generation_mix_*.csv"))
    if not mixes:
        pytest.skip("run run_analysis.py first")
    mix = pd.read_csv(mixes[0], index_col=0)
    assert ((mix.sum(axis=1) - 100).abs() < 1.0).all()
    summary = pd.read_csv(res / "summary_by_country.csv")
    assert len(summary) == 7
