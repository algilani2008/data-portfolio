"""Inflation by spending category (CPI division) for 2027 and 2028, and price-level helpers.

Division 04 (housing, water, electricity, gas) is split into utilities (electricity +
water, weights from assumptions.json) and housing excluding utilities. Without the
reform, each division keeps its current inflation scaled so the weighted total
equals the ARIMA baseline; utilities stay flat. With the reform, utilities rise by
the average bill change (direct effect) and the second-round effect is spread over
the other divisions by their weight x energy-intensity factor.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data, forecast


def division_table(scen: pd.DataFrame | None = None, shock: dict | None = None) -> pd.DataFrame:
    scen = forecast.scenarios() if scen is None else scen
    shock = forecast.central_shock() if shock is None else shock
    d = data.cpi_divisions()
    d = d[d["code"] != "00"].copy()
    we, ww = data.a("cpi_weight_electricity_pct"), data.a("cpi_weight_water_pct")
    util_w = we + ww
    rows = []
    for _, r in d.iterrows():
        if r["code"] == "04":
            rows.append({"code": "04h", "name_en": "Housing (rent, maintenance, gas)", "name_ar": "السكن (إيجار وصيانة وغاز)",
                         "weight": r["weight_pct"] - util_w, "yoy_q1_2026": r["chg_yoy_pct"]})
            rows.append({"code": "04u", "name_en": "Electricity & water", "name_ar": "الكهرباء والمياه",
                         "weight": util_w, "yoy_q1_2026": 0.0})
        else:
            rows.append({"code": r["code"], "name_en": r["division_en"], "name_ar": r["division_ar"],
                         "weight": r["weight_pct"], "yoy_q1_2026": r["chg_yoy_pct"]})
    t = pd.DataFrame(rows)
    b27 = forecast.annual_average(scen, "baseline", 2027)
    b28 = forecast.annual_average(scen, "baseline", 2028)
    non = t["code"] != "04u"
    raw = (t.loc[non, "weight"] * t.loc[non, "yoy_q1_2026"]).sum() / 100
    t["baseline_2027"] = np.where(non, t["yoy_q1_2026"] * b27 / raw, 0.0)
    t["baseline_2028"] = np.where(non, t["yoy_q1_2026"] * b28 / raw, 0.0)
    # direct effect: utilities rise by the weighted average bill change
    util_change = (we * shock["elec_bill_change_pct"] + ww * shock["water_bill_change_pct"]) / util_w
    # second-round: spread by weight x intensity
    f = data.a("indirect_energy_intensity")
    t["intensity"] = t["code"].map(lambda c: f.get(c[:2], 0.0) if c != "04u" else 0.0)
    wf = (t["weight"] * t["intensity"]).sum()
    contrib = shock["indirect_pp"] * t["weight"] * t["intensity"] / wf
    t["shock_pp_on_division"] = np.where(t["code"] == "04u", util_change, 100 * contrib / t["weight"])
    t["forecast_2027"] = t["baseline_2027"] + t["shock_pp_on_division"]
    t["forecast_2028"] = t["baseline_2028"]
    t["contribution_2027_pp"] = t["weight"] * t["forecast_2027"] / 100
    for c in ("weight", "baseline_2027", "baseline_2028", "shock_pp_on_division", "forecast_2027", "forecast_2028", "contribution_2027_pp"):
        t[c] = t[c].round(3)
    return t


def headline_check(t: pd.DataFrame) -> dict:
    return {"headline_2027": round(float((t.weight * t.forecast_2027).sum() / 100), 2),
            "headline_2028": round(float((t.weight * t.forecast_2028).sum() / 100), 2)}


def basket_value(amount: float, t: pd.DataFrame, code: str | None = None) -> dict:
    """What `amount` SAR of spending in 2026 costs in 2027 and 2028 (whole basket or one division)."""
    if code:
        r = t.set_index("code").loc[code]
        i27, i28 = r["forecast_2027"], r["forecast_2028"]
    else:
        h = headline_check(t)
        i27, i28 = h["headline_2027"], h["headline_2028"]
    v27 = amount * (1 + i27 / 100)
    return {"2026": amount, "2027": round(v27, 2), "2028": round(v27 * (1 + i28 / 100), 2)}


def personal_inflation(spending: dict[str, float], t: pd.DataFrame, year: str = "2027") -> float:
    """Personal inflation (%) from monthly spending per division code."""
    tot = sum(spending.values())
    if tot <= 0:
        return 0.0
    ix = t.set_index("code")[f"forecast_{year}"]
    return round(sum(v * ix[k] for k, v in spending.items()) / tot, 2)
