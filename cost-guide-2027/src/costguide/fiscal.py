"""Cost of the 500 SAR support vs. extra residential bill revenue (order of magnitude)."""
from __future__ import annotations

import pandas as pd

from . import data
from .household import national_bill_change, simulate_accounts


def support_cost(level: str = "value") -> dict:
    b = data.a("beneficiaries_million", level)
    m = data.a("support_monthly_sar")
    total_m = sum(b.values())
    return {"level": level, **{f"{k}_m": v for k, v in b.items()},
            "beneficiaries_m": round(total_m, 2),
            "cost_bn_sar_year": round(total_m * 1e6 * m * 12 / 1e9, 1)}


def calibration_2018() -> dict:
    """The same beneficiary counts priced at the 2018 package (1,000/500/500)."""
    b = data.a("beneficiaries_million")
    cost = (b["employees"] * 1000 + (b["retirees"] + b["social_security_families"]) * 500) * 12 / 1e3
    return {"model_cost_bn": round(cost, 1), "reported_cost_bn": data.a("support_2018_cost_bn_sar_year")}


def residential_revenue() -> dict:
    acc = simulate_accounts()
    nb = national_bill_change(acc, elasticity=data.a("price_elasticity_short_run"))
    n = data.a("residential_accounts_million") * 1e6
    return {
        "elec_extra_bn_sar_year": round((nb["elec_new"] - nb["elec_old"]) * n / 1e9, 1),
        "water_extra_bn_sar_year_upper": round((nb["water_new"] - nb["water_old"]) * n / 1e9, 1),
        "elec_avg_bill_old_year": round(nb["elec_old"]),
        "elec_avg_bill_new_year": round(nb["elec_new"]),
        "water_avg_bill_old_year": round(nb["water_old"]),
        "water_avg_bill_new_year": round(nb["water_new"]),
    }


def fiscal_table() -> pd.DataFrame:
    return pd.DataFrame([support_cost(l) for l in ("low", "value", "high")])
