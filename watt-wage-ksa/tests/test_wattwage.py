import numpy as np
import pytest

from wattwage import data, fiscal, forecast, impact, tariffs, wages


# --- tariffs: worked examples published with the 2027 announcement --------
def test_sabq_example_1000kwh():
    b = tariffs.electricity_bill(1000, breaker_a=60, schedule="2027", vat=0)
    assert b.energy == pytest.approx(210)
    assert b.fixed == 70
    assert b.total == pytest.approx(280)
    assert tariffs.electricity_bill(1000, 60, "2027").total == pytest.approx(322)


def test_2000kwh_100a_example():
    assert tariffs.electricity_bill(2000, 150, "2027", vat=0).total == pytest.approx(500)


def test_second_tier_applies_only_above_6000():
    b = tariffs.electricity_bill(7000, 350, "2027", vat=0)
    assert b.energy == pytest.approx(6000 * 0.21 + 1000 * 0.33)
    assert b.fixed == 100


def test_old_meter_fees():
    assert tariffs.electricity_fixed_fee(60, "2018") == 10
    assert tariffs.electricity_fixed_fee(150, "2018") == 15
    assert tariffs.electricity_fixed_fee(400, "2018") == 25
    assert tariffs.electricity_fixed_fee(500, "2018") == 30


def test_2016_tiers():
    assert tariffs.electricity_bill(5000, 60, "2016", vat=0).energy == pytest.approx(
        2000 * 0.05 + 2000 * 0.10 + 1000 * 0.20)


def test_water_2027_progressive_with_sewage_and_fees():
    b = tariffs.water_bill(30, 20, "2027", vat=0)
    assert b.energy == pytest.approx(15 * 1.5 + 15 * 3.0)
    assert b.fixed == 30
    assert tariffs.water_bill(50, 20, "2027", vat=0).energy == pytest.approx(
        15 * 1.5 + 15 * 3 + 15 * 6 + 5 * 9)


def test_vectorised_matches_scalar():
    q = np.array([0, 150, 2500, 6000, 6400, 12000])
    for s in ("pre2016", "2016", "2018", "2027"):
        vec = tariffs.electricity_bill_vec(q, 150, s)
        ref = [tariffs.electricity_bill(x, 150, s).total for x in q]
        assert np.allclose(vec, ref)
    m = np.array([0, 10, 33, 47, 90])
    assert np.allclose(tariffs.water_bill_vec(m, "2027"), [tariffs.water_bill(x, 20, "2027").total for x in m])


def test_sector_changes():
    s = tariffs.sector_comparison().set_index("sector")
    assert s.loc["residential", "tier1_change_pct"] == pytest.approx(16.7)
    assert s.loc["residential", "tier2_change_pct"] == pytest.approx(10.0)


# --- data integrity ---------------------------------------------------------
def test_tariff_tiers_are_contiguous():
    for sched, g in data.electricity_tariffs().groupby("schedule"):
        g = g.sort_values("tier_from_kwh")
        assert g["tier_from_kwh"].iloc[0] == 0
        assert (g["tier_from_kwh"].iloc[1:].to_numpy() == g["tier_to_kwh"].iloc[:-1].to_numpy()).all(), sched
        assert g["tier_to_kwh"].isna().iloc[-1]


def test_cpi_series_complete():
    cpi = data.cpi_monthly()
    assert cpi.index.is_monotonic_increasing
    assert len(cpi) == (cpi.index[-1] - cpi.index[0]).n + 1


def test_seasonality_mean_is_one():
    from wattwage.household import seasonality
    assert seasonality().mean() == pytest.approx(1.0)


# --- analysis ---------------------------------------------------------------
def test_past_reforms_reverse_after_12_months():
    t = impact.event_table()
    assert (t["jump_pp"] > 2).all()
    assert t["symmetry_ratio"].between(0.8, 1.3).all()


def test_wage_reconstruction_matches_published_bands():
    w = wages.sample_wages(300_000)
    f = data.wage_facts()
    assert (w < 4000).mean() * 100 == pytest.approx(f["share_below_4000"], abs=0.2)
    assert np.median(w) == pytest.approx(f["median_wage"], rel=0.01)
    assert ((w >= 4000) & (w < 8000)).mean() * 100 == pytest.approx(f["share_4000_8000"], abs=0.3)
    wb = wages.sample_wages(300_000, bunching=0.4)
    assert np.median(wb) == pytest.approx(f["median_wage"], rel=0.01)


def test_support_calibration_2018():
    c = fiscal.calibration_2018()
    assert c["model_cost_bn"] == pytest.approx(c["reported_cost_bn"], rel=0.05)


def test_forecast_shock_window():
    base = forecast.baseline()
    path = forecast.scenario_path(base, 1.0)
    months = base["month"]
    diff = path - base["baseline"].to_numpy()
    assert diff[months.str.startswith("2027")].min() == pytest.approx(1.0)
    assert abs(diff[~months.str.startswith("2027")]).max() == pytest.approx(0.0)


def test_arima_beats_naive_backtest():
    bt = forecast.backtest()
    assert bt["mae_arima"] <= bt["mae_naive"]
