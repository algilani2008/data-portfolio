"""Small, testable helpers for measuring how closely GDP tracks the oil price.

All functions are pure (no network, no files) so they can be unit-tested.
The data loading / downloading lives in ``run_analysis.py``.

Key idea
--------
If an economy depends heavily on oil, its GDP (in US dollars) rises and falls
with the oil price. We measure that link with the *elasticity*: the slope of a
regression of yearly GDP growth on yearly oil-price growth, both in log terms.

    dlog(GDP_t) = a + b * dlog(Brent_t) + e_t

An elasticity ``b = 0.3`` means: in a year when Brent rose 10%, GDP in dollars
grew on average about 3% more than in a year when Brent was flat.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

GCC = {
    "SAU": "Saudi Arabia",
    "ARE": "United Arab Emirates",
    "QAT": "Qatar",
    "KWT": "Kuwait",
    "OMN": "Oman",
    "BHR": "Bahrain",
}
BENCHMARKS = {
    "NOR": "Norway",
    "EGY": "Egypt",
    "JOR": "Jordan",
    "WLD": "World",
}


def annual_mean_price(prices: pd.DataFrame, min_obs: int = 12) -> pd.Series:
    """Average a monthly price table (columns Date, Price) into calendar years.

    Years with fewer than ``min_obs`` observations (partial years such as the
    first year of the series or the current, unfinished year) are dropped.
    """
    df = prices.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    df = df.dropna(subset=["Price"])
    g = df.groupby(df["Date"].dt.year)["Price"]
    out = g.mean()[g.count() >= min_obs]
    out.index.name = "year"
    out.name = "brent_usd"
    return out


def wide_by_country(long: pd.DataFrame, codes: list[str]) -> pd.DataFrame:
    """World Bank long table (Country Code, Year, Value) -> year x country."""
    sub = long[long["Country Code"].isin(codes)]
    wide = sub.pivot_table(index="Year", columns="Country Code", values="Value")
    wide.index = wide.index.astype(int)
    wide.index.name = "year"
    return wide.reindex(columns=[c for c in codes if c in wide.columns])


def log_growth(s: pd.Series | pd.DataFrame):
    """Year-on-year growth in log points: log(x_t) - log(x_{t-1}).

    Uses the previous *calendar* year only, so a gap in the data never creates
    a fake multi-year jump.
    """
    x = np.log(s.where(s > 0))
    prev = x.shift(1)
    if isinstance(x, pd.DataFrame):
        consecutive = pd.Series(x.index, index=x.index).diff().eq(1)
        return (x - prev).where(consecutive, axis=0)
    consecutive = pd.Series(x.index, index=x.index).diff().eq(1)
    return (x - prev).where(consecutive)


@dataclass
class Elasticity:
    slope: float
    intercept: float
    r2: float
    corr: float
    n: int
    ci_low: float
    ci_high: float


def ols_slope(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Slope and intercept of y = a + b x by least squares."""
    xm, ym = x.mean(), y.mean()
    sxx = ((x - xm) ** 2).sum()
    if sxx == 0:
        raise ValueError("x has no variation")
    b = ((x - xm) * (y - ym)).sum() / sxx
    return float(b), float(ym - b * xm)


def elasticity(
    gdp_growth: pd.Series,
    oil_growth: pd.Series,
    n_boot: int = 2000,
    seed: int = 0,
    min_obs: int = 8,
) -> Elasticity | None:
    """Regress GDP growth on oil growth over the years both are available.

    The 95% interval is a simple bootstrap over years (resampling year pairs).
    Returns ``None`` if fewer than ``min_obs`` overlapping years exist.
    """
    df = pd.concat({"y": gdp_growth, "x": oil_growth}, axis=1).dropna()
    if len(df) < min_obs:
        return None
    x, y = df["x"].to_numpy(), df["y"].to_numpy()
    b, a = ols_slope(x, y)
    resid = y - (a + b * x)
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = 1 - (resid**2).sum() / ss_tot if ss_tot > 0 else float("nan")
    corr = float(np.corrcoef(x, y)[0, 1])
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(x), len(x))
        if np.ptp(x[idx]) == 0:
            continue
        boots.append(ols_slope(x[idx], y[idx])[0])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return Elasticity(b, a, float(r2), corr, len(df), float(lo), float(hi))


def rolling_corr(a: pd.Series, b: pd.Series, window: int = 10) -> pd.Series:
    """Rolling correlation over ``window`` years, labelled by the window's last year."""
    df = pd.concat({"a": a, "b": b}, axis=1)
    return df["a"].rolling(window, min_periods=window).corr(df["b"])


def per_capita(gdp: pd.DataFrame, pop: pd.DataFrame) -> pd.DataFrame:
    """GDP per person, aligned on year and country."""
    g, p = gdp.align(pop, join="inner")
    return g / p


def cagr(s: pd.Series, start: int, end: int) -> float:
    """Compound annual growth rate between two years (NaN if a value is missing)."""
    if start not in s.index or end not in s.index:
        return float("nan")
    a, b = s.loc[start], s.loc[end]
    if not (a > 0 and b > 0):
        return float("nan")
    return float((b / a) ** (1 / (end - start)) - 1)
