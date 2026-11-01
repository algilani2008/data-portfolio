"""Reusable helpers for analysing the GCC electricity mix with Our World in Data energy data.

All numbers come from the public OWID energy dataset (CC BY 4.0):
https://github.com/owid/energy-data
"""
from __future__ import annotations

import hashlib
import io
import urllib.request
from pathlib import Path

import pandas as pd

OWID_URL = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"

GCC = {
    "SAU": "Saudi Arabia",
    "ARE": "United Arab Emirates",
    "QAT": "Qatar",
    "KWT": "Kuwait",
    "OMN": "Oman",
    "BHR": "Bahrain",
}
GCC_AR = {
    "SAU": "السعودية",
    "ARE": "الإمارات",
    "QAT": "قطر",
    "KWT": "الكويت",
    "OMN": "عُمان",
    "BHR": "البحرين",
}
WORLD = "World"

# Electricity sources (TWh columns) used for the mix breakdown.
SOURCES = {
    "gas": "gas_electricity",
    "oil": "oil_electricity",
    "coal": "coal_electricity",
    "solar": "solar_electricity",
    "wind": "wind_electricity",
    "nuclear": "nuclear_electricity",
    "hydro": "hydro_electricity",
    "other_renewable": "other_renewable_electricity",
}

COLUMNS = [
    "country", "iso_code", "year", "population",
    "electricity_generation", "per_capita_electricity", "carbon_intensity_elec",
    "low_carbon_electricity", "low_carbon_share_elec", "fossil_electricity",
    "oil_share_elec", "gas_share_elec", "solar_share_elec", "nuclear_share_elec",
    *SOURCES.values(),
]


def download(cache: Path | None = None, url: str = OWID_URL) -> tuple[pd.DataFrame, str]:
    """Download the OWID CSV (or read a cached copy). Returns (frame, sha256 of the bytes)."""
    if cache is not None and cache.exists():
        raw = cache.read_bytes()
    else:
        with urllib.request.urlopen(url, timeout=120) as resp:  # noqa: S310 - fixed https URL
            raw = resp.read()
        if cache is not None:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    return pd.read_csv(io.BytesIO(raw)), digest


def select(df: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    """Keep the six GCC countries plus the World aggregate, the needed columns and years."""
    keep = df["iso_code"].isin(GCC) | (df["country"] == WORLD)
    cols = [c for c in COLUMNS if c in df.columns]
    out = df.loc[keep & df["year"].between(start, end), cols].copy()
    out["code"] = out["iso_code"].where(out["country"] != WORLD, "WLD")
    return out.sort_values(["code", "year"]).reset_index(drop=True)


def latest_common_year(df: pd.DataFrame, codes=tuple(GCC), column: str = "electricity_generation") -> int:
    """Latest year in which every country in `codes` has a value for `column`.

    Using a common year avoids comparing one country's 2025 estimate with another's 2024 value.
    """
    years = None
    for code in codes:
        ys = set(df.loc[(df["code"] == code) & df[column].notna(), "year"])
        years = ys if years is None else years & ys
    if not years:
        raise ValueError(f"no common year with data for {column}")
    return max(years)


def mix_shares(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Share (%) of each source in total generation for one year, one row per country code."""
    sub = df[df["year"] == year].set_index("code")
    twh = sub.reindex(columns=list(SOURCES.values())).fillna(0.0)  # missing source = 0 TWh
    twh.columns = list(SOURCES)
    total = sub["electricity_generation"]
    shares = twh.div(total, axis=0) * 100
    # Anything not covered by the listed sources (rounding, unlisted fuels) goes to "other".
    shares["other"] = (100 - shares.sum(axis=1)).clip(lower=0)
    return shares.round(2)


def cagr(first: float, last: float, years: int) -> float:
    """Compound annual growth rate in percent."""
    if years <= 0 or first <= 0:
        raise ValueError("years and first value must be positive")
    return ((last / first) ** (1 / years) - 1) * 100


def growth_met_by_low_carbon(df: pd.DataFrame, code: str, start: int, end: int) -> dict:
    """How much of the extra electricity produced between two years came from low-carbon sources.

    Returns added TWh in total, added low-carbon TWh and the share (%) of growth they covered.
    """
    s = df[df["code"] == code].set_index("year")
    added = s.at[end, "electricity_generation"] - s.at[start, "electricity_generation"]
    added_lc = s.at[end, "low_carbon_electricity"] - s.at[start, "low_carbon_electricity"]
    share = (added_lc / added * 100) if added > 0 else float("nan")
    return {"added_twh": round(added, 2), "added_low_carbon_twh": round(added_lc, 2),
            "low_carbon_share_of_growth_pct": round(share, 1)}


def summary_table(df: pd.DataFrame, start: int, end: int, growth_from: int) -> pd.DataFrame:
    """One row per country (and World) with the headline indicators."""
    rows = []
    for code in [*GCC, "WLD"]:
        s = df[df["code"] == code].set_index("year")
        if start not in s.index or end not in s.index:
            continue
        g0, g1 = s.at[start, "electricity_generation"], s.at[end, "electricity_generation"]
        row = {
            "code": code,
            "country": s["country"].iloc[0],
            f"generation_twh_{start}": round(g0, 2),
            f"generation_twh_{end}": round(g1, 2),
            f"generation_cagr_pct_{start}_{end}": round(cagr(g0, g1, end - start), 2),
            f"per_capita_kwh_{end}": round(s.at[end, "per_capita_electricity"], 0),
            f"carbon_intensity_g_per_kwh_{end}": s.at[end, "carbon_intensity_elec"],
            f"low_carbon_share_pct_{growth_from}": round(s.at[growth_from, "low_carbon_share_elec"], 2),
            f"low_carbon_share_pct_{end}": round(s.at[end, "low_carbon_share_elec"], 2),
            f"oil_share_pct_{growth_from}": round(s.at[growth_from, "oil_share_elec"], 2),
            f"oil_share_pct_{end}": round(s.at[end, "oil_share_elec"], 2),
        }
        row.update({f"{k}_{growth_from}_{end}": v
                    for k, v in growth_met_by_low_carbon(df, code, growth_from, end).items()})
        rows.append(row)
    return pd.DataFrame(rows)
