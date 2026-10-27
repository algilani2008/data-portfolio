"""Household-level impact: seasonal annual bills, behaviour response, net of support."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data
from .tariffs import (BREAKER_CLASSES, electricity_bill, electricity_bill_vec,
                      water_bill, water_bill_vec)

MONTHS_AR = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو",
             "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]

PROFILES = [
    {"id": "apartment", "name_ar": "شقة صغيرة", "name_en": "Small apartment",
     "kwh_month": 800, "breaker": "20-99A", "water_m3": 25},
    {"id": "typical", "name_ar": "منزل متوسط (متوسط المملكة)", "name_en": "Typical home (national average)",
     "kwh_month": 1550, "breaker": "100-199A", "water_m3": 43},
    {"id": "villa", "name_ar": "فيلا كبيرة", "name_en": "Large villa",
     "kwh_month": 3500, "breaker": "200-299A", "water_m3": 70},
    {"id": "mansion", "name_ar": "قصر / فيلا كبيرة جداً", "name_en": "Very large villa",
     "kwh_month": 7000, "breaker": "300A+", "water_m3": 120},
]


def seasonality() -> np.ndarray:
    s = np.array(data.a("monthly_seasonality"), dtype=float)
    return s / s.mean()


def _response(q_old: float, bill_old: float, bill_new: float, elasticity: float) -> float:
    """Constant-elasticity response of consumption to the change in the bill per unit."""
    if q_old <= 0 or bill_old <= 0 or elasticity == 0:
        return q_old
    return q_old * (bill_new / bill_old) ** elasticity


def annual_profile_bills(profile: dict, elasticity: float = 0.0) -> pd.DataFrame:
    """Month-by-month electricity + water bills under 2018 (current) and 2027 tariffs."""
    amps = BREAKER_CLASSES[profile["breaker"]]
    rows = []
    for m, f in enumerate(seasonality()):
        kwh = profile["kwh_month"] * f
        e_old = electricity_bill(kwh, amps, "2018")
        e_new0 = electricity_bill(kwh, amps, "2027")
        kwh_new = _response(kwh, e_old.energy + e_old.fixed, e_new0.energy + e_new0.fixed, elasticity)
        e_new = electricity_bill(kwh_new, amps, "2027")
        m3 = profile["water_m3"]
        w_old = water_bill(m3, 20, "2016", vat=0.15)
        w_new0 = water_bill(m3, 20, "2027")
        m3_new = _response(m3, w_old.energy + w_old.fixed, w_new0.energy + w_new0.fixed, elasticity)
        w_new = water_bill(m3_new, 20, "2027")
        rows.append({
            "month": m + 1, "month_ar": MONTHS_AR[m],
            "kwh_old": round(kwh), "kwh_new": round(kwh_new),
            "elec_old": round(e_old.total, 2), "elec_new": round(e_new.total, 2),
            "water_old": round(w_old.total, 2), "water_new": round(w_new.total, 2),
        })
    df = pd.DataFrame(rows)
    df["total_old"] = df["elec_old"] + df["water_old"]
    df["total_new"] = df["elec_new"] + df["water_new"]
    return df


def profile_summary(elasticity: float | None = None) -> pd.DataFrame:
    """Annual cost change per profile vs. the 500 SAR/month support (6,000 SAR/year)."""
    e = data.a("price_elasticity_short_run") if elasticity is None else elasticity
    support_year = 12 * data.a("support_monthly_sar")
    out = []
    for p in PROFILES:
        df0 = annual_profile_bills(p, 0.0)
        df1 = annual_profile_bills(p, e)
        row = {**p,
               "elec_old_year": round(df0["elec_old"].sum()),
               "elec_new_year": round(df0["elec_new"].sum()),
               "water_old_year": round(df0["water_old"].sum()),
               "water_new_year": round(df0["water_new"].sum()),
               "total_old_year": round(df0["total_old"].sum()),
               "total_new_year": round(df0["total_new"].sum()),
               "total_new_year_with_response": round(df1["total_new"].sum())}
        row["increase_year"] = row["total_new_year"] - row["total_old_year"]
        row["increase_pct"] = round(100 * row["increase_year"] / row["total_old_year"], 1)
        row["increase_year_with_response"] = row["total_new_year_with_response"] - row["total_old_year"]
        row["net_if_supported"] = support_year - row["increase_year"]
        row["support_covers_pct"] = round(100 * support_year / row["increase_year"], 0) if row["increase_year"] > 0 else None
        out.append(row)
    return pd.DataFrame(out)


def simulate_accounts(n: int = 20000, seed: int = 7, sigma: float | None = None,
                      mean_kwh: float | None = None) -> pd.DataFrame:
    """Synthetic population of residential accounts (consumption, breaker, water use)."""
    rng = np.random.default_rng(seed)
    sigma = data.a("consumption_lognormal_sigma") if sigma is None else sigma
    if mean_kwh is None:
        mean_kwh = data.a("residential_kwh_per_consumer_year_2024") / 12
    mu = np.log(mean_kwh) - sigma ** 2 / 2          # lognormal with the right mean
    kwh = rng.lognormal(mu, sigma, n)
    mix = data.a("breaker_mix")
    # bigger consumers get bigger breakers: assign breakers by consumption rank
    shares = np.cumsum([mix[k] for k in BREAKER_CLASSES])
    rank = kwh.argsort().argsort() / n
    breaker = np.array(list(BREAKER_CLASSES))[np.searchsorted(shares, rank, side="right").clip(0, 3)]
    m3_mean = data.a("water_litres_per_capita_day") * data.a("household_size") * 30 / 1000
    sw = 0.6
    m3 = rng.lognormal(np.log(m3_mean) - sw ** 2 / 2, sw, n)
    return pd.DataFrame({"kwh_month": kwh, "breaker": breaker, "m3_month": m3})


def national_bill_change(accounts: pd.DataFrame | None = None, elasticity: float = 0.0) -> dict:
    """Average annual electricity and water bill per account, current vs 2027 (SAR, incl. VAT)."""
    acc = simulate_accounts() if accounts is None else accounts
    old, new = _account_elec_year(acc, elasticity)
    m3 = acc["m3_month"].to_numpy()
    wo = water_bill_vec(m3, "2016", vat=0.15)
    wn = water_bill_vec(m3, "2027")
    if elasticity:
        wn = water_bill_vec(m3 * (wn / wo) ** elasticity, "2027")
    res = {"elec_old": old.mean(), "elec_new": new.mean(),
           "water_old": 12 * wo.mean(), "water_new": 12 * wn.mean()}
    res["elec_change_pct"] = 100 * (res["elec_new"] / res["elec_old"] - 1)
    res["water_change_pct"] = 100 * (res["water_new"] / res["water_old"] - 1)
    return res


def _account_elec_year(acc: pd.DataFrame, elasticity: float = 0.0):
    """Annual electricity bill per account under 2018 and 2027 tariffs."""
    old = np.zeros(len(acc))
    new = np.zeros(len(acc))
    for br, amps in BREAKER_CLASSES.items():
        mask = (acc["breaker"] == br).to_numpy()
        if not mask.any():
            continue
        for f in seasonality():
            q = acc.loc[mask, "kwh_month"].to_numpy() * f
            o = electricity_bill_vec(q, amps, "2018")
            n_ = electricity_bill_vec(q, amps, "2027")
            if elasticity:
                n_ = electricity_bill_vec(q * (n_ / o) ** elasticity, amps, "2027")
            old[mask] += o
            new[mask] += n_
    return old, new


def decile_table(accounts: pd.DataFrame | None = None) -> pd.DataFrame:
    """Bill change by consumption decile: shows how the fixed charge hits small users."""
    acc = simulate_accounts() if accounts is None else accounts.copy()
    acc["decile"] = pd.qcut(acc["kwh_month"], 10, labels=range(1, 11)).astype(int)
    old, new = _account_elec_year(acc)
    acc["old"], acc["new"] = old, new
    g = acc.groupby("decile")
    out = pd.DataFrame({"avg_kwh_month": g["kwh_month"].mean().round(),
                        "elec_old_year": g["old"].mean().round(),
                        "elec_new_year": g["new"].mean().round()}).reset_index()
    out["change_sar"] = out["elec_new_year"] - out["elec_old_year"]
    out["change_pct"] = (100 * (out["elec_new_year"] / out["elec_old_year"] - 1)).round(1)
    return out
