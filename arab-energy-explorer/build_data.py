"""Build the data file behind the Arab Energy Explorer site.

Downloads the Our World in Data energy and CO2 datasets (CC BY 4.0), keeps the 22 Arab
League member states plus the World aggregate, and writes:

  site/data.js                 embedded data, loaded by the page with a <script> tag
  results/latest_by_country.csv  one row per country for the latest year
  results/findings.md          headline findings, written from the data
  results/metadata.json        source URLs, SHA-256 of the files used, end year

Nothing is imputed: a value missing from the source stays missing on the site.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import urllib.request
from pathlib import Path

import pandas as pd

ENERGY_URL = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"
CO2_URL = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"

START_YEAR = 2000
# The end year is the latest year with electricity data for at least this share of countries,
# so a year reported by only a handful of countries does not become the "latest" ranking.
MIN_COVERAGE = 0.75

WORLD = "WLD"

# code: (English name, Arabic name). Arab League members, in the source's ISO codes.
COUNTRIES = {
    "SAU": ("Saudi Arabia", "السعودية"),
    "ARE": ("United Arab Emirates", "الإمارات"),
    "QAT": ("Qatar", "قطر"),
    "KWT": ("Kuwait", "الكويت"),
    "OMN": ("Oman", "عُمان"),
    "BHR": ("Bahrain", "البحرين"),
    "IRQ": ("Iraq", "العراق"),
    "JOR": ("Jordan", "الأردن"),
    "LBN": ("Lebanon", "لبنان"),
    "PSE": ("Palestine", "فلسطين"),
    "SYR": ("Syria", "سوريا"),
    "YEM": ("Yemen", "اليمن"),
    "EGY": ("Egypt", "مصر"),
    "SDN": ("Sudan", "السودان"),
    "LBY": ("Libya", "ليبيا"),
    "TUN": ("Tunisia", "تونس"),
    "DZA": ("Algeria", "الجزائر"),
    "MAR": ("Morocco", "المغرب"),
    "MRT": ("Mauritania", "موريتانيا"),
    "SOM": ("Somalia", "الصومال"),
    "DJI": ("Djibouti", "جيبوتي"),
    "COM": ("Comoros", "جزر القمر"),
}

# Columns shown as selectable metrics: site key -> (source frame, decimals kept).
METRICS = {
    "electricity_generation": ("energy", 2),
    "per_capita_electricity": ("energy", 0),
    "low_carbon_share_elec": ("energy", 2),
    "solar_share_elec": ("energy", 2),
    "wind_share_elec": ("energy", 2),
    "gas_share_elec": ("energy", 2),
    "oil_share_elec": ("energy", 2),
    "carbon_intensity_elec": ("energy", 1),
    "co2": ("co2", 2),
    "co2_per_capita": ("co2", 2),
}

# Generation by source in TWh, for the mix bar. The order matches the chart's colour slots.
SOURCES = {
    "gas": "gas_electricity",
    "oil": "oil_electricity",
    "hydro": "hydro_electricity",
    "solar": "solar_electricity",
    "nuclear": "nuclear_electricity",
    "wind": "wind_electricity",
    "coal": "coal_electricity",
    "other": "other_renewable_electricity",
}
EXTRA = {"fossil_electricity": 2, "low_carbon_electricity": 2}


def fetch(url: str, cache_dir: Path) -> tuple[pd.DataFrame, str]:
    """Read a CSV from the cache or download it. Returns (frame, sha256 of the bytes)."""
    path = cache_dir / url.rsplit("/", 1)[1]
    if path.exists():
        raw = path.read_bytes()
    else:
        with urllib.request.urlopen(url, timeout=180) as resp:  # noqa: S310 - fixed https URL
            raw = resp.read()
        cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return pd.read_csv(io.BytesIO(raw), low_memory=False), hashlib.sha256(raw).hexdigest()


def select(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the listed countries and World, from START_YEAR on, with a `code` column."""
    keep = df["iso_code"].isin(COUNTRIES) | (df["country"] == "World")
    out = df.loc[keep & (df["year"] >= START_YEAR)].copy()
    out["code"] = out["iso_code"].where(out["country"] != "World", WORLD)
    return out


def end_year(energy: pd.DataFrame, min_coverage: float = MIN_COVERAGE) -> int:
    """Latest year in which enough countries report electricity generation."""
    arab = energy[energy["code"] != WORLD]
    counts = arab[arab["electricity_generation"].notna()].groupby("year")["code"].nunique()
    good = counts[counts >= min_coverage * len(COUNTRIES)]
    if good.empty:
        raise ValueError("no year reaches the coverage threshold")
    return int(good.index.max())


def clean(value, decimals: int):
    """JSON-safe rounded number, or None when missing. Never fills gaps."""
    if value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value):
        return None
    number = round(float(value), decimals)
    return int(number) if decimals == 0 else number


def series(df: pd.DataFrame, code: str, column: str, years: list[int], decimals: int) -> list:
    """Values of one column for one country, aligned to `years`, None where missing."""
    if column not in df.columns:
        return [None] * len(years)
    sub = df[df["code"] == code].drop_duplicates("year").set_index("year")[column]
    return [clean(sub.get(year), decimals) for year in years]


def build_payload(energy: pd.DataFrame, co2: pd.DataFrame, last: int) -> dict:
    """Assemble the JSON-serialisable structure embedded in site/data.js."""
    years = list(range(START_YEAR, last + 1))
    frames = {"energy": energy, "co2": co2}
    values = {}
    for code in [*COUNTRIES, WORLD]:
        row = {m: series(frames[src], code, m, years, dec) for m, (src, dec) in METRICS.items()}
        row["mix"] = {s: series(energy, code, col, years, 2) for s, col in SOURCES.items()}
        for col, dec in EXTRA.items():
            row[col] = series(energy, code, col, years, dec)
        values[code] = row
    return {"years": years, "values": values}


def arab_total(energy: pd.DataFrame, year: int) -> dict:
    """Totals across the listed countries that report generation in `year`."""
    sub = energy[(energy["code"] != WORLD) & (energy["year"] == year)]
    sub = sub[sub["electricity_generation"].notna()]
    gen = float(sub["electricity_generation"].sum())
    low = float(sub["low_carbon_electricity"].sum())
    return {
        "countries": int(sub["code"].nunique()),
        "generation_twh": round(gen, 1),
        "low_carbon_twh": round(low, 1),
        "low_carbon_share_pct": round(low / gen * 100, 1),
        "population": float(sub["population"].sum()),
    }


def latest_table(energy: pd.DataFrame, co2: pd.DataFrame, year: int) -> pd.DataFrame:
    """One row per country (and World) for `year`."""
    cols = ["code", "country", "population", "electricity_generation", "per_capita_electricity",
            "low_carbon_share_elec", "solar_share_elec", "wind_share_elec", "gas_share_elec",
            "oil_share_elec", "carbon_intensity_elec"]
    left = energy.loc[energy["year"] == year, cols]
    right = co2.loc[co2["year"] == year, ["code", "co2", "co2_per_capita"]]
    out = left.merge(right, on="code", how="left")
    return out.sort_values("low_carbon_share_elec", ascending=False).reset_index(drop=True)


def _name(code: str, lang: int) -> str:
    return "World" if code == WORLD else COUNTRIES[code][lang]


def highlights(energy: pd.DataFrame, year: int, base: int = 2015) -> list[dict]:
    """Findings computed from the data, one {ar, en} dict each."""
    now = energy[energy["year"] == year].set_index("code")
    arab = now.drop(index=WORLD)
    total = arab_total(energy, year)
    world = now.loc[WORLD]

    pop_share = total["population"] / world["population"] * 100
    gen_share = total["generation_twh"] / world["electricity_generation"] * 100
    w_low = world["low_carbon_share_elec"]

    per = arab["per_capita_electricity"].dropna()
    hi, lo = per.idxmax(), per.idxmin()
    ratio = per[hi] / per[lo]

    # Only countries above 10 TWh, so a tiny system does not lead the ranking on one project.
    big = arab[arab["electricity_generation"] >= 10]["low_carbon_share_elec"].sort_values(ascending=False)
    top = big.index[:3]

    then = energy[(energy["year"] == base) & (energy["code"] != WORLD)].set_index("code")
    gain = (arab["low_carbon_share_elec"] - then["low_carbon_share_elec"]).dropna()
    gain = gain[arab["electricity_generation"].reindex(gain.index) >= 10].sort_values(ascending=False)
    gainer = gain.index[0]

    top_en = ", ".join(f"{_name(c, 0)} {big[c]:.0f}%" for c in top)
    top_ar = "، ".join(f"{_name(c, 1)} {big[c]:.0f}%" for c in top)
    return [
        {"en": f"Arab countries hold {pop_share:.1f}% of the world's people and generate "
               f"{gen_share:.1f}% of its electricity. {total['low_carbon_share_pct']:.1f}% of that "
               f"electricity is low-carbon, against {w_low:.1f}% for the world.",
         "ar": f"الدول العربية فيها {pop_share:.1f}% من سكان العالم وتنتج {gen_share:.1f}% من كهربائه. "
               f"{total['low_carbon_share_pct']:.1f}% من هذي الكهرباء منخفضة الكربون، "
               f"مقابل {w_low:.1f}% في العالم."},
        {"en": f"Among systems above 10 TWh, the cleanest electricity in {year} is in {top_en}. "
               f"The largest gain since {base}: {_name(gainer, 0)}, up {gain[gainer]:.1f} points.",
         "ar": f"بين الأنظمة اللي تتجاوز 10 تيراواط ساعة، أنظف كهرباء في {year}: {top_ar}. "
               f"وأكبر تقدم منذ {base}: {_name(gainer, 1)} بزيادة {gain[gainer]:.1f} نقطة."},
        {"en": f"The gap is wide: a person's share of generation in {_name(hi, 0)} "
               f"({per[hi]:,.0f} kWh) is {ratio:,.0f} times that in {_name(lo, 0)} ({per[lo]:,.0f} kWh).",
         "ar": f"الفجوة كبيرة: نصيب الفرد من إنتاج الكهرباء في {_name(hi, 1)} "
               f"({per[hi]:,.0f} ك.و.س) يعادل {ratio:,.0f} ضعف نصيبه في {_name(lo, 1)} "
               f"({per[lo]:,.0f} ك.و.س)."},
    ]


def findings_markdown(highlight_list: list[dict], year: int, total: dict) -> str:
    lines = [f"# Findings (computed by build_data.py, latest year {year})", ""]
    lines += [f"- {h['en']}" for h in highlight_list]
    lines += ["", f"Totals cover the {total['countries']} of {len(COUNTRIES)} countries with "
                  f"{year} electricity data: {total['generation_twh']} TWh generated, "
                  f"{total['low_carbon_twh']} TWh low-carbon.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    here = Path(__file__).resolve().parent
    parser.add_argument("--cache-dir", type=Path, default=here / ".cache")
    args = parser.parse_args()

    energy_raw, energy_sha = fetch(ENERGY_URL, args.cache_dir)
    co2_raw, co2_sha = fetch(CO2_URL, args.cache_dir)
    energy, co2 = select(energy_raw), select(co2_raw)
    last = end_year(energy)

    payload = build_payload(energy, co2, last)
    payload["countries"] = [{"code": c, "en": en, "ar": ar} for c, (en, ar) in COUNTRIES.items()]
    payload["sources"] = list(SOURCES)
    payload["highlights"] = highlights(energy, last)
    payload["total"] = arab_total(energy, last)

    site, results = here / "site", here / "results"
    results.mkdir(exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    (site / "data.js").write_text(
        "// Generated by build_data.py from Our World in Data (CC BY 4.0). Do not edit by hand.\n"
        f"window.AEE_DATA={text};\n", encoding="utf-8")

    latest_table(energy, co2, last).to_csv(results / "latest_by_country.csv", index=False)
    (results / "findings.md").write_text(
        findings_markdown(payload["highlights"], last, payload["total"]), encoding="utf-8")
    meta = {
        "end_year": last,
        "start_year": START_YEAR,
        "licence": "CC BY 4.0",
        "sources": [{"url": ENERGY_URL, "sha256": energy_sha}, {"url": CO2_URL, "sha256": co2_sha}],
    }
    (results / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote site/data.js ({len(text) / 1024:.0f} KB), end year {last}")
    print(findings_markdown(payload["highlights"], last, payload["total"]))


if __name__ == "__main__":
    main()
