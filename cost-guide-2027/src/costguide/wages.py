"""Nitaqat wage threshold: who sits below 5,000 / 6,000 SAR and what it costs to lift them.

The NLO publishes Saudi private-sector wages only in four bands plus the median,
so the distribution below 8,000 SAR is reconstructed as a piecewise-linear CDF
through the published points. Because the current threshold (4,000 SAR) makes
employers bunch wages just at 4,000, a 'bunching' variant puts part of the
4,000-5,050 band right at the threshold.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data


def cdf_points() -> pd.DataFrame:
    f = data.wage_facts()
    return pd.DataFrame({
        "wage": [2000, 4000, f["median_wage"], 8000, 15000, 60000],
        "cdf": [0.0, f["share_below_4000"] / 100, 0.5,
                (f["share_below_4000"] + f["share_4000_8000"]) / 100,
                1 - f["share_above_15000"] / 100, 1.0],
    })


def sample_wages(n: int = 200_000, bunching: float = 0.0, seed: int = 3) -> np.ndarray:
    """Synthetic wages matching the published bands.

    bunching: share of the 4,000-median band placed at 4,000-4,100 SAR.
    """
    rng = np.random.default_rng(seed)
    pts = cdf_points()
    u = rng.uniform(0, 1, n)
    w = np.interp(u, pts["cdf"], pts["wage"])
    if bunching > 0:
        lo, hi = pts["cdf"].iloc[1], pts["cdf"].iloc[2]
        band = (u >= lo) & (u < hi)
        move = band & (rng.uniform(0, 1, n) < bunching)
        w[move] = rng.uniform(4000, 4100, move.sum())
        # the rest of the band spreads over 4,100-median so the median stays put
        rest = band & ~move
        w[rest] = rng.uniform(4100, pts["wage"].iloc[2], rest.sum())
    return w


def threshold_impact(threshold: float, bunching: float = 0.0, compliance: float = 1.0,
                     n: int = 200_000) -> dict:
    """Workers below `threshold` and the employer cost to raise them to it."""
    f = data.wage_facts()
    workers = f["saudi_private_workers"]
    w = sample_wages(n, bunching)
    below = w < threshold
    share = below.mean()
    gap = np.where(below, threshold - w, 0.0)
    avg_gap = gap[below].mean() if below.any() else 0.0
    gosi = data.a("gosi_employer_rate_saudi_pct") / 100
    affected = share * workers * compliance
    wage_bill_month = affected * avg_gap
    return {
        "threshold": threshold, "bunching": bunching, "compliance": compliance,
        "share_below_pct": round(100 * share, 1),
        "workers_below": int(round(share * workers)),
        "workers_raised": int(round(affected)),
        "avg_raise_sar": round(avg_gap),
        "worker_gain_bn_sar_year": round(wage_bill_month * 12 / 1e9, 2),
        "employer_cost_bn_sar_year": round(wage_bill_month * (1 + gosi) * 12 / 1e9, 2),
    }


def threshold_table() -> pd.DataFrame:
    rows = []
    for t in (5000, 6000):
        for b in (0.0, 0.4):
            for c in (1.0, 0.7):
                rows.append(threshold_impact(t, b, c))
    return pd.DataFrame(rows)


def threshold_curve(bunching: float = 0.0) -> pd.DataFrame:
    """Share below and employer cost for thresholds 4,000-8,000 (dashboard slider)."""
    return pd.DataFrame([threshold_impact(t, bunching, 1.0, n=100_000)
                         for t in range(4000, 8001, 250)])


def history_check() -> dict:
    """The 2020 precedent: Saudis below 4,000 SAR then vs now."""
    f = data.wage_facts()
    now = f["share_below_4000"] / 100 * f["saudi_private_workers"]
    return {"below_4000_2020": int(f["saudis_benefiting_4000_threshold_2020"]),
            "below_4000_q2_2026": int(round(now)),
            "reduction_pct": round(100 * (1 - now / f["saudis_benefiting_4000_threshold_2020"]), 1),
            "median_wage_q2_2026": int(f["median_wage"])}


def wage_histogram(bunching: float = 0.4, bins=np.arange(3000, 12001, 250)) -> pd.DataFrame:
    w = sample_wages(200_000, bunching)
    counts, edges = np.histogram(w, bins=bins)
    total = data.wage_facts()["saudi_private_workers"]
    return pd.DataFrame({"from": edges[:-1].astype(int), "to": edges[1:].astype(int),
                         "workers": (counts / len(w) * total).round().astype(int)})
