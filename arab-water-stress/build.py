"""Build the Arab water stress analysis from public World Bank / FAO AQUASTAT data.

Usage:
    python build.py            # download (or reuse cache), write results/
    python build.py --offline  # only use files already in raw_cache/

Data: World Development Indicators (World Bank, CC BY 4.0; water series from
FAO AQUASTAT), read from Gapminder's open-numbers mirror on GitHub, pinned to a
fixed commit so the numbers are reproducible.

Outputs (results/):
    water_stress_latest.csv     latest SDG 6.4.2 water stress per country + class
    water_per_person.csv        renewable internal freshwater per person, first year vs 2022
    withdrawals_by_sector.csv   agriculture / industry / domestic shares
    saudi_withdrawals.csv       Saudi total withdrawals by year vs renewable resources
    water_productivity.csv      GDP (constant 2015 US$) per m3 withdrawn
    findings.md                 headline findings, every number computed here
    metadata.json               source URLs, commit, SHA-256 of every file, checks
    *.png                       charts
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

import water  # noqa: E402

HERE = Path(__file__).resolve().parent
CACHE = HERE / "raw_cache"
RESULTS = HERE / "results"

REPO = "open-numbers/ddf--open_numbers--world_development_indicators"
COMMIT = "1bd7fac42b3d5012353607bf2464a485557fd049"
BASE = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}"

INDICATORS = {
    "er_h2o_fwst_zs": "Level of water stress (% of available freshwater), SDG 6.4.2",
    "er_h2o_intr_pc": "Renewable internal freshwater per capita (m3)",
    "er_h2o_intr_k3": "Renewable internal freshwater resources (billion m3)",
    "er_h2o_fwtl_k3": "Annual freshwater withdrawals, total (billion m3)",
    "er_h2o_fwag_zs": "Withdrawals, agriculture (% of total)",
    "er_h2o_fwin_zs": "Withdrawals, industry (% of total)",
    "er_h2o_fwdm_zs": "Withdrawals, domestic (% of total)",
    "er_gdp_fwtl_m3_kd": "Water productivity (constant 2015 US$ GDP per m3 withdrawn)",
    "sp_pop_totl": "Population, total",
}

START_YEAR = 1962
END_YEAR = 2022

# Reference palette (dataviz skill): categorical slots and an ordinal blue ramp.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
ORDINAL = {  # SDG 6.4.2 classes, light -> dark blue
    "No stress": "#86b6ef",
    "Low": "#5598e7",
    "Medium": "#2a78d6",
    "High": "#1c5cab",
    "Critical": "#0d366b",
}


# ---------------------------------------------------------------- download
def fetch(concept: str, offline: bool) -> tuple[Path, str]:
    CACHE.mkdir(exist_ok=True)
    name = f"ddf--datapoints--{concept}--by--geo--time.csv"
    path = CACHE / name
    url = f"{BASE}/datapoints/{name}"
    if not path.exists():
        if offline:
            sys.exit(f"missing {path} and --offline given")
        print(f"downloading {concept} ...")
        with urllib.request.urlopen(url, timeout=120) as resp:
            path.write_bytes(resp.read())
    return path, url


def load(concept: str, offline: bool) -> tuple[pd.DataFrame, dict]:
    path, url = fetch(concept, offline)
    df = pd.read_csv(path)
    df = df.rename(columns={concept: "value"})[["geo", "time", "value"]]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return df, {"url": url, "sha256": digest, "rows": int(len(df))}


# ---------------------------------------------------------------- charts
def style(ax, title: str, subtitle: str | None = None) -> None:
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    pad = 8 + 14 * (subtitle.count("\n") + 1) if subtitle else 8
    ax.set_title(title, loc="left", fontsize=12, color=INK, pad=pad)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9, color=INK2)


def chart_stress(stress: pd.DataFrame, out: Path) -> None:
    d = stress.sort_values("value")
    fig, ax = plt.subplots(figsize=(8, 7.5), facecolor=SURFACE)
    colors = [ORDINAL[c] for c in d["class"]]
    ax.barh(d["name_en"], d["value"], color=colors, height=0.7, edgecolor=SURFACE, linewidth=2)
    ax.set_xscale("log")
    ax.axvline(100, color=INK2, linewidth=1, linestyle="--")
    ax.text(100, len(d) - 0.4, " 100% = all renewable water used", fontsize=8, color=INK2, va="bottom")
    for y, v in enumerate(d["value"]):
        ax.text(v * 1.08, y, f"{v:,.0f}%", va="center", fontsize=8, color=INK)
    style(ax, "Water stress in the 22 Arab countries (SDG 6.4.2)",
          "Freshwater withdrawn as % of renewable freshwater available, latest value, log scale")
    ax.set_xlim(0.5, d["value"].max() * 4)
    handles = [plt.Rectangle((0, 0), 1, 1, color=ORDINAL[k]) for k in ORDINAL]
    ax.legend(handles, list(ORDINAL), title="FAO class", loc="lower right", fontsize=8,
              title_fontsize=8, frameon=False)
    fig.text(0.01, 0.005, "Source: World Bank WDI / FAO AQUASTAT (CC BY 4.0)", fontsize=7, color=INK2)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def chart_per_person(pc: pd.DataFrame, out: Path) -> None:
    picks = ["sau", "egy", "jor", "are", "irq", "mar"]
    fig, ax = plt.subplots(figsize=(8, 5), facecolor=SURFACE)
    for i, geo in enumerate(picks):
        g = pc[pc["geo"] == geo].sort_values("time")
        ax.plot(g["time"], g["value"], color=CAT[i], linewidth=2)
        nudge = {"irq": 1.12, "mar": 0.88}.get(geo, 1.0)
        ax.text(g["time"].iloc[-1] + 0.8, g["value"].iloc[-1] * nudge, water.ARAB_COUNTRIES[geo][0],
                fontsize=8, color=INK, va="center")
    ax.set_yscale("log")
    for level, label in [(1700, "stress"), (1000, "scarcity"), (500, "absolute scarcity")]:
        ax.axhline(level, color=INK2, linewidth=0.8, linestyle="--")
        ax.text(1961, level * 1.05, f"{level:,} m³: {label}", fontsize=7, color=INK2)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    style(ax, "Renewable water per person keeps falling",
          "Renewable INTERNAL freshwater, m³ per person per year (log scale; excludes rivers\n"
          "entering from other countries, e.g. the Nile). The water did not shrink: population grew.")
    ax.grid(axis="x", visible=False)
    ax.set_xlim(1960, END_YEAR + 9)
    ax.legend([plt.Line2D([], [], color=CAT[i], lw=2) for i in range(len(picks))],
              [water.ARAB_COUNTRIES[g][0] for g in picks], fontsize=8, frameon=False,
              loc="upper right", ncol=3)
    fig.text(0.01, 0.005, "Source: World Bank WDI / FAO AQUASTAT (CC BY 4.0)", fontsize=7, color=INK2)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def chart_sectors(sec: pd.DataFrame, out: Path) -> None:
    d = sec.sort_values("agriculture")
    fig, ax = plt.subplots(figsize=(8, 7.5), facecolor=SURFACE)
    left = pd.Series(0.0, index=d.index)
    parts = [("agriculture", "Agriculture", CAT[0]), ("industry", "Industry", CAT[1]),
             ("domestic", "Domestic (homes, cities)", CAT[2])]
    for col, label, color in parts:
        ax.barh(d["name_en"], d[col], left=left, color=color, height=0.7, label=label,
                edgecolor=SURFACE, linewidth=2)
        left = left + d[col].fillna(0)
    style(ax, "Where the water goes", "Share of total freshwater withdrawals by sector, latest value (%)")
    ax.set_xlim(0, 100)
    ax.legend(fontsize=8, frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    fig.text(0.01, 0.005, "Source: World Bank WDI / FAO AQUASTAT (CC BY 4.0)", fontsize=7, color=INK2)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def chart_saudi(sw: pd.DataFrame, renewable: float, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor=SURFACE)
    ax.plot(sw["time"], sw["withdrawals_bn_m3"], color=CAT[0], linewidth=2, marker="o", markersize=3)
    ax.axhline(renewable, color=CAT[1], linewidth=2)
    ax.text(sw["time"].min(), renewable + 0.5,
            f"Renewable internal freshwater: {renewable:.1f} bn m³ / year", fontsize=8, color=INK)
    last = sw.iloc[-1]
    ax.text(last["time"], last["withdrawals_bn_m3"] + 0.6, f"{last['withdrawals_bn_m3']:.1f} bn m³",
            fontsize=8, color=INK, ha="right")
    ax.set_ylim(0, sw["withdrawals_bn_m3"].max() * 1.2)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    style(ax, "Saudi Arabia: water withdrawn vs water that renews",
          "Total freshwater withdrawals, billion m³ per year (incl. desalinated water)")
    ax.grid(axis="x", visible=False)
    ax.legend([plt.Line2D([], [], color=CAT[0], lw=2), plt.Line2D([], [], color=CAT[1], lw=2)],
              ["Withdrawals", "Renewable internal resources"], fontsize=8, frameon=False,
              loc="center right")
    fig.text(0.01, 0.005, "Source: World Bank WDI / FAO AQUASTAT (CC BY 4.0)", fontsize=7, color=INK2)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- main
def names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["name_en"] = df["geo"].map(lambda g: water.ARAB_COUNTRIES[g][0])
    df["name_ar"] = df["geo"].map(lambda g: water.ARAB_COUNTRIES[g][1])
    return df


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--offline", action="store_true", help="use cached files only")
    args = ap.parse_args(argv)

    data, meta_files = {}, {}
    for concept in INDICATORS:
        data[concept], meta_files[concept] = load(concept, args.offline)
    arab = list(water.ARAB_COUNTRIES)
    A = {k: v[v["geo"].isin(arab)] for k, v in data.items()}
    RESULTS.mkdir(exist_ok=True)

    # 1. Water stress, latest value
    stress = water.latest_observation(A["er_h2o_fwst_zs"])
    stress["class"] = stress["value"].map(water.stress_class)
    stress = names(stress).sort_values("value", ascending=False)
    stress.to_csv(RESULTS / "water_stress_latest.csv", index=False, float_format="%.1f")
    stress_counts = water.count_by_class(stress.set_index("geo")["value"], water.stress_class)

    # 2. Renewable water per person: first year with data vs END_YEAR
    pc = A["er_h2o_intr_pc"]
    first = START_YEAR  # countries without data in both years are left out of this table
    ch = water.change_table(pc, first, END_YEAR)
    ch["class_start"] = ch[f"v{first}"].map(water.falkenmark_class)
    ch["class_end"] = ch[f"v{END_YEAR}"].map(water.falkenmark_class)
    ch = names(ch.reset_index()).sort_values(f"v{END_YEAR}")
    ch.to_csv(RESULTS / "water_per_person.csv", index=False, float_format="%.2f")
    abs_start = int((ch["class_start"] == "Absolute scarcity").sum())
    abs_end = int((ch["class_end"] == "Absolute scarcity").sum())
    n_pc = int(len(ch))
    n_fell = int((ch["ratio"] < 1).sum())
    missing_pc = sorted(set(arab) - set(ch["geo"]))
    not_fell = ch[~(ch["ratio"] < 1)]
    not_fell_txt = "; ".join(
        f"{r.name_en}: {getattr(r, f'v{first}'):,.0f} -> {getattr(r, f'v{END_YEAR}'):,.0f} m³" for r in not_fell.itertuples()
    )
    # World reference: median over all countries in the dataset (not population-weighted)
    world_pc = water.value_in_year(data["er_h2o_intr_pc"], END_YEAR)
    world_median = float(world_pc.median())
    world_n = int(world_pc.notna().sum())

    # Consistency check: recompute per-capita from totals / population
    recomputed = water.per_capita(A["er_h2o_intr_k3"], A["sp_pop_totl"])
    chk = recomputed.merge(pc, on=["geo", "time"], suffixes=("_calc", "_pub"))
    rel_err = ((chk["value_calc"] - chk["value_pub"]).abs() / chk["value_pub"]).median()

    # 3. Sector shares
    sec = None
    for concept, col in [("er_h2o_fwag_zs", "agriculture"), ("er_h2o_fwin_zs", "industry"),
                         ("er_h2o_fwdm_zs", "domestic")]:
        lo = water.latest_observation(A[concept])[["geo", "value", "last_changed_year"]]
        lo = lo.rename(columns={"value": col, "last_changed_year": f"{col}_last_changed"})
        sec = lo if sec is None else sec.merge(lo, on="geo", how="outer")
    sec = names(sec).sort_values("agriculture", ascending=False)
    sec["share_sum"] = sec[["agriculture", "industry", "domestic"]].sum(axis=1)
    sec["consistent"] = (sec["share_sum"] - 100).abs() <= 1.5  # source rounding tolerance
    sec.to_csv(RESULTS / "withdrawals_by_sector.csv", index=False, float_format="%.1f")
    bad_sec = sec[~sec["consistent"]]
    sec_ok = sec[sec["consistent"]]
    agri_majority = int((sec_ok["agriculture"] > 50).sum())
    agri_median = float(sec_ok["agriculture"].median())

    # 4. Saudi Arabia
    sw = A["er_h2o_fwtl_k3"]
    sw = sw[sw["geo"] == "sau"].sort_values("time").rename(columns={"value": "withdrawals_bn_m3"})
    sau_ren = water.latest_observation(A["er_h2o_intr_k3"]).set_index("geo").loc["sau"]
    sw = sw[["time", "withdrawals_bn_m3"]].copy()
    sw["renewable_internal_bn_m3"] = sau_ren["value"]
    sw["multiple_of_renewable"] = sw["withdrawals_bn_m3"] / sau_ren["value"]
    sw.to_csv(RESULTS / "saudi_withdrawals.csv", index=False, float_format="%.3f")
    sau_last = water.latest_observation(A["er_h2o_fwtl_k3"]).set_index("geo").loc["sau"]
    sau_first = sw.iloc[0]
    sau_mult = water.multiple_of_renewable(sau_last["value"], sau_ren["value"])
    sau_pc = ch.set_index("geo").loc["sau"]
    sau_stress = stress.set_index("geo").loc["sau"]
    sau_sec = sec.set_index("geo").loc["sau"]

    # 5. Water productivity
    wp = water.latest_observation(A["er_gdp_fwtl_m3_kd"])
    wp = names(wp).sort_values("value", ascending=False)
    wp.to_csv(RESULTS / "water_productivity.csv", index=False, float_format="%.2f")
    wp_world = float(water.value_in_year(data["er_gdp_fwtl_m3_kd"], END_YEAR).median())
    sau_wp = wp.set_index("geo").loc["sau"]

    # Charts
    chart_stress(stress, RESULTS / "water_stress_ranking.png")
    chart_per_person(pc, RESULTS / "water_per_person.png")
    chart_sectors(sec_ok, RESULTS / "withdrawals_by_sector.png")
    chart_saudi(sw, float(sau_ren["value"]), RESULTS / "saudi_withdrawals.png")

    # Findings (all numbers come from the variables above)
    over100 = stress[stress["value"] > 100]
    top3 = stress.head(3)
    stale = stress[stress["last_changed_year"] < stress["latest_year"]]
    lines = [
        "# Findings (generated by build.py)",
        "",
        f"Data: World Bank WDI / FAO AQUASTAT via open-numbers mirror, commit `{COMMIT[:10]}`. "
        f"Water series end in {int(stress['latest_year'].max())}.",
        "",
        f"1. **{len(over100)} of 22 Arab countries withdraw more freshwater than renews each year** "
        f"(SDG 6.4.2 water stress above 100%, FAO class \"Critical\"). Highest: "
        + ", ".join(f"{r.name_en} {r.value:,.0f}%" for r in top3.itertuples()) + ".",
        f"   Class counts: " + ", ".join(f"{k}: {stress_counts.get(k, 0)}" for _, k in water.STRESS_CLASSES) + ".",
        f"2. **Saudi Arabia: water stress {sau_stress['value']:,.0f}%** (last changed in "
        f"{int(sau_stress['last_changed_year'])}). Withdrawals were {sau_last['value']:.1f} bn m³/year vs "
        f"{sau_ren['value']:.1f} bn m³ of renewable internal freshwater, i.e. **{sau_mult:.1f}x** what renews. "
        f"Withdrawals grew from {sau_first['withdrawals_bn_m3']:.1f} bn m³ in {int(sau_first['time'])}.",
        f"3. **Renewable water per person fell in {n_fell} of {n_pc} countries** with data in both {first} and "
        f"{END_YEAR} (left out: {', '.join(water.ARAB_COUNTRIES[g][0] for g in missing_pc)}; did not fall: "
        f"{not_fell_txt or 'none'}). The number of these "
        f"countries below 500 m³ per person (\"absolute scarcity\") went from {abs_start} to {abs_end}. "
        f"Saudi Arabia went from {sau_pc[f'v{first}']:,.0f} to {sau_pc[f'v{END_YEAR}']:,.0f} m³ per person "
        f"({(1 - sau_pc['ratio']) * 100:.0f}% less), because population grew while renewable resources are fixed. "
        f"World reference: median country {world_median:,.0f} m³ per person in {END_YEAR} (n={world_n}).",
        f"4. **Agriculture uses most of the water**: it is over half of withdrawals in {agri_majority} of "
        f"{len(sec_ok)} countries with consistent sector data (median share {agri_median:.0f}%). "
        f"Saudi Arabia: agriculture {sau_sec['agriculture']:.0f}%, industry {sau_sec['industry']:.0f}%, "
        f"domestic {sau_sec['domestic']:.0f}%."
        + (" Left out because the source shares do not add up to 100%: "
           + "; ".join(f"{r.name_en} ({r.share_sum:.1f}%)" for r in bad_sec.itertuples()) + "."
           if len(bad_sec) else ""),
        f"5. **Water productivity** (GDP per m³ withdrawn, constant 2015 US$): Saudi Arabia "
        f"${sau_wp['value']:.1f}/m³ vs ${wp_world:.1f}/m³ for the median country in the world in {END_YEAR}. "
        f"Highest in the Arab group: {wp.iloc[0]['name_en']} ${wp.iloc[0]['value']:,.0f}/m³.",
        "",
        f"Data freshness: for {len(stale)} of 22 countries the latest water-stress number is a value carried "
        f"forward from an earlier estimate (see `last_changed_year` in water_stress_latest.csv).",
        f"Check: per-person water recomputed from totals and population matches the published series "
        f"(median relative difference {rel_err:.2%}).",
    ]
    (RESULTS / "findings.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    meta = {
        "source_repo": f"https://github.com/{REPO}",
        "commit": COMMIT,
        "license": "CC BY 4.0 (World Bank WDI; water series from FAO AQUASTAT)",
        "indicators": {k: {"title": INDICATORS[k], **meta_files[k]} for k in INDICATORS},
        "countries": arab,
        "per_person_years": [first, END_YEAR],
        "per_capita_recompute_median_rel_diff": round(float(rel_err), 6),
    }
    (RESULTS / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print((RESULTS / "findings.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
