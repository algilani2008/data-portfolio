"""Business P&L 2026 -> 2027 -> 2028 for any activity in data/raw/activity_catalog.csv.

Each activity row holds indicative benchmarks (employees, kWh and revenue per
employee, cost shares, margin, Saudization and wage mix). They are starting values
for the calculator, not statistics about the sector. The dashboard mirrors this
logic in JavaScript; tests check that the two agree.

Cost lines: materials, rent, Saudi wages (low < 5,000 / mid 5,000-6,000 / high),
expat wages, employer GOSI on Saudi wages, electricity (sector tariff, ex-VAT),
water (assumed non-residential rate), other (balancing item so the 2026 margin
matches the benchmark).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import data
from .tariffs import sector_bill

YEARS = (2026, 2027, 2028)


def breaker_for(kwh_month: float) -> int:
    if kwh_month < 5000:
        return 60
    if kwh_month < 15000:
        return 150
    if kwh_month < 40000:
        return 250
    return 350


@dataclass
class Inputs:
    tariff: str
    revenue_month: float
    materials_month: float
    rent_month: float
    kwh_month: float
    breaker_a: int
    water_m3_month: float
    saudi_low: int
    saudi_low_wage: float
    saudi_mid: int
    saudi_mid_wage: float
    saudi_high: int
    saudi_high_wage: float
    expats: int
    expat_wage: float
    other_month: float = None  # filled from the benchmark margin when None
    margin_pct: float = 10.0
    infl: dict = field(default_factory=dict)  # {"materials":{2027:..,2028:..}, "rent":.., "other":..}
    comply: bool = True


def inputs_from_activity(row: pd.Series | dict, employees: int | None = None) -> Inputs:
    r = dict(row)
    e = int(employees if employees is not None else r["employees"])
    saudis = round(e * r["saudi_share"])
    low = round(saudis * r["saudi_low_share"])
    mid = round(saudis * r["saudi_mid_share"])
    high = max(0, saudis - low - mid)
    kwh = e * r["kwh_per_emp"]
    rev = e * r["revenue_per_emp"]
    return Inputs(tariff=r["tariff"], revenue_month=rev, materials_month=rev * r["materials_pct"] / 100,
                  rent_month=rev * r["rent_pct"] / 100, kwh_month=kwh, breaker_a=breaker_for(kwh),
                  water_m3_month=e * r["water_m3_per_emp"], saudi_low=low, saudi_low_wage=data.a("saudi_low_wage_default"),
                  saudi_mid=mid, saudi_mid_wage=data.a("saudi_mid_wage_default"), saudi_high=high,
                  saudi_high_wage=r["saudi_high_wage"], expats=e - saudis, expat_wage=r["expat_wage"],
                  margin_pct=r["margin_pct"])


def default_inflation(div: pd.DataFrame | None = None) -> dict:
    """Cost-line inflation from the CPI forecast (headline for materials/other, rent assumption)."""
    from . import inflation
    t = inflation.division_table() if div is None else div
    h = inflation.headline_check(t)
    return {"materials": {2027: h["headline_2027"], 2028: h["headline_2028"]},
            "other": {2027: h["headline_2027"], 2028: h["headline_2028"]},
            "rent": {2027: data.a("rent_inflation_pct"), 2028: data.a("rent_inflation_pct")}}


def _saudi_wage_month(w: float, year: int, comply: bool) -> float:
    """Average monthly wage in `year` for a Saudi on `w` in 2026 (Nitaqat phases)."""
    if not comply:
        return w
    if year == 2027:
        return (w * 4 + max(w, 5000) * 8) / 12
    if year == 2028:
        return (max(w, 5000) * 4 + max(w, 6000) * 8) / 12
    return w


def pnl(inp: Inputs) -> pd.DataFrame:
    """Annual P&L lines for 2026, 2027, 2028 (SAR)."""
    gosi = data.a("gosi_employer_rate_saudi_pct") / 100
    g_exp = data.a("expat_wage_growth_pct") / 100
    g_sau = data.a("saudi_wage_growth_pct") / 100
    w_rate = data.a("nonres_water_sar_per_m3")
    w_chg = data.a("nonres_water_change_pct") / 100
    infl = inp.infl or default_inflation()
    lines = {}
    for y in YEARS:
        k = y - 2026
        cum = lambda key: (1.0 if k == 0 else (1 + infl[key][2027] / 100) * (1 if k == 1 else 1 + infl[key][2028] / 100))
        sched = "2018" if y == 2026 else "2027"
        eb = sector_bill(inp.kwh_month, inp.breaker_a, inp.tariff, sched)
        sw_nitaqat = 12 * (inp.saudi_low * _saudi_wage_month(inp.saudi_low_wage, y, inp.comply) +
                           inp.saudi_mid * _saudi_wage_month(inp.saudi_mid_wage, y, inp.comply))
        sw_high = 12 * inp.saudi_high * inp.saudi_high_wage * (1 + g_sau) ** k
        lines[y] = {
            "materials": 12 * inp.materials_month * cum("materials"),
            "rent": 12 * inp.rent_month * cum("rent"),
            "saudi_wages_threshold": sw_nitaqat,
            "saudi_wages_other": sw_high,
            "gosi_employer": gosi * (sw_nitaqat + sw_high),
            "expat_wages": 12 * inp.expats * inp.expat_wage * (1 + g_exp) ** k,
            "electricity": 12 * (eb.energy + eb.fixed),
            "water": 12 * inp.water_m3_month * w_rate * (1 if y == 2026 else 1 + w_chg),
        }
    base_costs = sum(lines[2026].values())
    rev = 12 * inp.revenue_month
    other0 = inp.other_month * 12 if inp.other_month is not None else max(0.0, rev * (1 - inp.margin_pct / 100) - base_costs)
    for y in YEARS:
        k = y - 2026
        f = 1.0 if k == 0 else (1 + infl["other"][2027] / 100) * (1 if k == 1 else 1 + infl["other"][2028] / 100)
        lines[y]["other"] = other0 * f
    df = pd.DataFrame(lines)
    df.loc["total_cost"] = df.sum()
    df.loc["revenue"] = rev
    df.loc["profit"] = df.loc["revenue"] - df.loc["total_cost"]
    df.loc["margin_pct"] = 100 * df.loc["profit"] / rev if rev else 0.0
    return df.round(2)


def summary(inp: Inputs) -> dict:
    p = pnl(inp)
    rev = float(p.loc["revenue", 2026])
    d = (p[2028] - p[2026]).drop(["revenue", "profit", "margin_pct", "total_cost"])
    dtot = float(p.loc["total_cost", 2028] - p.loc["total_cost", 2026])
    return {"revenue_year": rev, "cost_2026": float(p.loc["total_cost", 2026]),
            "cost_2027": float(p.loc["total_cost", 2027]), "cost_2028": float(p.loc["total_cost", 2028]),
            "cost_increase_2028_pct": round(100 * dtot / float(p.loc["total_cost", 2026]), 2) if p.loc["total_cost", 2026] else None,
            "margin_2026": float(p.loc["margin_pct", 2026]), "margin_2028_no_price_change": float(p.loc["margin_pct", 2028]),
            "price_rise_to_keep_profit_pct": round(100 * dtot / rev, 2) if rev else None,
            "breakdown_2028": {k: round(float(v)) for k, v in d.items()}}


def catalog_table() -> pd.DataFrame:
    inf = default_inflation()
    g = data.a("gosi_employer_rate_saudi_pct") / 100
    rows = []
    for _, r in data.activity_catalog().iterrows():
        inp = inputs_from_activity(r)
        inp.infl = inf
        p = pnl(inp)
        d = p[2028] - p[2026]
        rev = float(p.loc["revenue", 2026])
        c0 = float(p.loc["total_cost", 2026])
        dt = float(d["total_cost"])
        rows.append({"id": r["id"], "group": r["group"], "isic": r["isic"], "name_ar": r["name_ar"], "name_en": r["name_en"],
                     "employees": int(r["employees"]), "revenue_year": round(rev), "cost_2026": round(c0),
                     "elec_2026": round(float(p.loc["electricity", 2026])),
                     "d_electricity": round(float(d["electricity"])), "d_water": round(float(d["water"])),
                     "d_nitaqat_wages": round(float(d["saudi_wages_threshold"]) * (1 + g)),
                     "d_other_wages": round(float(d["saudi_wages_other"]) * (1 + g) + float(d["expat_wages"])),
                     "d_inputs_inflation": round(float(d["materials"] + d["rent"] + d["other"])),
                     "d_total": round(dt),
                     "cost_increase_2028_pct": round(100 * dt / c0, 2),
                     "price_rise_to_keep_profit_pct": round(100 * dt / rev, 2),
                     "margin_2026": round(float(p.loc["margin_pct", 2026]), 2),
                     "margin_2028_no_price_change": round(float(p.loc["margin_pct", 2028]), 2),
                     "elec_share_of_revenue_pct": round(100 * float(p.loc["electricity", 2026]) / rev, 2)})
    return pd.DataFrame(rows)
