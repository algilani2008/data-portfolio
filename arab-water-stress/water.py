"""Pure analysis functions for the Arab water stress analysis.

Everything here works on plain pandas DataFrames in "long" form
(columns: ``geo``, ``time``, ``value``) so it can be tested offline
with tiny hand-made tables. ``build.py`` downloads the real data and
calls these functions.
"""
from __future__ import annotations

import pandas as pd

# The 22 member states of the League of Arab States (ISO 3166-1 alpha-3, lower case,
# as used by the Gapminder / open-numbers mirror of the World Development Indicators).
ARAB_COUNTRIES: dict[str, tuple[str, str]] = {
    "dza": ("Algeria", "الجزائر"),
    "bhr": ("Bahrain", "البحرين"),
    "com": ("Comoros", "جزر القمر"),
    "dji": ("Djibouti", "جيبوتي"),
    "egy": ("Egypt", "مصر"),
    "irq": ("Iraq", "العراق"),
    "jor": ("Jordan", "الأردن"),
    "kwt": ("Kuwait", "الكويت"),
    "lbn": ("Lebanon", "لبنان"),
    "lby": ("Libya", "ليبيا"),
    "mrt": ("Mauritania", "موريتانيا"),
    "mar": ("Morocco", "المغرب"),
    "omn": ("Oman", "عُمان"),
    "pse": ("Palestine", "فلسطين"),
    "qat": ("Qatar", "قطر"),
    "sau": ("Saudi Arabia", "السعودية"),
    "som": ("Somalia", "الصومال"),
    "sdn": ("Sudan", "السودان"),
    "syr": ("Syria", "سوريا"),
    "tun": ("Tunisia", "تونس"),
    "are": ("United Arab Emirates", "الإمارات"),
    "yem": ("Yemen", "اليمن"),
}

GCC = ["sau", "are", "kwt", "qat", "bhr", "omn"]

# SDG indicator 6.4.2 severity classes used by FAO (withdrawal as % of available
# renewable freshwater after environmental flow requirements).
STRESS_CLASSES = [
    (25.0, "No stress"),
    (50.0, "Low"),
    (75.0, "Medium"),
    (100.0, "High"),
    (float("inf"), "Critical"),
]

# Falkenmark water-scarcity thresholds (renewable water, cubic metres per person per year).
FALKENMARK_CLASSES = [
    (500.0, "Absolute scarcity"),
    (1000.0, "Scarcity"),
    (1700.0, "Stress"),
    (float("inf"), "No stress"),
]


def classify(value: float, classes: list[tuple[float, str]]) -> str | None:
    """Return the label of the first class whose upper bound is above ``value``.

    Bounds are exclusive upper limits, so a value exactly on a bound goes to the
    next (worse for stress, better for Falkenmark) class. NaN returns None.
    """
    if value is None or pd.isna(value):
        return None
    for upper, label in classes:
        if value < upper:
            return label
    return classes[-1][1]


def stress_class(pct: float) -> str | None:
    """SDG 6.4.2 class for a water-stress percentage."""
    return classify(pct, STRESS_CLASSES)


def falkenmark_class(m3_per_person: float) -> str | None:
    """Falkenmark class for renewable water per person (m3/year)."""
    return classify(m3_per_person, FALKENMARK_CLASSES)


def latest_observation(series: pd.DataFrame, rel_tol: float = 1e-6) -> pd.DataFrame:
    """Latest value per country plus the year that value was last *changed*.

    Many AQUASTAT series are carried forward unchanged for several years after the
    last real estimate (e.g. a value from 2018 repeated in 2019-2022). Reporting
    only the final year would overstate how recent the information is, so for
    every ``geo`` we return:

    - ``value``: the value in the latest year with data
    - ``latest_year``: that latest year
    - ``last_changed_year``: the first year of the final run of identical values,
      i.e. the most recent year in which the number actually moved.
    """
    rows = []
    for geo, g in series.dropna(subset=["value"]).sort_values("time").groupby("geo"):
        values = g["value"].to_numpy()
        years = g["time"].to_numpy()
        last = values[-1]
        i = len(values) - 1
        while i > 0 and abs(values[i - 1] - last) <= rel_tol * max(abs(last), 1.0):
            i -= 1
        rows.append(
            {
                "geo": geo,
                "value": float(last),
                "latest_year": int(years[-1]),
                "last_changed_year": int(years[i]),
            }
        )
    return pd.DataFrame(rows, columns=["geo", "value", "latest_year", "last_changed_year"])


def value_in_year(series: pd.DataFrame, year: int) -> pd.Series:
    """Values for one year, indexed by geo."""
    s = series[series["time"] == year].set_index("geo")["value"]
    return s


def per_capita(resources_bn_m3: pd.DataFrame, population: pd.DataFrame) -> pd.DataFrame:
    """Recompute renewable water per person (m3) from total resources and population.

    Used as a consistency check against the published per-capita series.
    """
    m = resources_bn_m3.merge(population, on=["geo", "time"], suffixes=("_res", "_pop"))
    m = m[m["value_pop"] > 0]
    m["value"] = m["value_res"] * 1e9 / m["value_pop"]
    return m[["geo", "time", "value"]]


def change_table(series: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    """Start value, end value and the ratio end/start for every geo with both."""
    a = value_in_year(series, start).rename(f"v{start}")
    b = value_in_year(series, end).rename(f"v{end}")
    t = pd.concat([a, b], axis=1).dropna()
    t["ratio"] = t[f"v{end}"] / t[f"v{start}"]
    return t


def count_by_class(values: pd.Series, classifier) -> dict[str, int]:
    """Count how many entries fall in each class label."""
    labels = values.map(classifier).dropna()
    return labels.value_counts().to_dict()


def multiple_of_renewable(withdrawal_bn_m3: float, renewable_bn_m3: float) -> float:
    """How many times the yearly renewable internal resource a country withdraws."""
    if renewable_bn_m3 <= 0:
        raise ValueError("renewable resource must be positive")
    return withdrawal_bn_m3 / renewable_bn_m3
