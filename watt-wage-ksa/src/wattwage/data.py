"""Load the raw, sourced data files."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW = PROJECT_ROOT / "data" / "raw"
CLEAN = PROJECT_ROOT / "data" / "clean"
OUTPUTS = PROJECT_ROOT / "outputs"


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(RAW / name, encoding="utf-8")


@lru_cache(maxsize=None)
def electricity_tariffs() -> pd.DataFrame:
    df = _read("electricity_residential_tariffs.csv")
    df["schedule"] = df["schedule"].astype(str)
    return df


@lru_cache(maxsize=None)
def electricity_fixed_fees() -> pd.DataFrame:
    df = _read("electricity_fixed_fees.csv")
    df["schedule"] = df["schedule"].astype(str)
    return df


@lru_cache(maxsize=None)
def sector_tariffs() -> pd.DataFrame:
    df = _read("electricity_sector_tariffs.csv")
    df["schedule"] = df["schedule"].astype(str)
    return df


@lru_cache(maxsize=None)
def water_tariffs() -> pd.DataFrame:
    df = _read("water_residential_tariffs.csv")
    df["schedule"] = df["schedule"].astype(str)
    return df


@lru_cache(maxsize=None)
def water_fixed_fees() -> pd.DataFrame:
    df = _read("water_fixed_fees.csv")
    df["schedule"] = df["schedule"].astype(str)
    return df


@lru_cache(maxsize=None)
def cpi_monthly() -> pd.Series:
    df = _read("cpi_yoy_monthly.csv")
    s = pd.Series(df["cpi_yoy_pct"].values,
                  index=pd.PeriodIndex(df["month"], freq="M"), name="cpi_yoy_pct")
    return s


@lru_cache(maxsize=None)
def cpi_annual() -> pd.DataFrame:
    return _read("cpi_annual.csv")


@lru_cache(maxsize=None)
def policy_events() -> pd.DataFrame:
    return _read("policy_events.csv")


@lru_cache(maxsize=None)
def nitaqat_thresholds() -> pd.DataFrame:
    return _read("nitaqat_thresholds.csv")


@lru_cache(maxsize=None)
def wage_facts() -> dict:
    df = _read("saudi_private_wages_q2_2026.csv")
    return dict(zip(df["metric"], df["value"].astype(float)))


@lru_cache(maxsize=None)
def assumptions() -> dict:
    with open(RAW / "assumptions.json", encoding="utf-8") as f:
        return json.load(f)


def a(key: str, field: str = "value"):
    """Shortcut: value (or low/high) of an assumption."""
    return assumptions()[key][field]


@lru_cache(maxsize=None)
def sector_fixed_fees() -> pd.DataFrame:
    df = _read("sector_fixed_fees.csv")
    df["schedule"] = df["schedule"].astype(str)
    return df


@lru_cache(maxsize=None)
def business_archetypes() -> pd.DataFrame:
    return _read("business_archetypes.csv")


@lru_cache(maxsize=None)
def savings_measures() -> pd.DataFrame:
    return _read("savings_measures.csv")


@lru_cache(maxsize=None)
def society_households() -> pd.DataFrame:
    return _read("society_households.csv")


@lru_cache(maxsize=None)
def activity_catalog() -> pd.DataFrame:
    return _read("activity_catalog.csv")


@lru_cache(maxsize=None)
def cpi_divisions() -> pd.DataFrame:
    df = pd.read_csv(RAW / "cpi_divisions_q1_2026.csv", encoding="utf-8-sig", dtype={"code": str})
    return df
