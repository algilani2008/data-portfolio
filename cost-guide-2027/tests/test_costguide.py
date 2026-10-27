import numpy as np
import pytest

from costguide import data, fiscal, forecast, impact, tariffs, wages


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
    from costguide.household import seasonality
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


# --- business, society, solutions, outlook ---------------------------------
from costguide import business, outlook, society, solutions


def test_commercial_fixed_charges_2027():
    assert tariffs.sector_fixed_fee(60, "commercial", "2027") == 350
    assert tariffs.sector_fixed_fee(350, "industrial", "2027") == 900
    assert tariffs.sector_fixed_fee(150, "agricultural", "2027") == 160
    assert tariffs.sector_fixed_fee(60, "commercial", "2018") == 10


def test_commercial_bill_tiers():
    b = tariffs.sector_bill(8000, 150, "commercial", "2027")
    assert b.energy == pytest.approx(6000 * 0.25 + 2000 * 0.35)
    assert b.fixed == 500


def test_parse_wages():
    assert business.parse_wages("4000x2|5500") == [4000, 4000, 5500]
    assert business.nitaqat_raise([4000, 4500, 7000], 5000) == 1500


def test_archetypes_are_consistent():
    t = business.archetype_table()
    assert (t["elec_new_year"] > t["elec_old_year"]).all()
    assert (t["wage_cost_6000_year"] >= t["wage_cost_5000_year"]).all()


def test_burden_signs():
    b = society.burden_table().set_index("id")
    assert b.loc["expat_family", "net_2028_year"] < 0
    assert b.loc["ss_family", "net_2028_year"] > 0


def test_price_response_reduces_use():
    r = society.consumption_response()
    assert -10 < r["residential_kwh_change_pct"] < 0
    assert r["co2_mt_saved_year"] > 0


def test_measures_pay_back_faster_under_new_tariff():
    m = solutions.measure_table()
    m = m[m["cost_sar"] > 0]
    assert (m["saving_new_year"] >= m["saving_old_year"]).all()


def test_outlook_years():
    o = outlook.outlook_table()
    assert list(o["year"]) == list(range(2025, 2031))
    assert (o.loc[o.year >= 2027, "gwh_saved"] > 0).all()


# --- inflation by category, salary, activity catalogue -----------------------
from costguide import catalog, inflation, salary


def test_division_forecast_adds_up_to_headline():
    scen = forecast.scenarios()
    t = inflation.division_table(scen)
    assert t["weight"].sum() == pytest.approx(100, abs=0.2)
    h = inflation.headline_check(t)
    assert h["headline_2027"] == pytest.approx(forecast.annual_average(scen, "central", 2027), abs=0.05)
    assert h["headline_2028"] == pytest.approx(forecast.annual_average(scen, "baseline", 2028), abs=0.05)


def test_salary_nitaqat_and_allowance():
    assert salary.take_home(4300, "private_saudi", 2029) == pytest.approx(6000 * (1 - 0.0975))
    assert salary.take_home(9000, "gov", 2027) == 9500
    assert salary.take_home(9000, "expat", 2028) == 9000


def test_catalog_margins_match_benchmarks():
    t = catalog.catalog_table()
    acts = data.activity_catalog().set_index("id")
    ok = (t.set_index("id")["margin_2026"] - acts["margin_pct"]).abs() < 0.01
    assert ok.mean() > 0.9   # 'other' balances to the benchmark margin unless costs already exceed it
    assert len(t) >= 70
    assert (t["d_electricity"] > 0).all()


def test_catalog_pnl_lines():
    row = data.activity_catalog().set_index("id").loc["restaurant"]
    inp = catalog.inputs_from_activity(row.reset_index().set_index("index")[row.name] if False else row)
    p = catalog.pnl(inp)
    assert p.loc["total_cost", 2028] > p.loc["total_cost", 2026]
    assert p.loc["revenue", 2026] == 12 * 15 * 17000


# --- Nitaqat calculator ------------------------------------------------------
from costguide import nitaqat


def test_nitaqat_formula_matches_published_example():
    r = nitaqat.required(7, 100, 2026)  # manufacturing, 100 staff (noqta.tn example)
    assert r["lg"] == pytest.approx(22.82, abs=0.01)
    assert r["mg"] == pytest.approx(30.48, abs=0.01)
    assert r["hg"] == pytest.approx(33.55, abs=0.01)
    assert r["pl"] == pytest.approx(39.45, abs=0.01)


def test_hires_needed_example():
    assert nitaqat.hires_needed(30, 20, 100) == 15


def test_threshold_changes_counting():
    staff = {"saudi_full": [4500] * 10 + [7000] * 10, "non_saudi": 80}
    a26 = nitaqat.assess(7, staff, 2026)
    a27 = nitaqat.assess(7, staff, 2027)
    assert a26["weighted_saudis"] == 20
    assert a27["weighted_saudis"] == 15          # 4,500 SAR staff count half once the threshold is 5,000
    assert a27["saudization_pct"] < a26["saudization_pct"]


def test_isic_classes_complete():
    d = data.isic4_classes()
    assert len(d) >= 395 and not d["code"].duplicated().any()
    acts = set(data.activity_catalog()["id"])
    assert set(d["profile"]) <= acts
    assert set(d["nitaqat_id"]) <= set(data.nitaqat_activities()["id"])


# --- water: network vs tankers -----------------------------------------------
from costguide import water


def test_tanker_cost_and_need():
    t = water.tanker_cost(143, 19, 2, rise_pct=10)
    assert t["old_month"] == 286 and t["new_month"] == pytest.approx(314.6)
    assert water.tankers_needed(43, 19) == 2.5
    assert water.monthly_m3(6, 240) == pytest.approx(43.2)


def test_network_cost_matches_tariff():
    n = water.network_cost(30)
    assert n["new_month"] == pytest.approx((15 * 1.5 + 15 * 3 + 30) * 1.15)
