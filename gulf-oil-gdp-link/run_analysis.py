"""Gulf economies and the oil price, 1988-2023.

Downloads real public data (World Bank GDP and population, EIA Brent monthly price,
all mirrored on GitHub by the Data Hub "datasets" project), measures how
closely each economy's GDP tracks the Brent price, and writes CSV tables,
charts and a short findings file to ``results/``.

Run:  python run_analysis.py            (uses a local cache after the first run)
      python run_analysis.py --refresh  (force re-download)
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import oil_gdp as og  # noqa: E402

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache"
RESULTS = HERE / "results"
CHARTS = RESULTS / "charts"

SOURCES = {
    "gdp": "https://raw.githubusercontent.com/datasets/gdp/main/data/gdp.csv",
    "population": "https://raw.githubusercontent.com/datasets/population/main/data/population.csv",
    "brent_monthly": "https://raw.githubusercontent.com/datasets/oil-prices/main/data/brent-monthly.csv",
}

# Growth years used for the regressions. 1993 is the first growth year after
# the 1990-91 Gulf War, which wrecked Kuwait's (and distorted the region's) GDP
# for reasons unrelated to the oil price.
FULL = (1993, 2023)
EARLY = (1993, 2008)
LATE = (2009, 2023)

COLORS = {
    "SAU": "#1b7f5a", "ARE": "#c0392b", "QAT": "#7d3c98", "KWT": "#2471a3",
    "OMN": "#d68910", "BHR": "#5d6d7e", "NOR": "#17a589", "EGY": "#a04000",
    "JOR": "#884ea0", "WLD": "#273746",
}


def fetch(name: str, refresh: bool = False) -> tuple[pd.DataFrame, dict]:
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"{name}.csv"
    if refresh or not path.exists():
        with urllib.request.urlopen(SOURCES[name], timeout=60) as r:
            path.write_bytes(r.read())
    raw = path.read_bytes()
    meta = {
        "url": SOURCES[name],
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "fetched_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
    }
    return pd.read_csv(io.BytesIO(raw)), meta


def in_period(s: pd.Series, period: tuple[int, int]) -> pd.Series:
    return s[(s.index >= period[0]) & (s.index <= period[1])]


def main(refresh: bool = False) -> dict:
    RESULTS.mkdir(exist_ok=True)
    CHARTS.mkdir(exist_ok=True)
    gdp_long, m_gdp = fetch("gdp", refresh)
    pop_long, m_pop = fetch("population", refresh)
    brent_monthly, m_brent = fetch("brent_monthly", refresh)

    codes = list(og.GCC) + list(og.BENCHMARKS)
    names = {**og.GCC, **og.BENCHMARKS}
    brent = og.annual_mean_price(brent_monthly)
    gdp = og.wide_by_country(gdp_long, codes)
    pop = og.wide_by_country(pop_long, codes)
    years = range(1988, int(gdp.index.max()) + 1)
    gdp = gdp.reindex(years)
    pop = pop.reindex(years)
    brent_y = brent.reindex(years)
    gdppc = og.per_capita(gdp, pop)

    # ---- tidy time-series table -------------------------------------------
    ts = pd.DataFrame({"brent_usd": brent_y.round(2)})
    for c in codes:
        ts[f"gdp_bn_usd_{c}"] = (gdp[c] / 1e9).round(2)
        ts[f"gdp_per_capita_usd_{c}"] = gdppc[c].round(0)
    ts.to_csv(RESULTS / "gdp_brent_timeseries.csv")

    # ---- elasticities -----------------------------------------------------
    d_oil = og.log_growth(brent_y)
    d_gdp = og.log_growth(gdp)
    rows = []
    for c in codes:
        for label, per in [("full", FULL), ("early", EARLY), ("late", LATE)]:
            e = og.elasticity(in_period(d_gdp[c], per), in_period(d_oil, per))
            if e is None:
                continue
            rows.append({
                "code": c, "country": names[c], "group": "GCC" if c in og.GCC else "benchmark",
                "period": label, "years": f"{per[0]}-{per[1]}", "n_years": e.n,
                "elasticity": round(e.slope, 3), "ci95_low": round(e.ci_low, 3),
                "ci95_high": round(e.ci_high, 3), "correlation": round(e.corr, 3),
                "r2": round(e.r2, 3),
            })
    el = pd.DataFrame(rows)
    el.to_csv(RESULTS / "elasticities.csv", index=False)

    # ---- per-capita summary -----------------------------------------------
    last = int(gdp.dropna(how="all").index.max())
    summ = []
    for c in codes:
        s = gdppc[c].dropna()
        end = int(s.index.max())
        summ.append({
            "code": c, "country": names[c],
            "gdp_per_capita_1995": round(float(s.get(1995, np.nan)), 0),
            "latest_year": end,
            "gdp_per_capita_latest": round(float(s.loc[end]), 0),
            "cagr_per_capita_1995_latest_pct": round(100 * og.cagr(s, 1995, end), 2),
            "population_growth_1995_latest_pct_per_year": round(100 * og.cagr(pop[c].dropna(), 1995, end), 2),
        })
    summ = pd.DataFrame(summ)
    summ.to_csv(RESULTS / "per_capita_summary.csv", index=False)

    # ---- charts -----------------------------------------------------------
    plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False})

    # 1. Indexed GDP vs Brent
    fig, ax = plt.subplots(figsize=(9, 5))
    base = 2000
    ax.plot(brent_y.index, 100 * brent_y / brent_y.loc[base], color="black", lw=2.6, ls="--", label="Brent oil price")
    for c in og.GCC:
        s = gdp[c].dropna()
        ax.plot(s.index, 100 * s / s.loc[base], color=COLORS[c], lw=1.6, label=names[c])
    ax.set_yscale("log")
    ax.set_title("GCC GDP (current US$) and the Brent price, index 2000 = 100 (log scale)")
    ax.set_ylabel("Index, 2000 = 100")
    ax.legend(ncol=2, fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(CHARTS / "gdp_vs_brent_index.png")
    plt.close(fig)

    # 2. Full-period elasticity with CI
    f = el[el.period == "full"].sort_values("elasticity")
    fig, ax = plt.subplots(figsize=(8, 5))
    y = np.arange(len(f))
    cols = [COLORS[c] for c in f.code]
    ax.barh(y, f.elasticity, color=cols, alpha=0.85)
    ax.errorbar(f.elasticity, y, xerr=[f.elasticity - f.ci95_low, f.ci95_high - f.elasticity],
                fmt="none", ecolor="black", capsize=3, lw=1)
    ax.set_yticks(y, f.country)
    ax.axvline(0, color="grey", lw=0.8)
    ax.set_xlabel("Elasticity of GDP (US$) to the Brent price, 1993-2023\n(bar = estimate, line = 95% bootstrap interval)")
    ax.set_title("How strongly does GDP move with oil?")
    fig.tight_layout()
    fig.savefig(CHARTS / "elasticity_full_period.png")
    plt.close(fig)

    # 3. Early vs late
    pv = el[el.period.isin(["early", "late"])].pivot(index="code", columns="period", values="elasticity").reindex(codes)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    x = np.arange(len(pv))
    ax.bar(x - 0.2, pv["early"], 0.4, label=f"{EARLY[0]}-{EARLY[1]}", color="#95a5a6")
    ax.bar(x + 0.2, pv["late"], 0.4, label=f"{LATE[0]}-{LATE[1]}", color="#1b7f5a")
    ax.set_xticks(x, [names[c].replace("United Arab Emirates", "UAE") for c in pv.index], rotation=30, ha="right")
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_ylabel("Elasticity to Brent")
    ax.set_title("Has the oil link weakened? Elasticity before and after 2008")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(CHARTS / "elasticity_early_vs_late.png")
    plt.close(fig)

    # 4. Rolling correlation
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for c in ["SAU", "KWT", "QAT", "ARE", "NOR", "WLD"]:
        rc = og.rolling_corr(d_gdp[c], d_oil, 10).dropna()
        rc = rc[rc.index >= FULL[0] + 9]
        ax.plot(rc.index, rc, color=COLORS[c], lw=1.8, label=names[c])
    ax.set_ylim(-1, 1)
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_ylabel("Correlation of yearly growth")
    ax.set_xlabel("Last year of the 10-year window")
    ax.set_title("Rolling 10-year correlation: GDP growth vs Brent price growth")
    ax.legend(ncol=3, fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(CHARTS / "rolling_correlation.png")
    plt.close(fig)

    # 5. Per capita
    s2 = summ.set_index("code").reindex(codes)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    x = np.arange(len(s2))
    ax.bar(x - 0.2, s2.gdp_per_capita_1995 / 1000, 0.4, label="1995", color="#95a5a6")
    ax.bar(x + 0.2, s2.gdp_per_capita_latest / 1000, 0.4, label="latest (2023; Qatar 2022)", color="#2471a3")
    ax.set_xticks(x, [names[c].replace("United Arab Emirates", "UAE") for c in s2.index], rotation=30, ha="right")
    ax.set_ylabel("GDP per person, thousand current US$")
    ax.set_title("GDP per person, 1995 vs latest")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(CHARTS / "gdp_per_capita.png")
    plt.close(fig)

    # ---- findings -----------------------------------------------------------
    full = el[el.period == "full"].set_index("code")
    gcc_full = full.loc[list(og.GCC)]
    lines = ["# Findings (generated by run_analysis.py)", ""]
    lines.append(f"Data: World Bank GDP in current US$ (to {last}), Brent annual average of EIA monthly prices.")
    lines.append("")
    lines.append(f"## Elasticity of GDP to the Brent price, {FULL[0]}-{FULL[1]}")
    for c, r in full.sort_values("elasticity", ascending=False).iterrows():
        lines.append(f"- {r.country}: {r.elasticity:.2f} (95% CI {r.ci95_low:.2f} to {r.ci95_high:.2f}), "
                     f"correlation {r.correlation:.2f}, {int(r.n_years)} years")
    lines.append("")
    lines.append(f"- GCC median elasticity: {gcc_full.elasticity.median():.2f}; "
                 f"World: {full.loc['WLD','elasticity']:.2f}; Norway: {full.loc['NOR','elasticity']:.2f}.")
    lines.append("")
    lines.append("## Early vs late period")
    for c in og.GCC:
        e, l_ = pv.loc[c, "early"], pv.loc[c, "late"]
        lines.append(f"- {names[c]}: {e:.2f} ({EARLY[0]}-{EARLY[1]}) -> {l_:.2f} ({LATE[0]}-{LATE[1]})")
    lines.append("")
    lines.append("## GDP per person (current US$)")
    for _, r in summ.iterrows():
        lines.append(f"- {r.country}: {r.gdp_per_capita_1995:,.0f} (1995) -> {r.gdp_per_capita_latest:,.0f} "
                     f"({r.latest_year}); {r.cagr_per_capita_1995_latest_pct:.2f}%/yr; "
                     f"population {r.population_growth_1995_latest_pct_per_year:.2f}%/yr")
    (RESULTS / "findings.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    meta = {"sources": {"gdp": m_gdp, "population": m_pop, "brent_monthly": m_brent},
            "brent_years": [int(brent.index.min()), int(brent.index.max())],
            "gdp_last_year": last}
    (RESULTS / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("\n".join(lines))
    return {"elasticities": el, "summary": summ}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh", action="store_true", help="re-download the data")
    main(ap.parse_args().refresh)
