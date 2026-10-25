"""Saudization (Nitaqat Mutawar) calculator.

Required Saudization for a band: r = m * ln(N) + c, with m and c per activity, band and year
(HRSD procedural guide 2026, Annex 1), N = total headcount. Establishments with 5 or fewer
workers need one counted Saudi.

Counting weights (HRSD rules, as published on Nitaqat calculators in 2026):
  full-time Saudi at or above the full-count wage -> 1; 3,000 SAR up to the full-count wage -> 0.5;
  below 3,000 -> 0; part-time (>= 3,000) -> 0.5; student -> 0.5; flexible work (168 h) -> 1/3;
  person with a disability at or above the full-count wage -> 4 (weights above one also add to
  the denominator).
The full-count wage is 4,000 SAR today and rises to 5,000 then 6,000 SAR under the October 2026
decision. The partial (0.5) band below the new thresholds is an assumption: the decision states
only the full-count wage.
"""
from __future__ import annotations

import math
from functools import lru_cache

import pandas as pd

from . import data

BANDS = ("lg", "mg", "hg", "pl")
BAND_NAMES = {"red": ("أحمر", "Red"), "lg": ("أخضر منخفض", "Low green"), "mg": ("أخضر متوسط", "Medium green"),
              "hg": ("أخضر مرتفع", "High green"), "pl": ("بلاتيني", "Platinum")}


@lru_cache(maxsize=None)
def activities() -> pd.DataFrame:
    return pd.read_csv(data.RAW / "nitaqat_activities.csv", encoding="utf-8").set_index("id")


def full_count_wage(year: int, after_phase: bool = True) -> int:
    """Full-count wage in force for most of `year` (phases from late April)."""
    if year <= 2026:
        return 4000
    return 5000 if year == 2027 else 6000


def required(activity_id: int, headcount: int, year: int) -> dict:
    """Required Saudization % per band (monotone across bands, clamped 0-100)."""
    a = activities().loc[activity_id]
    yy = str(min(max(year, 2026), 2028))[2:]
    n = max(1, headcount)
    out, prev = {}, 0.0
    for b in BANDS:
        r = a[f"m_{b}"] * math.log(n) + a[f"c{yy}_{b}"]
        r = min(100.0, max(0.0, r, prev))
        out[b] = round(r, 2)
        prev = r
    return out


def weighted_count(staff: dict, year: int) -> tuple[float, float]:
    """(weighted Saudi count, weighted denominator) from staff counts.

    staff keys: saudi_full (list of wages), part_time, students, flexible, disabled (list of wages), non_saudi
    """
    t = full_count_wage(year)
    num = 0.0
    extra_den = 0.0
    for w in staff.get("saudi_full", []):
        num += 1.0 if w >= t else (0.5 if w >= 3000 else 0.0)
    num += 0.5 * staff.get("part_time", 0) + 0.5 * staff.get("students", 0) + staff.get("flexible", 0) / 3
    for w in staff.get("disabled", []):
        wt = 4.0 if w >= t else (0.5 if w >= 3000 else 0.0)
        num += wt
        extra_den += max(0.0, wt - 1)
    heads = (len(staff.get("saudi_full", [])) + staff.get("part_time", 0) + staff.get("students", 0) +
             staff.get("flexible", 0) + len(staff.get("disabled", [])) + staff.get("non_saudi", 0))
    return num, heads + extra_den


def hires_needed(target_pct: float, saudis: float, total: float) -> int:
    """New full-count Saudis needed: (S + n) / (T + n) >= target."""
    t = target_pct / 100
    if t >= 1:
        return 10 ** 6
    n = (t * total - saudis) / (1 - t)
    return max(0, math.ceil(n - 1e-9))


def assess(activity_id: int, staff: dict, year: int) -> dict:
    num, den = weighted_count(staff, year)
    heads = int(round(den))
    rate = 100 * num / den if den else 0.0
    if heads <= 5:
        band = "pl" if num >= 1 else "red"
        req = {b: None for b in BANDS}
        hires = {b: (0 if num >= 1 else 1) for b in BANDS}
    else:
        req = required(activity_id, heads, year)
        band = "red"
        for b in BANDS:
            if rate >= req[b]:
                band = b
        hires = {b: hires_needed(req[b], num, den) for b in BANDS}
    gosi = 1 + data.a("gosi_employer_rate_saudi_pct") / 100
    t = full_count_wage(year)
    return {"year": year, "full_count_wage": t, "weighted_saudis": round(num, 2), "denominator": round(den, 2),
            "saudization_pct": round(rate, 2), "band": band, "required_pct": req, "hires_needed": hires,
            "hire_cost_year": {b: round(h * t * 12 * gosi) for b, h in hires.items()}}
