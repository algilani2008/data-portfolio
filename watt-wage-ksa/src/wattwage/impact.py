"""Event study: what past reforms did to CPI inflation.

A one-off rise in the price level shows up in year-on-year inflation for exactly
12 months and then drops out (the base effect). For each reform we measure the
jump in the reform month and the reversal 12 months later; if the two are close,
the reform behaved like a one-off level shock rather than lasting inflation.
"""
from __future__ import annotations

import pandas as pd

from . import data

EVENTS = [
    {"month": "2016-01", "name_ar": "إصلاح الطاقة والمياه 2016", "name_en": "2016 energy & water reform",
     "includes_en": "electricity upper tiers, new water tariff, gasoline +50%"},
    {"month": "2018-01", "name_ar": "إصلاح الكهرباء + ضريبة 5% (2018)", "name_en": "2018 electricity reform + 5% VAT",
     "includes_en": "electricity 18/30 halalas, 5% VAT, gasoline price rise"},
    {"month": "2020-07", "name_ar": "رفع الضريبة إلى 15% (2020)", "name_en": "VAT raised to 15% (2020)",
     "includes_en": "VAT 5% to 15%"},
]


def event_table(cpi: pd.Series | None = None) -> pd.DataFrame:
    cpi = data.cpi_monthly() if cpi is None else cpi
    rows = []
    for e in EVENTS:
        t = pd.Period(e["month"], "M")
        before = cpi.loc[t - 12: t - 1]
        after = cpi.loc[t: t + 11]
        jump = cpi[t] - cpi[t - 1]
        reversal = cpi[t + 12] - cpi[t + 11]
        rows.append({
            **e,
            "yoy_month_before": cpi[t - 1],
            "yoy_reform_month": cpi[t],
            "jump_pp": round(jump, 2),
            "reversal_pp_12m_later": round(reversal, 2),
            "symmetry_ratio": round(-reversal / jump, 2),
            "avg_yoy_12m_before": round(before.mean(), 2),
            "avg_yoy_12m_after": round(after.mean(), 2),
            "excess_pp": round(after.mean() - before.mean(), 2),
        })
    return pd.DataFrame(rows)


def event_windows(cpi: pd.Series | None = None, k: int = 15) -> pd.DataFrame:
    """yoy inflation from -k to +k months around each event (for overlay charts)."""
    cpi = data.cpi_monthly() if cpi is None else cpi
    rows = []
    for e in EVENTS:
        t = pd.Period(e["month"], "M")
        for h in range(-k, k + 1):
            p = t + h
            if p in cpi.index:
                rows.append({"event": e["name_en"], "event_ar": e["name_ar"], "h": h,
                             "month": str(p), "cpi_yoy_pct": cpi[p]})
    return pd.DataFrame(rows)
