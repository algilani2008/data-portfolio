"""Year-by-year outlook 2025-2030: demand, bills, emissions, wages, fiscal, inflation."""
from __future__ import annotations

import pandas as pd

from . import data, forecast
from .household import national_bill_change, simulate_accounts
from .society import consumption_response
from .wages import threshold_impact


def outlook_table(base: pd.DataFrame | None = None, scen: pd.DataFrame | None = None) -> pd.DataFrame:
    base = forecast.baseline() if base is None else base
    scen = forecast.scenarios(base) if scen is None else scen
    g = data.a("residential_growth_pct_year") / 100
    gwh24 = data.a("residential_electricity_gwh_2024")
    resp = consumption_response()["residential_kwh_change_pct"] / 100
    nb = national_bill_change(simulate_accounts(), elasticity=data.a("price_elasticity_short_run"))
    co2 = data.a("grid_co2_kg_per_kwh")
    from .fiscal import support_cost
    support = support_cost()["cost_bn_sar_year"]
    w5 = threshold_impact(5000, 0.4)
    w6 = threshold_impact(6000, 0.4)
    infl_base_late = round(float(base["baseline"].iloc[-12:].mean()), 2)
    rows = []
    for y in range(2025, 2031):
        base_gwh = gwh24 * (1 + g) ** (y - 2024)
        with_gwh = base_gwh * (1 + resp) if y >= 2027 else base_gwh
        if y < 2027:
            infl_b = infl_c = None
        elif y <= 2028:
            infl_b = forecast.annual_average(scen, "baseline", y)
            infl_c = forecast.annual_average(scen, "central", y)
        else:
            infl_b = infl_c = infl_base_late
        # Nitaqat phases: phase 1 from late April 2027 (8 of 12 months), phase 2 from late April 2028
        wage_bn = {2027: w5["worker_gain_bn_sar_year"] * 8 / 12,
                   2028: w5["worker_gain_bn_sar_year"] * 4 / 12 + w6["worker_gain_bn_sar_year"] * 8 / 12}.get(
            y, w6["worker_gain_bn_sar_year"] if y > 2028 else 0.0)
        rows.append({
            "year": y, "residential_gwh_no_reform": round(base_gwh), "residential_gwh_with_reform": round(with_gwh),
            "gwh_saved": round(base_gwh - with_gwh), "co2_mt_saved": round((base_gwh - with_gwh) * 1e6 * co2 / 1e9, 2),
            "avg_elec_bill_year": round(nb["elec_new"] if y >= 2027 else nb["elec_old"]),
            "inflation_no_reform": infl_b, "inflation_with_reform": infl_c,
            "support_cost_bn": support if y >= 2027 else 0.0,
            "saudi_wage_gain_bn": round(wage_bn, 1),
            "nitaqat_threshold": 4000 if y < 2027 else (5000 if y == 2027 else 6000),
        })
    return pd.DataFrame(rows)
