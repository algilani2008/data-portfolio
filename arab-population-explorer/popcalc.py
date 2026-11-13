"""Small, dependency-free population growth helpers.

These are the formulas the site uses. The same logic is mirrored in site/calc.js, and the
tests run both versions on the same inputs so the page and the Python report never disagree.
"""
from __future__ import annotations

import math


def growth_multiple(p_start: float, p_end: float) -> float:
    """How many times bigger p_end is than p_start (2.0 means it doubled)."""
    if p_start <= 0:
        raise ValueError("starting population must be positive")
    return p_end / p_start


def cagr(p_start: float, p_end: float, years: float) -> float:
    """Average yearly growth rate (compound), as a fraction: 0.02 means 2% a year."""
    if years <= 0:
        raise ValueError("years must be positive")
    return growth_multiple(p_start, p_end) ** (1.0 / years) - 1.0


def doubling_time(rate: float) -> float:
    """Years needed to double at a constant yearly rate (a fraction). inf if rate <= 0."""
    if rate <= 0:
        return math.inf
    return math.log(2.0) / math.log1p(rate)


def rule_of_70(rate: float) -> float:
    """The quick mental shortcut for doubling_time: 70 divided by the rate in percent."""
    if rate <= 0:
        return math.inf
    return 70.0 / (rate * 100.0)


def added_per_day(p_start: float, p_end: float, years: float) -> float:
    """Average net change in people per day between two dates (births - deaths + migration)."""
    if years <= 0:
        raise ValueError("years must be positive")
    return (p_end - p_start) / (years * 365.25)


def project(p_now: float, rate: float, years: float) -> float:
    """What constant growth would give after `years`. An illustration, not a forecast."""
    return p_now * (1.0 + rate) ** years
