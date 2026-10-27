"""Society-wide view: who is covered by support, net burden by household type, environment."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data
from .household import PROFILES, _account_elec_year, profile_summary, seasonality, simulate_accounts
from .tariffs import BREAKER_CLASSES, electricity_bill_vec, water_bill_vec


def burden_table() -> pd.DataFrame:
    """Net yearly position of typical household types once the 2028 Nitaqat phase is in place."""
    prof = profile_summary().set_index("id")
    rows = []
    for _, h in data.society_households().iterrows():
        p = prof.loc[h["profile"]]
        inc = float(p["increase_year"])
        allowance = 12 * float(h["allowance_sar"])
        wage1 = 12 * float(h["wage_uplift_phase1_sar"])
        wage2 = 12 * float(h["wage_uplift_phase2_sar"])
        income = 12 * float(h["monthly_income_sar"])
        net = allowance + wage2 - inc
        rows.append({
            "id": h["id"], "name_ar": h["name_ar"], "name_en": h["name_en"], "profile": h["profile"],
            "income_year": round(income), "bill_increase_year": round(inc),
            "bill_increase_pct_income": round(100 * inc / income, 2),
            "allowance_year": round(allowance), "wage_uplift_2027_year": round(wage1), "wage_uplift_2028_year": round(wage2),
            "net_2028_year": round(net), "net_pct_income": round(100 * net / income, 2),
            "status": "gain" if net > 0 else ("loss" if net < 0 else "neutral"),
        })
    return pd.DataFrame(rows)


def coverage() -> dict:
    """How many metered households receive any compensation."""
    saudi = data.a("saudi_households_m")
    share = data.a("saudi_hh_with_allowance_share")
    expat = data.a("expat_metered_households_m")
    covered = saudi * share
    return {"saudi_households_m": saudi, "saudi_covered_m": round(covered, 2),
            "saudi_not_covered_m": round(saudi - covered, 2), "expat_households_m": expat,
            "covered_share_of_metered_pct": round(100 * covered / (saudi + expat), 1)}


def consumption_response(elasticity: float | None = None) -> dict:
    """Aggregate residential kWh and water reduction from the price response."""
    e = data.a("price_elasticity_short_run") if elasticity is None else elasticity
    acc = simulate_accounts()
    kwh_old = kwh_new = 0.0
    for br, amps in BREAKER_CLASSES.items():
        mask = (acc["breaker"] == br).to_numpy()
        for f in seasonality():
            q = acc.loc[mask, "kwh_month"].to_numpy() * f
            ratio = electricity_bill_vec(q, amps, "2027") / electricity_bill_vec(q, amps, "2018")
            kwh_old += q.sum()
            kwh_new += (q * ratio ** e).sum()
    m3 = acc["m3_month"].to_numpy()
    wr = water_bill_vec(m3, "2027") / water_bill_vec(m3, "2016", vat=0.15)
    water_pct = 100 * ((m3 * wr ** e).sum() / m3.sum() - 1)
    pct = 100 * (kwh_new / kwh_old - 1)
    gwh_saved = -pct / 100 * data.a("residential_electricity_gwh_2024")
    co2_mt = gwh_saved * 1e6 * data.a("grid_co2_kg_per_kwh") / 1e9
    barrels_m = gwh_saved * 1e6 / data.a("kwh_per_barrel_electric") / 1e6 * data.a("oil_share_generation")
    return {"elasticity": e, "residential_kwh_change_pct": round(pct, 2), "gwh_saved_year": round(gwh_saved),
            "co2_mt_saved_year": round(co2_mt, 2),
            "oil_barrels_saved_m_year": round(barrels_m, 1),
            "oil_value_usd_m_year": round(barrels_m * data.a("oil_price_usd"), 0),
            "water_use_change_pct": round(water_pct, 2)}
