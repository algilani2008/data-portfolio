"""Build the data behind the Arab Population Explorer site, plus a findings report.

Downloads the World Bank total population series (SP.POP.TOTL) as mirrored in the
`datasets/population` GitHub data package, keeps the 22 Arab League members, the World and
the World Bank "Arab World" aggregate, adds a GCC total, and writes:

  site/data.js                     embedded data, loaded by the page with a <script> tag
  results/summary_by_country.csv   one row per country: populations, growth, doubling time
  results/findings.md              headline findings, written from the numbers
  results/population_index.png     GCC vs the rest of the Arab world vs the world (1960 = 100)
  results/growth_ranking.png       how many times each country grew since 1960
  results/metadata.json            source URL, SHA-256 of the downloaded file, years covered

Nothing is imputed: a year missing in the source stays missing on the site.

Usage:  python build_data.py            (downloads the CSV)
        python build_data.py --csv FILE (uses a local copy, e.g. for offline runs)
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

from popcalc import cagr, doubling_time, growth_multiple

SOURCE_URL = "https://raw.githubusercontent.com/datasets/population/main/data/population.csv"
HERE = Path(__file__).resolve().parent
SITE = HERE / "site"
RESULTS = HERE / "results"

FIRST_YEAR = 1960
RECENT_WINDOW = 10  # years used for "recent" growth rate

GCC = ["SAU", "ARE", "QAT", "KWT", "OMN", "BHR"]

# code: (English name, Arabic name). Arab League members, World Bank ISO3 codes.
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
AGGREGATES = {
    "WLD": ("World", "العالم"),
    "ARB": ("Arab World (World Bank aggregate)", "العالم العربي (تجميع البنك الدولي)"),
    "GCC": ("GCC total", "مجموع دول الخليج"),
}


def load_source(csv_path: str | None) -> tuple[pd.DataFrame, str, str]:
    """Return (long frame, sha256, where it came from)."""
    if csv_path:
        raw = Path(csv_path).read_bytes()
        origin = str(csv_path)
    else:
        with urllib.request.urlopen(SOURCE_URL, timeout=120) as resp:
            raw = resp.read()
        origin = SOURCE_URL
    df = pd.read_csv(io.BytesIO(raw))
    df.columns = ["name", "code", "year", "value"]
    return df, hashlib.sha256(raw).hexdigest(), origin


def to_wide(df: pd.DataFrame) -> pd.DataFrame:
    """Rows = years, columns = codes we need (countries + WLD + ARB + computed GCC)."""
    keep = list(COUNTRIES) + ["WLD", "ARB"]
    missing = [c for c in keep if c not in set(df["code"])]
    if missing:
        raise ValueError(f"codes missing from source: {missing}")
    wide = (
        df[df["code"].isin(keep) & (df["year"] >= FIRST_YEAR)]
        .pivot_table(index="year", columns="code", values="value", aggfunc="first")
        .reindex(columns=keep)
        .sort_index()
    )
    # GCC total only where all six members have a value (no partial sums).
    gcc = wide[GCC].sum(axis=1, min_count=len(GCC))
    wide["GCC"] = gcc.where(wide[GCC].notna().all(axis=1))
    return wide


def latest_complete_year(wide: pd.DataFrame) -> int:
    """Latest year in which every one of the 22 countries has a value."""
    complete = wide[list(COUNTRIES)].notna().all(axis=1)
    return int(complete[complete].index.max())


def full_series_countries(wide: pd.DataFrame, last: int) -> list[str]:
    """Countries with a value in every year from FIRST_YEAR to `last`."""
    block = wide.loc[FIRST_YEAR:last, list(COUNTRIES)]
    return [c for c in COUNTRIES if block[c].notna().all()]


def summarise(wide: pd.DataFrame, last: int) -> pd.DataFrame:
    rows = []
    arab_total = wide.loc[last, list(COUNTRIES)].sum()
    recent_start = last - RECENT_WINDOW
    for code, (en, ar) in {**COUNTRIES, **AGGREGATES}.items():
        s = wide[code]
        p0, p90, p_rs, p_last = s.get(FIRST_YEAR), s.get(1990), s.get(recent_start), s.get(last)
        r_recent = cagr(p_rs, p_last, RECENT_WINDOW)
        has0 = pd.notna(p0)  # the Palestine series starts in 1990
        rows.append(
            {
                "code": code,
                "name_en": en,
                "name_ar": ar,
                "is_country": code in COUNTRIES,
                "gcc": code in GCC,
                f"pop_{FIRST_YEAR}": int(p0) if has0 else None,
                "pop_1990": int(p90),
                f"pop_{last}": int(p_last),
                f"times_bigger_since_{FIRST_YEAR}": round(growth_multiple(p0, p_last), 2) if has0 else None,
                f"avg_growth_pct_{FIRST_YEAR}_{last}": (
                    round(100 * cagr(p0, p_last, last - FIRST_YEAR), 2) if has0 else None
                ),
                f"avg_growth_pct_{recent_start}_{last}": round(100 * r_recent, 2),
                "doubling_years_at_recent_rate": (
                    round(doubling_time(r_recent), 1) if r_recent > 0 else None
                ),
                "share_of_arab_total_pct": (
                    round(100 * p_last / arab_total, 2) if code in COUNTRIES or code == "GCC" else None
                ),
            }
        )
    out = pd.DataFrame(rows)
    pop_cols = [c for c in out.columns if c.startswith("pop_")]
    return out.astype({c: "Int64" for c in pop_cols})


def findings(wide: pd.DataFrame, summary: pd.DataFrame, last: int) -> list[str]:
    c = summary[summary["is_country"]].set_index("code")
    times = c[f"times_bigger_since_{FIRST_YEAR}"].dropna().sort_values(ascending=False)
    rs = last - RECENT_WINDOW
    recent = c[f"avg_growth_pct_{rs}_{last}"].sort_values(ascending=False)
    full = full_series_countries(wide, last)
    arab = wide[full].sum(axis=1)
    gcc_share_0 = 100 * wide.loc[FIRST_YEAR, "GCC"] / arab[FIRST_YEAR]
    gcc_share_n = 100 * wide.loc[last, "GCC"] / arab[last]
    world_times = growth_multiple(wide.loc[FIRST_YEAR, "WLD"], wide.loc[last, "WLD"])
    arab_times = growth_multiple(arab[FIRST_YEAR], arab[last])
    sau = wide["SAU"]
    sau_dips = [int(y) for y in sau.index[1:] if sau[y] < sau[y - 1]]
    world_share_0 = 100 * arab[FIRST_YEAR] / wide.loc[FIRST_YEAR, "WLD"]
    world_share_n = 100 * arab[last] / wide.loc[last, "WLD"]

    gaps = [COUNTRIES[k][0] for k in COUNTRIES if k not in full]
    if gaps:
        out_note = f" (not included, series starts later: {', '.join(gaps)})"
    else:
        out_note = ""

    def name(code: str) -> str:
        return COUNTRIES[code][0]

    out = [
        f"The {len(full)} Arab League countries with data back to {FIRST_YEAR} together grew from {arab[FIRST_YEAR]/1e6:.1f} million people in "
        f"{FIRST_YEAR} to {arab[last]/1e6:.1f} million in {last}: {arab_times:.1f}x, versus "
        f"{world_times:.1f}x for the world. Their share of humanity rose from {world_share_0:.1f}% to "
        f"{world_share_n:.1f}%{out_note}.",
        f"Fastest growth since {FIRST_YEAR}: {name(times.index[0])} ({times.iloc[0]:.0f}x), "
        f"{name(times.index[1])} ({times.iloc[1]:.0f}x) and {name(times.index[2])} "
        f"({times.iloc[2]:.0f}x). Slowest: {name(times.index[-1])} ({times.iloc[-1]:.1f}x).",
        f"Saudi Arabia went from {sau[FIRST_YEAR]/1e6:.1f} million to {sau[last]/1e6:.1f} million "
        f"({growth_multiple(sau[FIRST_YEAR], sau[last]):.1f}x). Years in which the series fell versus "
        f"the year before: {', '.join(map(str, sau_dips)) if sau_dips else 'none'}.",
        f"The six GCC states held {gcc_share_0:.1f}% of the population of those {len(full)} countries in {FIRST_YEAR} and "
        f"{gcc_share_n:.1f}% in {last}.",
        f"Fastest average growth over the last {RECENT_WINDOW} years ({rs}-{last}): "
        f"{name(recent.index[0])} ({recent.iloc[0]:.2f}%/yr), {name(recent.index[1])} "
        f"({recent.iloc[1]:.2f}%/yr). Slowest: {name(recent.index[-1])} ({recent.iloc[-1]:.2f}%/yr).",
    ]
    return out


def make_charts(wide: pd.DataFrame, summary: pd.DataFrame, last: int) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    others = [c for c in full_series_countries(wide, last) if c not in GCC]
    rest = wide[others].sum(axis=1)
    lines = {
        "GCC (6 countries)": (wide["GCC"], "#2a6f97"),
        f"Other {len(others)} Arab countries": (rest, "#e07a1f"),
        "World": (wide["WLD"], "#6b6b6b"),
    }
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    for label, (s, color) in lines.items():
        s = s.loc[FIRST_YEAR:last]
        ax.plot(s.index, 100 * s / s.iloc[0], label=label, color=color, linewidth=2)
    ax.set_yscale("log")
    ax.set_yticks([100, 200, 400, 800, 1600])
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_ylabel(f"Population index ({FIRST_YEAR} = 100, log scale)")
    ax.set_title(f"Population growth since {FIRST_YEAR}")
    ax.grid(alpha=0.25)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False)
    ax.text(0, -0.14, "Source: World Bank SP.POP.TOTL via datasets/population", transform=ax.transAxes,
            fontsize=7, color="#555")
    fig.tight_layout()
    fig.savefig(RESULTS / "population_index.png")
    plt.close(fig)

    col = f"times_bigger_since_{FIRST_YEAR}"
    c = summary[summary["is_country"]].dropna(subset=[col]).sort_values(col)
    fig, ax = plt.subplots(figsize=(8, 6.5), dpi=150)
    colors = ["#2a6f97" if g else "#e07a1f" for g in c["gcc"]]
    ax.barh(c["name_en"], c[f"times_bigger_since_{FIRST_YEAR}"], color=colors)
    w = growth_multiple(wide.loc[FIRST_YEAR, "WLD"], wide.loc[last, "WLD"])
    ax.axvline(w, color="#6b6b6b", linestyle="--", linewidth=1)
    ax.text(w, -1.2, f" world {w:.1f}x", color="#6b6b6b", fontsize=8, va="bottom")
    ax.set_xscale("log")
    ax.set_xticks([1, 2, 5, 10, 20, 50])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_xlabel(f"Times bigger in {last} than in {FIRST_YEAR} (log scale; blue = GCC)")
    ax.set_title(f"How many times each Arab country grew, {FIRST_YEAR}-{last}")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(RESULTS / "growth_ranking.png")
    plt.close(fig)


def write_site_data(wide: pd.DataFrame, last: int, sha: str) -> None:
    years = [int(y) for y in wide.loc[FIRST_YEAR:last].index]
    series = {}
    for code, (en, ar) in {**COUNTRIES, **AGGREGATES}.items():
        vals = wide.loc[FIRST_YEAR:last, code]
        series[code] = {
            "en": en,
            "ar": ar,
            "gcc": code in GCC,
            "country": code in COUNTRIES,
            "v": [None if (isinstance(x, float) and math.isnan(x)) else int(x) for x in vals],
        }
    payload = {
        "meta": {
            "source": "World Bank, Population total (SP.POP.TOTL)",
            "mirror": SOURCE_URL,
            "sha256": sha,
            "first_year": years[0],
            "last_year": years[-1],
        },
        "years": years,
        "series": series,
    }
    text = "// Generated by build_data.py - do not edit by hand.\nwindow.POP_DATA = " + json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ) + ";\n"
    (SITE / "data.js").write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", help="local copy of population.csv instead of downloading")
    ap.add_argument("--no-charts", action="store_true")
    args = ap.parse_args(argv)

    RESULTS.mkdir(exist_ok=True)
    df, sha, origin = load_source(args.csv)
    wide = to_wide(df)
    last = latest_complete_year(wide)
    summary = summarise(wide, last)
    summary.to_csv(RESULTS / "summary_by_country.csv", index=False)
    lines = findings(wide, summary, last)
    (RESULTS / "findings.md").write_text(
        f"# Findings ({FIRST_YEAR}-{last})\n\nGenerated by `build_data.py` from World Bank data.\n\n"
        + "\n".join(f"- {line}" for line in lines)
        + "\n",
        encoding="utf-8",
    )
    write_site_data(wide, last, sha)
    if not args.no_charts:
        make_charts(wide, summary, last)
    (RESULTS / "metadata.json").write_text(
        json.dumps(
            {"source": origin, "sha256": sha, "first_year": FIRST_YEAR, "last_year": last,
             "countries": len(COUNTRIES)},
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print("\n".join(lines))


if __name__ == "__main__":
    main()
