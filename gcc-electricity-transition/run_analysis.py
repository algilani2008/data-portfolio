"""Run the GCC electricity transition analysis and write results/ (CSV, charts, findings).

Usage:
    python run_analysis.py               # downloads the OWID CSV into .cache/
    python run_analysis.py --offline     # reuse .cache/owid-energy-data.csv
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import gcc_power as gp  # noqa: E402

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache" / "owid-energy-data.csv"
OUT = HERE / "results"
START, GROWTH_FROM = 2000, 2015

# Fixed categorical order (colour follows the country, never its rank).
COLORS = {"SAU": "#2a78d6", "ARE": "#eb6834", "QAT": "#1baf7a", "KWT": "#eda100",
          "OMN": "#e87ba4", "BHR": "#008300", "WLD": "#52514e"}
SRC_COLORS = {"gas": "#2a78d6", "oil": "#eb6834", "solar": "#eda100", "wind": "#1baf7a",
              "nuclear": "#6250d6", "coal": "#3d3d3a", "hydro": "#7fb3e8",
              "other_renewable": "#008300", "other": "#b8b7b1"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def _style(ax, title, ylabel=None):
    ax.set_title(title, loc="left", fontsize=12, color=INK, pad=12)
    if ylabel:
        ax.set_ylabel(ylabel, color=MUTED)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def chart_low_carbon(df, end, path):
    fig, ax = plt.subplots(figsize=(9, 5.2))
    labels = []
    for code in [*gp.GCC, "WLD"]:
        s = df[(df["code"] == code) & (df["year"] >= 2010)]
        ls = "--" if code == "WLD" else "-"
        ax.plot(s["year"], s["low_carbon_share_elec"], ls, color=COLORS[code], lw=2)
        last = s.iloc[-1]
        name = "World" if code == "WLD" else gp.GCC[code]
        labels.append([last["low_carbon_share_elec"], f"{name} {last['low_carbon_share_elec']:.1f}%"])
    # Spread end labels so they never overlap (minimum gap in data units).
    labels.sort()
    gap = 1.6
    for i in range(1, len(labels)):
        labels[i][0] = max(labels[i][0], labels[i - 1][0] + gap)
    for y, text in labels:
        ax.text(end + 0.25, y, text, va="center", fontsize=8.5, color=INK)
    ax.set_xlim(2010, end + 3.6)
    ax.set_xticks(range(2010, end + 1, 2))
    _style(ax, f"Low-carbon share of electricity (solar, wind, nuclear, hydro), 2010-{end}", "% of generation")
    fig.text(0.01, 0.01, "Source: Our World in Data energy dataset (CC BY 4.0)", fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def chart_mix(shares, end, path):
    order = [c for c in gp.GCC if c in shares.index] + ["WLD"]
    sources = [s for s in SRC_COLORS if s in shares.columns and shares.loc[order, s].max() >= 0.05]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    labels = ["World" if c == "WLD" else gp.GCC[c] for c in order]
    left = [0.0] * len(order)
    for src in sources:
        vals = shares.loc[order, src].tolist()
        ax.barh(labels, vals, left=left, color=SRC_COLORS[src], edgecolor="white", linewidth=1.5,
                label=src.replace("_", " "))
        left = [a + b for a, b in zip(left, vals)]
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    _style(ax, f"Electricity generation mix, {end} (% of total)")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    ax.legend(ncol=len(sources), loc="upper center", bbox_to_anchor=(0.5, -0.08), frameon=False, fontsize=8.5)
    fig.text(0.01, 0.01, "Source: Our World in Data energy dataset (CC BY 4.0)", fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def chart_per_capita(table, end, path):
    t = table.sort_values(f"per_capita_kwh_{end}")
    labels = ["World" if c == "WLD" else gp.GCC[c] for c in t["code"]]
    vals = t[f"per_capita_kwh_{end}"]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.barh(labels, vals, color=[COLORS[c] for c in t["code"]], height=0.6)
    for y, v in enumerate(vals):
        ax.text(v + 250, y, f"{v:,.0f}", va="center", fontsize=8.5, color=INK)
    _style(ax, f"Electricity generated per person, {end} (kWh)")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, vals.max() * 1.15)
    fig.text(0.01, 0.01, "Source: Our World in Data energy dataset (CC BY 4.0)", fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def chart_growth(table, end, path):
    t = table[table["code"] != "WLD"]
    k = f"{GROWTH_FROM}_{end}"
    labels = [gp.GCC[c] for c in t["code"]]
    lc = t[f"added_low_carbon_twh_{k}"].clip(lower=0)
    fossil = (t[f"added_twh_{k}"] - lc).clip(lower=0)  # negative = fossil output fell
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.barh(labels, lc, color="#1baf7a", edgecolor="white", linewidth=1.5, label="from low-carbon sources")
    ax.barh(labels, fossil, left=lc, color="#b8b7b1", edgecolor="white", linewidth=1.5,
            label="from fossil fuels (and other)")
    for y, (a, p) in enumerate(zip(t[f"added_twh_{k}"], t[f"low_carbon_share_of_growth_pct_{k}"])):
        ax.text(max(a, lc.iloc[y]) + 2, y, f"+{a:.0f} TWh, {p:.0f}% low-carbon", va="center", fontsize=8.5, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, (lc + fossil).max() * 1.45)
    _style(ax, f"Extra electricity produced in {end} vs {GROWTH_FROM} (TWh), and who supplied it")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    fig.text(0.01, 0.01, "Source: Our World in Data energy dataset (CC BY 4.0)", fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def findings(table, shares, end):
    k = f"{GROWTH_FROM}_{end}"
    t = table.set_index("code")
    gcc = t.drop(index="WLD")
    w = t.loc["WLD"]
    lines = [f"# Findings (computed by run_analysis.py, latest common year {end})", ""]
    top = gcc[f"low_carbon_share_pct_{end}"].idxmax()
    lines.append(f"- **Low-carbon leader:** {gp.GCC[top]} produced {gcc.at[top, f'low_carbon_share_pct_{end}']:.1f}% "
                 f"of its electricity from low-carbon sources in {end} (nuclear {shares.at[top, 'nuclear']:.1f}% + "
                 f"solar {shares.at[top, 'solar']:.1f}%). The other five GCC countries were all at or below "
                 f"{gcc.drop(index=top)[f'low_carbon_share_pct_{end}'].max():.1f}%, versus "
                 f"{w[f'low_carbon_share_pct_{end}']:.1f}% for the world.")
    s = gcc.loc["SAU"]
    lines.append(f"- **Saudi Arabia:** oil's share of electricity fell from {s[f'oil_share_pct_{GROWTH_FROM}']:.1f}% "
                 f"({GROWTH_FROM}) to {s[f'oil_share_pct_{end}']:.1f}% ({end}); low-carbon share rose from "
                 f"{s[f'low_carbon_share_pct_{GROWTH_FROM}']:.2f}% to {s[f'low_carbon_share_pct_{end}']:.2f}%. "
                 f"Generation grew {s[f'generation_cagr_pct_{START}_{end}']:.1f}% a year since {START} "
                 f"({s[f'generation_twh_{START}']:.0f} -> {s[f'generation_twh_{end}']:.0f} TWh).")
    lines.append(f"- **Growth mostly met by fossil fuels:** of the extra electricity produced across the GCC between "
                 f"{GROWTH_FROM} and {end} ({gcc[f'added_twh_{k}'].sum():.0f} TWh), "
                 f"{gcc[f'added_low_carbon_twh_{k}'].sum() / gcc[f'added_twh_{k}'].sum() * 100:.0f}% came from "
                 f"low-carbon sources. By country: " + ", ".join(
                     f"{gp.GCC[c]} {gcc.at[c, f'low_carbon_share_of_growth_pct_{k}']:.0f}%" for c in gcc.index) + ". A value above 100% means low-carbon output grew by more than total demand, so fossil-fuel generation actually fell.")
    pc = gcc[f"per_capita_kwh_{end}"]
    lines.append(f"- **Per person:** every GCC country generated more electricity per person than the world average "
                 f"({w[f'per_capita_kwh_{end}']:,.0f} kWh): from {pc.min():,.0f} kWh ({gp.GCC[pc.idxmin()]}) to "
                 f"{pc.max():,.0f} kWh ({gp.GCC[pc.idxmax()]}), i.e. {pc.min() / w[f'per_capita_kwh_{end}']:.1f}x to "
                 f"{pc.max() / w[f'per_capita_kwh_{end}']:.1f}x.")
    ci = gcc[f"carbon_intensity_g_per_kwh_{end}"]
    lines.append(f"- **Carbon intensity:** grams of CO2-equivalent per kWh ranged from {ci.min():.0f} "
                 f"({gp.GCC[ci.idxmin()]}) to {ci.max():.0f} ({gp.GCC[ci.idxmax()]}), versus "
                 f"{w[f'carbon_intensity_g_per_kwh_{end}']:.0f} for the world.")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true", help="use the cached CSV only")
    args = ap.parse_args(argv)
    if args.offline and not CACHE.exists():
        raise SystemExit(f"--offline given but {CACHE} does not exist")
    raw, sha = gp.download(cache=CACHE)
    df = gp.select(raw, START, 2100)
    end = gp.latest_common_year(df)
    df = df[df["year"] <= end]

    OUT.mkdir(exist_ok=True)
    (OUT / "charts").mkdir(exist_ok=True)
    shares = gp.mix_shares(df, end)
    table = gp.summary_table(df, START, end, GROWTH_FROM)

    df.drop(columns=["iso_code"]).to_csv(OUT / "gcc_electricity_timeseries.csv", index=False)
    shares.to_csv(OUT / f"generation_mix_{end}.csv")
    table.to_csv(OUT / "summary_by_country.csv", index=False)

    chart_low_carbon(df, end, OUT / "charts" / "low_carbon_share.png")
    chart_mix(shares, end, OUT / "charts" / "generation_mix.png")
    chart_per_capita(table, end, OUT / "charts" / "per_capita_electricity.png")
    chart_growth(table, end, OUT / "charts" / "growth_low_carbon_vs_fossil.png")

    text = findings(table, shares, end)
    (OUT / "findings.md").write_text(text, encoding="utf-8")
    meta = {"source": gp.OWID_URL, "license": "CC BY 4.0 (Our World in Data)",
            "sha256": sha, "rows_in_source": int(len(raw)), "latest_common_year": int(end),
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    (OUT / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
