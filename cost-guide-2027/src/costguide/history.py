"""Past, present and future: prices, wages and bills for any year from 1964 to 2050.

Every value carries a `kind` so the site can say how sure it is:
  actual        published figure
  derived       worked out from published figures (e.g. the civil-service scale)
  interpolated  between two published figures
  estimate      before the first published figure (real value held constant)
  partial       average of the months published so far (2026)
  forecast      this project's model (2027-2030)
  assumed       long-run assumption (after 2030, or prices held at today's level)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data, tariffs

FIRST, LAST, BASE = 1964, 2050, 2026
YEARS = list(range(FIRST, LAST + 1))
LONG_RUN_INFLATION = 2.0


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(data.RAW / name, encoding="utf-8")


_CENTRAL: tuple[float, float] | None = None


def _central() -> tuple[float, float]:
    """Central-scenario average inflation for 2027 and 2028 from the forecast model (cached)."""
    global _CENTRAL
    if _CENTRAL is None:
        from . import forecast
        scen = forecast.scenarios(forecast.baseline())
        _CENTRAL = (forecast.annual_average(scen, "central", 2027), forecast.annual_average(scen, "central", 2028))
    return _CENTRAL


def inflation_path(central_2027: float | None = None, central_2028: float | None = None,
                   baseline_after: float = 1.93) -> pd.DataFrame:
    """Annual inflation % and its kind for every year."""
    cpi = data.cpi_annual().set_index("year")["cpi_annual_pct"]
    monthly = data.cpi_monthly()
    m26 = monthly[monthly.index.year == 2026]
    if central_2027 is None or central_2028 is None:
        central_2027, central_2028 = _central()
    rows = []
    for y in YEARS:
        if y in cpi.index:
            rows.append((y, float(cpi[y]), "actual"))
        elif y == 2026:
            rows.append((y, round(float(m26.mean()), 2), "actual" if len(m26) == 12 else "partial"))
        elif y == 2027:
            rows.append((y, float(central_2027), "forecast"))
        elif y == 2028:
            rows.append((y, float(central_2028), "forecast"))
        elif y <= 2030:
            rows.append((y, baseline_after, "forecast"))
        else:
            rows.append((y, LONG_RUN_INFLATION, "assumed"))
    return pd.DataFrame(rows, columns=["year", "inflation_pct", "kind"])


def price_index(path: pd.DataFrame | None = None) -> pd.DataFrame:
    """Price level with 2026 = 100. Index(y) = Index(y-1) * (1 + inflation(y))."""
    path = inflation_path() if path is None else path
    p = path.set_index("year")
    lvl = {FIRST: 1.0}
    for y in YEARS[1:]:
        lvl[y] = lvl[y - 1] * (1 + p.loc[y, "inflation_pct"] / 100)
    scale = 100 / lvl[BASE]
    out = path.copy()
    out["index"] = [lvl[y] * scale for y in out.year]
    return out


def convert(amount: float, from_year: int, to_year: int, idx: pd.DataFrame | None = None) -> float:
    """What `amount` in `from_year` riyals is worth in `to_year` riyals."""
    idx = price_index() if idx is None else idx
    s = idx.set_index("year")["index"]
    return amount * s[to_year] / s[from_year]


def _series(points: pd.DataFrame, idx: pd.Series, start_back: int | None, growth: float | None,
            hold_flat: bool = False) -> tuple[list, list]:
    """Fill a yearly series from sparse points.

    Between points: geometric interpolation. Before the first point back to
    `start_back`: real value held constant (nominal follows prices). After the
    last point: grows at `growth` % a year, or stays flat if `hold_flat`.
    """
    pts = points.set_index("year")
    obs = {int(y): (float(r.value_sar), r.kind) for y, r in pts.iterrows()}
    ys = sorted(obs)
    vals, kinds = [], []
    for y in YEARS:
        if y in obs:
            v, k = obs[y]
        elif y < ys[0]:
            if start_back is None or y < start_back:
                v, k = None, None
            elif hold_flat:
                v, k = obs[ys[0]][0], "derived"
            else:
                v, k = obs[ys[0]][0] * idx[y] / idx[ys[0]], "estimate"
        elif y > ys[-1]:
            last = obs[ys[-1]][0]
            if hold_flat:
                v, k = last, "assumed"
            else:
                v, k = last * (1 + growth / 100) ** (y - ys[-1]), "assumed"
        else:
            a = max(t for t in ys if t < y)
            b = min(t for t in ys if t > y)
            va, vb = obs[a][0], obs[b][0]
            if obs[a][1] == "derived" and va == vb:
                v, k = va, "derived"
            else:
                v, k = va * (vb / va) ** ((y - a) / (b - a)), "interpolated"
        vals.append(None if v is None else round(v))
        kinds.append(k)
    return vals, kinds


def wage_table(idx: pd.DataFrame | None = None) -> dict:
    idx = price_index() if idx is None else idx
    s = idx.set_index("year")["index"]
    w = _read("wages_history.csv")
    a = data.assumptions()
    g_sau = a["saudi_wage_growth_pct"]["value"]
    g_exp = a["expat_wage_growth_pct"]["value"]
    spec = {
        # series: (first year shown, growth after the last point, hold flat)
        "gov_grade6_start": (1980, None, True),
        "private_saudi_avg": (2000, g_sau, False),
        "private_nonsaudi_avg": (2000, g_exp, False),
        "saudi_all_sectors_avg": (None, g_sau, False),
    }
    out = {}
    for name, (back, g, flat) in spec.items():
        v, k = _series(w[w.series == name], s, back, g, flat)
        out[name] = {"v": v, "k": k}
    return out


def nitaqat_wage(year: int) -> int | None:
    if year < 2011:
        return None
    if year < 2021:
        return 3000
    if year < 2027:
        return 4000
    if year < 2028:
        return 5000
    return 6000


def vat_pct(year: int) -> float:
    if year < 2018:
        return 0.0
    if year < 2020:
        return 5.0
    if year == 2020:
        return 10.0  # 5% until June, 15% from July
    return 15.0


def fuel(year: int) -> tuple[float | None, float | None, str | None]:
    f = _read("fuel_prices_history.csv")
    for r in f.itertuples():
        if r.from_year <= year <= r.to_year:
            return float(r.gasoline91_sar_l), float(r.gasoline95_sar_l), r.confidence
    if year > f.to_year.max():
        last = f.iloc[-1]
        return float(last.gasoline91_sar_l), float(last.gasoline95_sar_l), "assumed"
    return None, None, None


def elec_schedule(year: int) -> str:
    if year < 1995:
        return "flat"
    if year < 2001:
        return "1995"
    if year < 2016:
        return "pre2016"
    if year < 2018:
        return "2016"
    if year < 2027:
        return "2018"
    return "2027"


def water_schedule(year: int) -> str | None:
    if year < 1994:
        return None
    if year < 2016:
        return "pre2016"
    if year < 2027:
        return "2016"
    return "2027"


def historical_electricity_tariffs() -> pd.DataFrame:
    return _read("electricity_historical_tariffs.csv")


def elec_bill(kwh: float, amps: float, year: int) -> float:
    """Monthly residential bill in that year's riyals, with that year's VAT.

    Meter fees before 2027 use the 2018 table (the only published one), as in tariffs.py.
    """
    sched = elec_schedule(year)
    v = vat_pct(year) / 100
    if sched in ("flat", "1995"):
        rows = historical_electricity_tariffs()
        rows = rows[rows.schedule == sched].assign(rate_sar=lambda d: d.rate_halala / 100)
        energy = tariffs.progressive_charge(kwh, rows, "tier_from_kwh", "tier_to_kwh", "rate_sar")
        fee = tariffs.electricity_fixed_fee(amps, "2018")
        return (energy + fee) * (1 + v)
    return tariffs.electricity_bill(kwh, amps, sched, vat=v).total


def water_bill(m3: float, year: int, sewage: bool = True) -> float | None:
    sched = water_schedule(year)
    if sched is None:
        return None
    return tariffs.water_bill(m3, 20, sched, sewage=sewage, vat=vat_pct(year) / 100).total


def snapshot_table(years: list[int] | None = None, kwh: float = 2000, amps: float = 70,
                   m3: float = 30, tank_l: float = 60) -> pd.DataFrame:
    """One row per year: what 1,000 SAR of 2026 was then, bills, fuel and wages."""
    years = years or [1975, 1985, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2026, 2027, 2028, 2030, 2035, 2040, 2050]
    idx = price_index()
    s = idx.set_index("year")
    wages = wage_table(idx)
    rows = []
    for y in years:
        i = YEARS.index(y)
        g91, g95, _ = fuel(y)
        rows.append({
            "year": y, "kind": s.loc[y, "kind"],
            "inflation_pct": round(float(s.loc[y, "inflation_pct"]), 2),
            "price_index_2026_100": round(float(s.loc[y, "index"]), 2),
            "sar_1000_of_2026": round(1000 * float(s.loc[y, "index"]) / 100),
            "electricity_bill": round(elec_bill(kwh, amps, y), 2),
            "water_bill": None if water_bill(m3, y) is None else round(water_bill(m3, y), 2),
            "gasoline91_tank": None if g91 is None else round(g91 * tank_l, 2),
            "vat_pct": vat_pct(y), "nitaqat_full_count_wage": nitaqat_wage(y),
            **{k: v["v"][i] for k, v in wages.items()},
        })
    return pd.DataFrame(rows)


def dashboard_payload() -> dict:
    idx = price_index()
    f = [fuel(y) for y in YEARS]
    ev = _read("history_events.csv")
    return {
        "years": YEARS, "base": BASE,
        "infl": [round(float(v), 2) for v in idx.inflation_pct],
        "index": [round(float(v), 4) for v in idx["index"]],
        "kind": list(idx.kind),
        "wages": wage_table(idx),
        "fuel91": [x[0] for x in f], "fuel95": [x[1] for x in f], "fuel_conf": [x[2] for x in f],
        "vat": [vat_pct(y) for y in YEARS],
        "nitaqat": [nitaqat_wage(y) for y in YEARS],
        "esched": [elec_schedule(y) for y in YEARS],
        "wsched": [water_schedule(y) for y in YEARS],
        "elec_hist": historical_electricity_tariffs()[["schedule", "tier_from_kwh", "tier_to_kwh", "rate_halala"]]
            .replace({np.nan: None}).to_dict(orient="records"),
        "events": ev[["year", "title_ar", "title_en"]].to_dict(orient="records"),
    }
