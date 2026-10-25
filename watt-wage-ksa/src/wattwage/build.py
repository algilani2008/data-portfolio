"""Run the whole analysis: python -m wattwage.build

Writes
  outputs/*.csv               every result table
  outputs/summary.json        headline numbers (used by README and dashboard)
  dashboard/data.js           all data the dashboard needs (window.WW_DATA)
  reports/figures/*.png       static charts for the README
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import business, catalog, data, inflation, fiscal, forecast, household, impact, outlook, society, solutions, tariffs, wages
from .data import OUTPUTS, PROJECT_ROOT

FIG = PROJECT_ROOT / "reports" / "figures"
DASH = PROJECT_ROOT / "dashboard"

# reference palette (dataviz skill): categorical slots in fixed order
C = {"s1": "#2a78d6", "s2": "#eb6834", "s3": "#1baf7a", "s4": "#eda100",
     "text": "#0b0b0b", "muted": "#52514e", "grid": "#e4e3df", "surface": "#fcfcfb"}
SCHED_COLOR = {"pre2016": C["s3"], "2016": C["s4"], "2018": C["s1"], "2027": C["s2"]}


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else round(float(o), 4)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, float):
        return None if np.isnan(o) else round(o, 4)
    return o


def records(df: pd.DataFrame) -> list[dict]:
    return _clean(df.replace({np.nan: None}).to_dict(orient="records"))


def run(make_figures: bool = True) -> dict:
    OUTPUTS.mkdir(exist_ok=True)
    DASH.mkdir(exist_ok=True)

    # 1. tariffs
    e_curve = tariffs.electricity_curve()
    w_curve = tariffs.water_curve()
    sectors = tariffs.sector_comparison()

    # 2. households
    profiles = household.profile_summary()
    monthly = {p["id"]: records(household.annual_profile_bills(p)) for p in household.PROFILES}
    acc = household.simulate_accounts()
    deciles = household.decile_table(acc)
    nat = household.national_bill_change(acc, elasticity=data.a("price_elasticity_short_run"))

    # 3. past reforms
    events = impact.event_table()
    windows = impact.event_windows()

    # 4. forecast
    base = forecast.baseline()
    scen = forecast.scenarios(base)
    scen_summary = scen.attrs["summary"]
    mc = forecast.monte_carlo(base=base)
    torn = forecast.tornado()
    bt = forecast.backtest()

    # 5. wages + fiscal
    wt = wages.threshold_table()
    wcurve = wages.threshold_curve(0.4)
    whist = wages.wage_histogram(0.4)
    whist_check = wages.history_check()
    ftab = fiscal.fiscal_table()
    rev = fiscal.residential_revenue()
    calib = fiscal.calibration_2018()

    # 6. business, society, solutions, outlook
    biz = business.archetype_table()
    sec_agg = business.sector_aggregates()
    pt_check = business.passthrough_check()
    burden = society.burden_table()
    cover = society.coverage()
    resp = society.consumption_response()
    measures = solutions.measure_table()
    bundle = {p["id"]: solutions.best_bundle(p["id"]) for p in household.PROFILES}
    policies = solutions.policy_options()
    outl = outlook.outlook_table(base, scen)
    divs = inflation.division_table(scen)
    cat_tab = catalog.catalog_table()
    egrid = []
    for e in np.round(np.arange(-0.30, 0.001, 0.025), 3):
        nb_e = household.national_bill_change(acc, elasticity=float(e))
        egrid.append({"elasticity": float(e), "elec_change_pct": round(nb_e["elec_change_pct"], 2),
                      "water_change_pct": round(nb_e["water_change_pct"], 2)})

    for name, df in {
        "electricity_bill_curves": e_curve, "water_bill_curves": w_curve,
        "sector_tariff_changes": sectors, "household_profiles": profiles,
        "bill_change_by_decile": deciles, "past_reform_event_study": events,
        "cpi_forecast_scenarios": scen.drop(columns=[]), "cpi_scenario_shocks": scen_summary,
        "cpi_monte_carlo": mc.round(4), "shock_sensitivity": torn,
        "nitaqat_threshold_impact": wt, "nitaqat_threshold_curve": wcurve,
        "saudi_private_wage_histogram": whist, "support_cost": ftab,
        "business_archetypes_impact": biz, "sector_extra_cost": sec_agg, "household_burden": burden,
        "savings_measures": measures, "policy_options": policies, "outlook_2025_2030": outl,
        "cpi_by_category_2027_2028": divs, "activity_catalog_impact": cat_tab,
    }.items():
        df.to_csv(OUTPUTS / f"{name}.csv", index=False, encoding="utf-8")

    q = mc["inflation_2027"].quantile([0.1, 0.5, 0.9]).round(2).tolist()
    central = scen_summary.set_index("scenario").loc["central"]
    w5 = wt[(wt.threshold == 5000) & (wt.bunching == 0.4) & (wt.compliance == 1.0)].iloc[0]
    w6 = wt[(wt.threshold == 6000) & (wt.bunching == 0.4) & (wt.compliance == 1.0)].iloc[0]
    typical = profiles.set_index("id").loc["typical"]
    summary = _clean({
        "generated": pd.Timestamp.now(tz="Asia/Riyadh").strftime("%Y-%m-%d"),
        "electricity": {
            "avg_bill_change_pct": round(nat["elec_change_pct"], 1),
            "avg_bill_old_year": round(nat["elec_old"]), "avg_bill_new_year": round(nat["elec_new"]),
            "decile1_change_pct": float(deciles.iloc[0]["change_pct"]),
            "decile10_change_pct": float(deciles.iloc[-1]["change_pct"]),
        },
        "water": {"avg_bill_change_pct": round(nat["water_change_pct"], 1)},
        "typical_household": {
            "old_year": int(typical["total_old_year"]), "new_year": int(typical["total_new_year"]),
            "increase_year": int(typical["increase_year"]), "increase_pct": float(typical["increase_pct"]),
            "support_year": 12 * data.a("support_monthly_sar"),
        },
        "inflation": {
            "baseline_2027": forecast.annual_average(scen, "baseline", 2027),
            "central_2027": forecast.annual_average(scen, "central", 2027),
            "low_2027": forecast.annual_average(scen, "low", 2027),
            "high_2027": forecast.annual_average(scen, "high", 2027),
            "central_2028": forecast.annual_average(scen, "central", 2028),
            "mc_p10_p50_p90_2027": q,
            "shock_total_pp": float(central["total_pp"]), "shock_direct_pp": float(central["direct_pp"]),
            "backtest": bt,
        },
        "past_reforms": records(events),
        "wages": {
            "workers_below_5000": int(w5["workers_below"]), "share_below_5000_pct": float(w5["share_below_pct"]),
            "employer_cost_5000_bn": float(w5["employer_cost_bn_sar_year"]),
            "workers_below_6000": int(w6["workers_below"]), "share_below_6000_pct": float(w6["share_below_pct"]),
            "employer_cost_6000_bn": float(w6["employer_cost_bn_sar_year"]),
            "history": whist_check,
        },
        "fiscal": {"support_cost_bn": records(ftab), "calibration_2018": calib, "residential_revenue": rev},
        "business": {"sector_extra": records(sec_agg), "passthrough_check": pt_check},
        "society": {"coverage": cover, "response": resp},
        "solutions": {"bundles": bundle},
        "inflation_by_category": inflation.headline_check(divs),
        "catalog": {"activities": int(len(cat_tab)),
                    "median_price_rise_pct": float(cat_tab.price_rise_to_keep_profit_pct.median()),
                    "max_price_rise": records(cat_tab.nlargest(3, "price_rise_to_keep_profit_pct")[["id", "name_ar", "name_en", "price_rise_to_keep_profit_pct"]])},
    })
    with open(OUTPUTS / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    cpi = data.cpi_monthly()
    dash = _clean({
        "summary": summary,
        "tariffs": {
            "electricity": records(data.electricity_tariffs()[["schedule", "tier_from_kwh", "tier_to_kwh", "rate_halala"]]),
            "electricity_fees": records(data.electricity_fixed_fees()[["schedule", "breaker_from_a", "breaker_to_a", "fee_sar"]]),
            "water": records(data.water_tariffs()[["schedule", "tier_from_m3", "tier_to_m3", "water_sar", "sewage_sar"]]),
            "water_fees": records(data.water_fixed_fees()),
            "sectors": records(sectors),
        },
        "curves": {"electricity": records(e_curve[e_curve.kwh % 200 == 0]), "water": records(w_curve)},
        "profiles": records(profiles), "profile_months": monthly, "deciles": records(deciles),
        "cpi": [{"month": str(m), "yoy": v} for m, v in cpi.items()],
        "forecast": records(scen), "scenario_summary": records(scen_summary),
        "mc_hist": _hist(mc["inflation_2027"]), "tornado": records(torn),
        "events": records(events), "event_windows": records(windows),
        "policy_events": records(data.policy_events()),
        "wages": {"table": records(wt), "curve": records(wcurve), "hist": records(whist)},
        "fiscal": records(ftab),
        "assumptions": data.assumptions(),
        "seasonality": list(household.seasonality()),
        "business": records(biz), "sector_extra": records(sec_agg),
        "sector_tariffs": records(data.sector_tariffs()[["sector", "schedule", "tier_from_kwh", "tier_to_kwh", "rate_halala"]]),
        "sector_fees": records(data.sector_fixed_fees()[["fee_group", "schedule", "breaker_from_a", "breaker_to_a", "fee_sar"]]),
        "burden": records(burden), "measures": records(measures), "policies": records(policies),
        "outlook": records(outl), "elasticity_grid": egrid, "measure_defs": records(data.savings_measures()),
        "divisions": records(divs), "activities": records(data.activity_catalog().drop(columns=["note"]).assign(note=data.activity_catalog()["note"].fillna(""))),
        "catalog": records(cat_tab), "solar_shape": list(solutions.SOLAR_SHAPE),
    })
    with open(DASH / "data.js", "w", encoding="utf-8") as f:
        f.write("// generated by `python -m wattwage.build` - do not edit\n")
        f.write("window.WW_DATA = " + json.dumps(dash, ensure_ascii=False, separators=(",", ":")) + ";\n")

    write_sql_data(profiles)
    write_index_html()
    if make_figures:
        figures(e_curve, cpi, scen, windows, deciles, whist, biz, burden)
    return summary


def write_index_html() -> None:
    """dashboard/_page.html is the page body (also published as-is); wrap it as a full document for GitHub Pages."""
    page = (DASH / "_page.html").read_text(encoding="utf-8")
    cut = page.index('<header class="top')
    head, body = page[:cut], page[cut:]
    html = ('<!doctype html>\n<html lang="ar" dir="rtl">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + head + "</head>\n<body>\n" + body + "</body>\n</html>\n")
    (DASH / "index.html").write_text(html, encoding="utf-8")


def write_sql_data(profiles: pd.DataFrame) -> None:
    def lit(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "NULL"
        if isinstance(v, (int, float, np.integer, np.floating)):
            return str(int(v)) if float(v).is_integer() else str(float(v))
        return "'" + str(v).replace("'", "''") + "'"

    def inserts(table, df):
        return [f"INSERT INTO {table} ({', '.join(df.columns)}) VALUES ({', '.join(lit(v) for v in row)});"
                for row in df.itertuples(index=False)]

    lines = ["-- generated by `python -m wattwage.build`", "BEGIN;"]
    lines += inserts("electricity_tariffs", data.electricity_tariffs()[["schedule", "tier_from_kwh", "tier_to_kwh", "rate_halala"]])
    lines += inserts("electricity_fees", data.electricity_fixed_fees()[["schedule", "breaker_from_a", "breaker_to_a", "fee_sar"]])
    lines += inserts("water_tariffs", data.water_tariffs()[["schedule", "tier_from_m3", "tier_to_m3", "water_sar", "sewage_sar"]])
    cpi = data.cpi_monthly()
    lines += inserts("cpi_monthly", pd.DataFrame({"month": cpi.index.astype(str), "cpi_yoy_pct": cpi.values}))
    lines += inserts("policy_events", data.policy_events()[["date", "category", "title_ar", "title_en"]])
    lines += inserts("household_profiles", profiles[["id", "name_ar", "kwh_month", "water_m3", "total_old_year", "total_new_year"]])
    lines.append("COMMIT;")
    (PROJECT_ROOT / "sql" / "02_data.sql").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _hist(s: pd.Series, bins: int = 30) -> list[dict]:
    counts, edges = np.histogram(s, bins=bins)
    return [{"x0": round(float(a), 3), "x1": round(float(b), 3), "n": int(c)}
            for a, b, c in zip(edges[:-1], edges[1:], counts)]


def figures(e_curve, cpi, scen, windows, deciles, whist, biz=None, burden=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIG.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.size": 10, "axes.edgecolor": C["grid"], "axes.labelcolor": C["muted"],
        "xtick.color": C["muted"], "ytick.color": C["muted"], "axes.grid": True,
        "grid.color": C["grid"], "grid.linewidth": 0.6, "axes.spines.top": False,
        "axes.spines.right": False, "figure.facecolor": C["surface"], "axes.facecolor": C["surface"],
        "legend.frameon": False, "lines.linewidth": 2,
    })

    def finish(ax, title, name):
        ax.set_title(title, loc="left", color=C["text"], fontsize=12, fontweight="bold")
        ax.figure.tight_layout()
        ax.figure.savefig(FIG / name, dpi=160)
        plt.close(ax.figure)

    # tariff history
    fig, ax = plt.subplots(figsize=(8, 4.2))
    labels = {"pre2016": "Before 2016", "2016": "2016", "2018": "2018 (current)", "2027": "2027"}
    for s, g in e_curve.groupby("schedule", sort=False):
        g = g[g.kwh <= 10000]
        ax.plot(g.kwh, g.bill_sar, color=SCHED_COLOR[s], label=labels[s])
    ax.set_xlabel("Monthly consumption (kWh)"); ax.set_ylabel("Monthly bill, SAR (before VAT)")
    ax.legend(loc="upper left")
    finish(ax, "Residential electricity bill by tariff schedule", "tariff_history.png")

    # CPI history + forecast
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ts = cpi.index.to_timestamp()
    ax.plot(ts, cpi.values, color=C["muted"], linewidth=1.6, label="Actual (y/y %)")
    ft = pd.PeriodIndex(scen["month"], freq="M").to_timestamp()
    ax.fill_between(ft, scen["lo80"], scen["hi80"], color=C["s1"], alpha=0.15, linewidth=0)
    ax.plot(ft, scen["baseline"], color=C["s1"], linestyle="--", label="No-reform baseline")
    ax.fill_between(ft, scen["low"], scen["high"], color=C["s2"], alpha=0.18, linewidth=0)
    ax.plot(ft, scen["central"], color=C["s2"], label="With 2027 tariffs (central)")
    for m, lab in [("2016-01", "2016 reform"), ("2018-01", "2018 reform + VAT"), ("2020-07", "VAT 15%"), ("2027-01", "2027 tariffs")]:
        x = pd.Period(m, "M").to_timestamp()
        ax.axvline(x, color=C["grid"], linewidth=1, zorder=0)
        ax.text(x, 7.3, " " + lab, fontsize=8, color=C["muted"], ha="left", va="top")
    ax.set_ylim(-3.6, 7.6)
    ax.axhline(0, color=C["muted"], linewidth=0.6)
    ax.set_ylabel("CPI inflation, % y/y"); ax.legend(loc="lower left", fontsize=8)
    finish(ax, "Saudi inflation: history and 2027-2028 forecast", "cpi_forecast.png")

    # event study
    fig, ax = plt.subplots(figsize=(8, 4))
    for (ev, g), col in zip(windows.groupby("event", sort=False), [C["s1"], C["s2"], C["s3"]]):
        ax.plot(g.h, g.cpi_yoy_pct, color=col, label=ev)
    ax.axvline(0, color=C["muted"], linewidth=0.8); ax.axvline(12, color=C["muted"], linewidth=0.8, linestyle=":")
    ax.set_xlabel("Months from reform"); ax.set_ylabel("CPI inflation, % y/y"); ax.legend(fontsize=8)
    finish(ax, "Past reforms lift inflation for 12 months, then drop out", "event_study.png")

    # deciles
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(deciles.decile, deciles.change_pct, color=C["s2"], width=0.7)
    for x, y in zip(deciles.decile, deciles.change_pct):
        ax.text(x, y + 1.5, f"{y:.0f}%", ha="center", fontsize=8, color=C["text"])
    ax.set_xticks(deciles.decile); ax.set_xlabel("Consumption decile (1 = smallest users)")
    ax.set_ylabel("Annual electricity bill change, %")
    finish(ax, "The new fixed charge hits small users hardest", "bill_change_deciles.png")

    # wage histogram
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(whist["from"] + 125, whist.workers / 1000, width=230, color=C["s1"])
    top = ax.get_ylim()[1]
    for (t, lab), yf in zip([(4000, "4,000 now"), (5000, "5,000 (2027)"), (6000, "6,000 (2028)")], [0.97, 0.85, 0.73]):
        ax.axvline(t, color=C["s2"], linewidth=1.5)
        ax.text(t + 60, top * yf, lab, color=C["text"], fontsize=8, va="top")
    ax.set_xlabel("Monthly wage, SAR"); ax.set_ylabel("Saudi private-sector workers (thousands)")
    finish(ax, "Saudi private-sector wages vs. Nitaqat thresholds (modelled)", "wage_thresholds.png")


    if biz is not None:
        b = biz[biz.revenue_year > 0].copy()
        b["elec"] = 100 * b.elec_change_year / b.revenue_year
        b["wage"] = 100 * b.wage_cost_6000_year / b.revenue_year
        b = b.assign(tot=b.elec + b.wage).sort_values("tot", ascending=True)
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh(b.name_en, b.elec, color=C["s2"], label="Electricity tariff", height=0.6)
        ax.barh(b.name_en, b.wage, left=b.elec, color=C["s1"], label="Nitaqat 6,000 SAR wages", height=0.6)
        ax.set_xlabel("Extra annual cost, % of revenue"); ax.legend(loc="lower right"); ax.grid(axis="y", visible=False)
        finish(ax, "Extra cost by business type (2028, before price pass-through)", "business_cost.png")
    if burden is not None:
        d = burden.sort_values("net_pct_income")
        fig, ax = plt.subplots(figsize=(8, 4.2))
        cols = [C["s2"] if v < 0 else C["s3"] for v in d.net_pct_income]
        ax.barh(d.name_en, d.net_pct_income, color=cols, height=0.6)
        ax.axvline(0, color=C["muted"], linewidth=0.8)
        for y, v in enumerate(d.net_pct_income):
            ax.text(v + (0.4 if v >= 0 else -0.4), y, f"{v:+.1f}%", va="center", ha="left" if v >= 0 else "right", fontsize=8, color=C["text"])
        ax.set_xlabel("Net yearly position after allowance and wage uplift, % of income"); ax.grid(axis="y", visible=False)
        ax.set_xlim(min(d.net_pct_income) - 3, max(d.net_pct_income) + 4)
        finish(ax, "Who gains and who loses by 2028", "household_net.png")

if __name__ == "__main__":
    s = run()
    print(json.dumps({k: s[k] for k in ("electricity", "water", "inflation", "wages")}, ensure_ascii=False, indent=2))
