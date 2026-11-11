"""Unit tests for oil_gdp.py (no network needed)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import oil_gdp as og  # noqa: E402


def test_annual_mean_drops_partial_years():
    dates = pd.date_range("2019-06-15", "2021-03-15", freq="MS") + pd.Timedelta(days=14)
    df = pd.DataFrame({"Date": dates, "Price": 10.0})
    df.loc[df.Date.dt.year == 2020, "Price"] = np.arange(1, 13)
    out = og.annual_mean_price(df)
    assert list(out.index) == [2020]
    assert out.loc[2020] == pytest.approx(6.5)


def test_log_growth_series_and_gap():
    s = pd.Series([100.0, 110.0, 121.0, 200.0], index=[2000, 2001, 2002, 2005])
    g = og.log_growth(s)
    assert np.isnan(g.loc[2000])
    assert g.loc[2001] == pytest.approx(np.log(1.1))
    assert g.loc[2002] == pytest.approx(np.log(1.1))
    assert np.isnan(g.loc[2005])  # 2002 -> 2005 is not a one-year step


def test_log_growth_dataframe_ignores_nonpositive():
    df = pd.DataFrame({"A": [1.0, 2.0, 0.0], "B": [1.0, np.e, np.e**2]}, index=[2000, 2001, 2002])
    g = og.log_growth(df)
    assert g.loc[2001, "A"] == pytest.approx(np.log(2))
    assert np.isnan(g.loc[2002, "A"])
    assert g.loc[2002, "B"] == pytest.approx(1.0)


def test_elasticity_recovers_known_slope():
    rng = np.random.default_rng(1)
    years = range(1990, 2030)
    x = pd.Series(rng.normal(0, 0.25, len(years)), index=years)
    y = 0.02 + 0.4 * x + pd.Series(rng.normal(0, 0.01, len(years)), index=years)
    e = og.elasticity(y, x, n_boot=500)
    assert e.slope == pytest.approx(0.4, abs=0.02)
    assert e.intercept == pytest.approx(0.02, abs=0.01)
    assert e.ci_low < 0.4 < e.ci_high
    assert e.r2 > 0.95 and e.n == len(years)


def test_elasticity_needs_enough_years():
    s = pd.Series([0.1, 0.2, 0.3], index=[2000, 2001, 2002])
    assert og.elasticity(s, s) is None


def test_ols_slope_rejects_constant_x():
    with pytest.raises(ValueError):
        og.ols_slope(np.ones(5), np.arange(5.0))


def test_rolling_corr_perfect():
    a = pd.Series(np.arange(12.0), index=range(2000, 2012))
    rc = og.rolling_corr(a, 2 * a + 1, window=5)
    assert rc.iloc[:4].isna().all()
    assert np.allclose(rc.iloc[4:], 1.0)


def test_wide_per_capita_and_cagr():
    long = pd.DataFrame({
        "Country Code": ["AAA", "AAA", "BBB", "BBB"],
        "Year": [2000, 2010, 2000, 2010],
        "Value": [100.0, 200.0, 50.0, 50.0],
    })
    gdp = og.wide_by_country(long, ["BBB", "AAA", "ZZZ"])
    assert list(gdp.columns) == ["BBB", "AAA"]
    pop = gdp / 10
    pc = og.per_capita(gdp, pop)
    assert (pc == 10).all().all()
    assert og.cagr(gdp["AAA"], 2000, 2010) == pytest.approx(2 ** 0.1 - 1)
    assert np.isnan(og.cagr(gdp["AAA"], 1990, 2010))


def test_generated_results_are_consistent():
    path = HERE / "results" / "elasticities.csv"
    if not path.exists():
        pytest.skip("run run_analysis.py first")
    el = pd.read_csv(path)
    assert set(el.period) == {"full", "early", "late"}
    assert (el.ci95_low <= el.elasticity).all() and (el.elasticity <= el.ci95_high).all()
    assert set(og.GCC) <= set(el.code)
