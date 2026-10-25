"""Commercial, industrial and agricultural impact: tariffs + Nitaqat wages together.

Archetypes are illustrative businesses (data/raw/business_archetypes.csv); their
consumption, revenue and staff are assumptions chosen to be typical, not data
about real firms. Bills exclude VAT, which VAT-registered businesses reclaim.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data
from .tariffs import BREAKER_CLASSES, sector_bill, sector_fixed_fee


def parse_wages(spec) -> list[float]:
    """'4000x3|5000' -> [4000, 4000, 4000, 5000]"""
    out: list[float] = []
    for part in str(spec).split("|"):
        if "x" in part:
            w, n = part.split("x")
            out += [float(w)] * int(n)
        elif part.strip():
            out.append(float(part))
    return out


def nitaqat_raise(wages: list[float], threshold: float) -> float:
    """Monthly wage increase needed to bring every Saudi below `threshold` up to it."""
    return float(sum(max(0.0, threshold - w) for w in wages))


def archetype_impact(row: pd.Series) -> dict:
    sector = row["sector"]
    old = sector_bill(row["kwh_month"], row["breaker_a"], sector, "2018")
    new = sector_bill(row["kwh_month"], row["breaker_a"], sector, "2027")
    d_elec = 12 * (new.total - old.total)
    wages = parse_wages(row["saudi_wages_sar"])
    gosi = 1 + data.a("gosi_employer_rate_saudi_pct") / 100
    d_w5 = 12 * nitaqat_raise(wages, 5000) * gosi
    d_w6 = 12 * nitaqat_raise(wages, 6000) * gosi
    rev = 12 * float(row["revenue_month_sar"])
    profit = rev * float(row["net_margin_pct"]) / 100
    pct = lambda x, base: round(100 * x / base, 2) if base else None
    return {
        "id": row["id"], "group": row["group"], "sector": sector,
        "name_ar": row["name_ar"], "name_en": row["name_en"],
        "kwh_month": int(row["kwh_month"]), "breaker_a": int(row["breaker_a"]),
        "elec_old_year": round(12 * old.total), "elec_new_year": round(12 * new.total),
        "elec_change_year": round(d_elec), "elec_change_pct": round(100 * (new.total / old.total - 1), 1),
        "fixed_old_year": round(12 * old.fixed), "fixed_new_year": round(12 * new.fixed),
        "saudi_staff": len(wages), "saudis_below_5000": sum(w < 5000 for w in wages),
        "saudis_below_6000": sum(w < 6000 for w in wages),
        "wage_cost_5000_year": round(d_w5), "wage_cost_6000_year": round(d_w6),
        "total_cost_2028_year": round(d_elec + d_w6),
        "revenue_year": round(rev),
        "elec_change_pct_of_revenue": pct(d_elec, rev),
        "total_pct_of_revenue": pct(d_elec + d_w6, rev),
        "total_pct_of_profit": pct(d_elec + d_w6, profit),
        "price_rise_to_pass_on_pct": pct(d_elec + d_w6, rev),
        "elec_share_of_revenue_old_pct": pct(12 * old.total, rev),
        "net_margin_pct": float(row["net_margin_pct"]), "saudi_wages": wages,
    }


def archetype_table() -> pd.DataFrame:
    return pd.DataFrame([archetype_impact(r) for _, r in data.business_archetypes().iterrows()])


def sector_aggregates(level: str = "value") -> pd.DataFrame:
    """Extra annual electricity cost by sector (bn SAR, before VAT): energy + fixed charges."""
    total = data.a("total_electricity_gwh_2024")
    shares = data.a("sector_shares_2024")
    accounts = data.a("nonres_accounts_million", level)
    mix = data.a("nonres_breaker_mix")
    t = data.sector_tariffs()
    rows = []
    for sector, share_key, label_ar in [("commercial", "commercial", "التجاري"), ("industrial", "industrial", "الصناعي"),
                                         ("government", "government", "الحكومي"), ("agricultural", "other", "الزراعي وغيره")]:
        gwh = total * shares[share_key] / 100
        g = t[t["sector"] == sector]
        # blended energy-rate change: average of the two tiers' halala change
        d_h = (g[g.schedule == "2027"]["rate_halala"].mean() - g[g.schedule == "2018"]["rate_halala"].mean())
        energy_bn = gwh * 1e6 * d_h / 100 / 1e9
        n = accounts[sector] * 1e6
        fee_bn = sum(n * share * 12 * (sector_fixed_fee(BREAKER_CLASSES[b], sector, "2027") -
                                       sector_fixed_fee(BREAKER_CLASSES[b], sector, "2018"))
                     for b, share in mix[sector].items()) / 1e9
        rows.append({"sector": sector, "sector_ar": label_ar, "gwh_2024": round(gwh),
                     "rate_change_halala": round(d_h, 1), "energy_extra_bn": round(energy_bn, 2),
                     "fixed_extra_bn": round(fee_bn, 2), "total_extra_bn": round(energy_bn + fee_bn, 2)})
    return pd.DataFrame(rows)


def passthrough_check() -> dict:
    """Does the assumed second-round CPI effect fit the size of the business cost shock?

    Second-round effect = private-sector extra cost (commercial + industrial +
    agricultural) x share passed to consumers / private consumption.
    """
    agg = sector_aggregates()
    private = agg[agg.sector != "government"]["total_extra_bn"].sum()
    consumption_bn = 1650.0  # CEIC 2024, ~USD 110 bn a quarter
    out = {"private_sector_extra_bn": round(private, 1),
           "government_extra_bn": round(float(agg[agg.sector == "government"]["total_extra_bn"].iloc[0]), 1)}
    for share in (0.3, 0.5, 0.7):
        out[f"cpi_pp_if_{int(share*100)}pct_passed"] = round(100 * private * share / consumption_bn, 2)
    return out
