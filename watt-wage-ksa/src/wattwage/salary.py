"""Salary calculator: take-home pay 2026-2028 vs. cost of living.

Kinds: gov (state employee), retiree, ss (social-security family), private_saudi, expat.
- 500 SAR allowance for gov, retiree and ss from January 2027 (start month assumed).
- Private-sector Saudis below the Nitaqat threshold are lifted to 5,000 SAR from
  late April 2027 and 6,000 SAR from late April 2028 if the employer complies.
- GOSI employee contribution (9.75%) is deducted for private-sector Saudis only.
"""
from __future__ import annotations

from . import data

PHASE1_MONTHS_2027 = 8   # late April to December
PHASE2_MONTHS_2028 = 8


def take_home(gross: float, kind: str, year: int, raise_pct: float = 0.0, comply: bool = True) -> float:
    """Average monthly take-home pay in `year`."""
    g = gross * (1 + raise_pct / 100) ** max(0, year - 2026)
    if kind == "private_saudi" and comply:
        if year == 2027 and gross < 5000:
            g = (g * (12 - PHASE1_MONTHS_2027) + max(g, 5000) * PHASE1_MONTHS_2027) / 12
        elif year == 2028 and gross < 6000:
            g = (max(g, 5000) * (12 - PHASE2_MONTHS_2028) + max(g, 6000) * PHASE2_MONTHS_2028) / 12
        elif year > 2028 and gross < 6000:
            g = max(g, 6000)
    net = g * (1 - data.a("gosi_employee_rate_saudi_pct") / 100) if kind == "private_saudi" else g
    if kind in ("gov", "retiree", "ss") and year >= 2027:
        net += data.a("support_monthly_sar")
    return round(net, 2)


def salary_path(gross: float, kind: str, prices: dict[int, float], raise_pct: float = 0.0,
                comply: bool = True) -> list[dict]:
    """prices: inflation % per year, e.g. {2027: 3.1, 2028: 1.9}."""
    out, level = [], 1.0
    base = take_home(gross, kind, 2026, raise_pct, comply)
    for y in (2026, 2027, 2028):
        if y > 2026:
            level *= 1 + prices[y] / 100
        n = take_home(gross, kind, y, raise_pct, comply)
        out.append({"year": y, "net_month": n, "price_level": round(level, 4),
                    "real_month_2026_sar": round(n / level, 2),
                    "real_change_pct": round(100 * (n / level / base - 1), 2)})
    return out
