"""Household water: government network vs. water tankers (وايتات).

Network bills use the National Water Company tariffs (tariffs.water_bill). Tanker prices
are approximate market references; no 2027 tanker prices were announced, so the 2027
tanker cost uses an assumed percentage rise.
"""
from __future__ import annotations

from .tariffs import water_bill

# size (m3 = tonnes), typical price in SAR incl. VAT, supplier
TANKERS = [
    (6, 120, "private"), (12, 160, "private"), (18, 200, "private"),
    (19, 143, "National Water Company (114-135 SAR + VAT)"), (20, 220, "private"),
    (30, 259, "National Water Company (up to 225 SAR + VAT)"), (32, 300, "private"),
]


def monthly_m3(people: int, litres_per_day: float = 263) -> float:
    return people * litres_per_day * 30 / 1000


def tanker_cost(price: float, capacity_m3: float, per_month: float, rise_pct: float = 10.0) -> dict:
    old = price * per_month
    new = old * (1 + rise_pct / 100)
    return {"m3": capacity_m3 * per_month, "old_month": old, "new_month": new,
            "per_m3_old": price / capacity_m3, "per_m3_new": price * (1 + rise_pct / 100) / capacity_m3}


def network_cost(m3: float, sewage: bool = True) -> dict:
    old, new = water_bill(m3, 20, "2016", sewage, vat=0.15).total, water_bill(m3, 20, "2027", sewage).total
    return {"m3": m3, "old_month": old, "new_month": new,
            "per_m3_old": old / m3 if m3 else 0.0, "per_m3_new": new / m3 if m3 else 0.0}


def tankers_needed(m3: float, capacity_m3: float) -> float:
    """Tankers a month, rounded up to the nearest half."""
    import math
    return math.ceil(2 * m3 / capacity_m3) / 2
