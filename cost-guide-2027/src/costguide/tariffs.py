"""Electricity and water bill calculators for every residential tariff schedule.

All bills are monthly (30-day) and in SAR. Tiers are progressive: each rate
applies only to the volume inside its band.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from . import data

# VAT that applies to bills under each schedule (as of the schedule's own era;
# the 2018 schedule is billed at today's 15%, so "2018" means "current bill").
VAT = {"pre2016": 0.0, "2016": 0.0, "2018": 0.15, "2027": 0.15}

# Breaker classes used throughout the project (representative amps).
BREAKER_CLASSES = {"20-99A": 60, "100-199A": 150, "200-299A": 250, "300A+": 350}

# Meter fees before 2027: the 2018 schedule is the only published one, so it is
# also used for the 2016 and pre-2016 schedules.
_FEE_SCHEDULE = {"pre2016": "2018", "2016": "2018", "2018": "2018", "2027": "2027"}


@dataclass
class Bill:
    consumption: float
    energy: float
    fixed: float
    vat: float

    @property
    def total(self) -> float:
        return self.energy + self.fixed + self.vat

    def as_dict(self) -> dict:
        d = asdict(self)
        d["total"] = self.total
        return {k: round(v, 2) for k, v in d.items()}


def progressive_charge(volume: float, bands: pd.DataFrame, lo: str, hi: str, rate: str) -> float:
    """Charge for `volume` under progressive bands (rows sorted by `lo`)."""
    if volume <= 0:
        return 0.0
    total = 0.0
    for _, row in bands.sort_values(lo).iterrows():
        start = float(row[lo])
        end = float(row[hi]) if pd.notna(row[hi]) else np.inf
        if volume <= start:
            break
        total += (min(volume, end) - start) * float(row[rate])
    return total


def electricity_fixed_fee(breaker_a: float, schedule: str) -> float:
    fees = data.electricity_fixed_fees()
    fees = fees[fees["schedule"] == _FEE_SCHEDULE[schedule]]
    for _, row in fees.sort_values("breaker_from_a").iterrows():
        hi = row["breaker_to_a"] if pd.notna(row["breaker_to_a"]) else np.inf
        if row["breaker_from_a"] <= breaker_a < hi:
            return float(row["fee_sar"])
    return float(fees["fee_sar"].max())


def electricity_bill(kwh: float, breaker_a: float = 60, schedule: str = "2027",
                     vat: float | None = None) -> Bill:
    """Monthly residential electricity bill in SAR."""
    tiers = data.electricity_tariffs()
    tiers = tiers[tiers["schedule"] == schedule].copy()
    if tiers.empty:
        raise ValueError(f"unknown electricity schedule {schedule!r}")
    tiers["rate_sar"] = tiers["rate_halala"] / 100
    energy = progressive_charge(kwh, tiers, "tier_from_kwh", "tier_to_kwh", "rate_sar")
    fixed = electricity_fixed_fee(breaker_a, schedule)
    v = VAT[schedule] if vat is None else vat
    return Bill(kwh, energy, fixed, (energy + fixed) * v)


def water_fixed_fee(meter_mm: float, schedule: str, extra_units: int = 0,
                    sewage: bool = True) -> float:
    fees = data.water_fixed_fees()
    fees = fees[fees["schedule"] == schedule]
    if fees.empty:
        return 0.0
    for _, row in fees.sort_values("meter_from_mm").iterrows():
        hi = row["meter_to_mm"] if pd.notna(row["meter_to_mm"]) else np.inf
        if row["meter_from_mm"] <= meter_mm <= hi:
            fee = row["water_fee_sar"] + extra_units * row["extra_unit_water_sar"]
            if sewage:
                fee += row["sewage_fee_sar"] + extra_units * row["extra_unit_sewage_sar"]
            return float(fee)
    return 0.0


def water_bill(m3: float, meter_mm: float = 20, schedule: str = "2027",
               sewage: bool = True, extra_units: int = 0, vat: float | None = None) -> Bill:
    """Monthly residential water (+ sewage) bill in SAR."""
    tiers = data.water_tariffs()
    tiers = tiers[tiers["schedule"] == schedule]
    if tiers.empty:
        raise ValueError(f"unknown water schedule {schedule!r}")
    energy = progressive_charge(m3, tiers, "tier_from_m3", "tier_to_m3", "water_sar")
    if sewage:
        energy += progressive_charge(m3, tiers, "tier_from_m3", "tier_to_m3", "sewage_sar")
    fixed = water_fixed_fee(meter_mm, schedule, extra_units, sewage)
    v = VAT[schedule] if vat is None else vat
    return Bill(m3, energy, fixed, (energy + fixed) * v)


def _bands(df: pd.DataFrame, lo: str, hi: str, rate: str):
    d = df.sort_values(lo)
    los = d[lo].to_numpy(float)
    his = d[hi].fillna(np.inf).to_numpy(float)
    return los, his, d[rate].to_numpy(float)


def progressive_vec(q: np.ndarray, los, his, rates) -> np.ndarray:
    """Vectorised progressive charge for an array of volumes."""
    q = np.asarray(q, float)[..., None]
    return (np.clip(q - los, 0, his - los) * rates).sum(axis=-1)


def electricity_bill_vec(kwh: np.ndarray, breaker_a: float, schedule: str,
                         vat: float | None = None) -> np.ndarray:
    """Vectorised total monthly electricity bill (SAR) for many consumption values."""
    t = data.electricity_tariffs()
    t = t[t["schedule"] == schedule].assign(rate_sar=lambda d: d["rate_halala"] / 100)
    energy = progressive_vec(kwh, *_bands(t, "tier_from_kwh", "tier_to_kwh", "rate_sar"))
    fixed = electricity_fixed_fee(breaker_a, schedule)
    v = VAT[schedule] if vat is None else vat
    return (energy + fixed) * (1 + v)


def water_bill_vec(m3: np.ndarray, schedule: str, meter_mm: float = 20,
                   sewage: bool = True, vat: float | None = None) -> np.ndarray:
    t = data.water_tariffs()
    t = t[t["schedule"] == schedule]
    los, his, w = _bands(t, "tier_from_m3", "tier_to_m3", "water_sar")
    charge = progressive_vec(m3, los, his, w)
    if sewage:
        _, _, s = _bands(t, "tier_from_m3", "tier_to_m3", "sewage_sar")
        charge = charge + progressive_vec(m3, los, his, s)
    fixed = water_fixed_fee(meter_mm, schedule, 0, sewage)
    v = VAT[schedule] if vat is None else vat
    return (charge + fixed) * (1 + v)


def electricity_curve(schedules=("pre2016", "2016", "2018", "2027"), max_kwh=12000,
                      step=100, breaker_a=60, include_vat=False) -> pd.DataFrame:
    """Bill as a function of consumption for each schedule (for charts)."""
    rows = []
    for s in schedules:
        for k in range(0, max_kwh + 1, step):
            b = electricity_bill(k, breaker_a, s, vat=None if include_vat else 0.0)
            rows.append({"schedule": s, "kwh": k, "bill_sar": round(b.total, 2),
                         "avg_halala_per_kwh": round(100 * b.energy / k, 2) if k else None})
    return pd.DataFrame(rows)


def water_curve(schedules=("2016", "2027"), max_m3=120, step=1, include_vat=False) -> pd.DataFrame:
    rows = []
    for s in schedules:
        for m in range(0, max_m3 + 1, step):
            b = water_bill(m, 20, s, vat=None if include_vat else 0.0)
            rows.append({"schedule": s, "m3": m, "bill_sar": round(b.total, 2)})
    return pd.DataFrame(rows)


def sector_comparison() -> pd.DataFrame:
    """2018 vs 2027 energy rate (first tier and above 6,000 kWh) per sector."""
    df = data.sector_tariffs()
    out = []
    for (sector, sector_ar), g in df.groupby(["sector", "sector_ar"], sort=False):
        row = {"sector": sector, "sector_ar": sector_ar}
        for sched in ("2018", "2027"):
            gs = g[g["schedule"] == sched].sort_values("tier_from_kwh")
            row[f"tier1_{sched}"] = gs["rate_halala"].iloc[0]
            row[f"tier2_{sched}"] = gs["rate_halala"].iloc[-1]
        row["tier1_change_pct"] = round(100 * (row["tier1_2027"] / row["tier1_2018"] - 1), 1)
        row["tier2_change_pct"] = round(100 * (row["tier2_2027"] / row["tier2_2018"] - 1), 1)
        out.append(row)
    return pd.DataFrame(out)


# --- non-residential sectors ------------------------------------------------
def _fee_group(sector: str) -> str:
    return "agri_charity" if sector in ("agricultural", "charities") else "nonresidential"


def sector_fixed_fee(breaker_a: float, sector: str, schedule: str) -> float:
    if sector == "residential":
        return electricity_fixed_fee(breaker_a, schedule)
    f = data.sector_fixed_fees()
    f = f[(f["fee_group"] == _fee_group(sector)) & (f["schedule"] == schedule)]
    for _, row in f.sort_values("breaker_from_a").iterrows():
        hi = row["breaker_to_a"] if pd.notna(row["breaker_to_a"]) else np.inf
        if row["breaker_from_a"] <= breaker_a < hi:
            return float(row["fee_sar"])
    return float(f["fee_sar"].max())


def sector_bill(kwh: float, breaker_a: float, sector: str, schedule: str, vat: float = 0.0) -> Bill:
    """Monthly bill for any sector under the 2018 or 2027 schedule (businesses: VAT excluded by default)."""
    t = data.sector_tariffs()
    t = t[(t["sector"] == sector) & (t["schedule"] == schedule)].assign(rate_sar=lambda d: d["rate_halala"] / 100)
    if t.empty:
        raise ValueError(f"no tariff for {sector}/{schedule}")
    energy = progressive_charge(kwh, t, "tier_from_kwh", "tier_to_kwh", "rate_sar")
    fixed = sector_fixed_fee(breaker_a, sector, schedule)
    return Bill(kwh, energy, fixed, (energy + fixed) * vat)
