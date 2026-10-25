"""CPI forecast 2026-10 to 2028-12: no-reform baseline + 2027 tariff shock.

1. Baseline: ARIMA(1,0,0) with a constant fitted on year-on-year inflation since
   2022 (after the VAT base effects washed out). Back-tested against a naive
   forecast on the last 12 months.
2. Shock: direct effect = CPI weight x average household bill change, for
   electricity and for water; plus a second-round (indirect) effect from the
   higher commercial, industrial and government tariffs.
3. The shock enters year-on-year inflation in January 2027 and drops out in
   January 2028 (base effect), which is what the 2016, 2018 and 2020 episodes show.
4. Monte Carlo over the uncertain inputs gives a distribution for 2027 inflation.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

from . import data
from .household import national_bill_change, simulate_accounts

H_START = pd.Period("2026-10", "M")
H_END = pd.Period("2028-12", "M")
SHOCK_START = pd.Period("2027-01", "M")


def _fit(y: pd.Series):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ARIMA(y.to_timestamp(), order=(1, 0, 0), trend="c").fit()


def baseline(cpi: pd.Series | None = None) -> pd.DataFrame:
    cpi = data.cpi_monthly() if cpi is None else cpi
    y = cpi.loc[pd.Period(data.a("baseline_cpi_window_start"), "M"):]
    res = _fit(y)
    steps = (H_END - y.index[-1]).n
    fc = res.get_forecast(steps)
    idx = pd.period_range(y.index[-1] + 1, periods=steps, freq="M")
    ci80 = fc.conf_int(alpha=0.2).to_numpy()
    ci95 = fc.conf_int(alpha=0.05).to_numpy()
    return pd.DataFrame({"month": idx.astype(str), "baseline": fc.predicted_mean.to_numpy(),
                         "lo80": ci80[:, 0], "hi80": ci80[:, 1],
                         "lo95": ci95[:, 0], "hi95": ci95[:, 1]})


def backtest(cpi: pd.Series | None = None, holdout: int = 12) -> dict:
    """Out-of-sample check: ARIMA vs naive (last value) on the final `holdout` months."""
    cpi = data.cpi_monthly() if cpi is None else cpi
    y = cpi.loc[pd.Period(data.a("baseline_cpi_window_start"), "M"):]
    train, test = y.iloc[:-holdout], y.iloc[-holdout:]
    pred = _fit(train).get_forecast(holdout).predicted_mean.to_numpy()
    naive = np.repeat(train.iloc[-1], holdout)
    return {"holdout_months": holdout, "from": str(test.index[0]), "to": str(test.index[-1]),
            "mae_arima": round(float(np.abs(pred - test.to_numpy()).mean()), 3),
            "mae_naive": round(float(np.abs(naive - test.to_numpy()).mean()), 3)}


def shock_pp(elec_change_pct: float, water_change_pct: float, w_elec: float, w_water: float,
             passthrough: float) -> dict:
    direct_e = w_elec / 100 * elec_change_pct
    direct_w = w_water / 100 * water_change_pct
    direct = direct_e + direct_w
    return {"direct_electricity_pp": direct_e, "direct_water_pp": direct_w,
            "direct_pp": direct, "indirect_pp": direct * passthrough,
            "total_pp": direct * (1 + passthrough)}


def central_shock() -> dict:
    acc = simulate_accounts()
    nb = national_bill_change(acc, elasticity=data.a("price_elasticity_short_run"))
    s = shock_pp(nb["elec_change_pct"], nb["water_change_pct"],
                 data.a("cpi_weight_electricity_pct"), data.a("cpi_weight_water_pct"),
                 data.a("indirect_passthrough_ratio"))
    return {**{k: round(v, 3) for k, v in s.items()},
            "elec_bill_change_pct": round(nb["elec_change_pct"], 1),
            "water_bill_change_pct": round(nb["water_change_pct"], 1)}


def scenario_path(base: pd.DataFrame, total_pp: float) -> np.ndarray:
    months = pd.PeriodIndex(base["month"], freq="M")
    on = (months >= SHOCK_START) & (months < SHOCK_START + 12)
    return base["baseline"].to_numpy() + np.where(on, total_pp, 0.0)


def scenarios(base: pd.DataFrame | None = None) -> pd.DataFrame:
    """Low / central / high paths using the assumption ranges."""
    base = baseline() if base is None else base
    acc = simulate_accounts()
    out = base[["month", "baseline", "lo80", "hi80", "lo95", "hi95"]].copy()
    specs = {
        "low": dict(e="low", w="low", p="low", el="high"),
        "central": dict(e="value", w="value", p="value", el="value"),
        "high": dict(e="high", w="high", p="high", el="low"),
    }
    summary = []
    for name, sp in specs.items():
        nb = national_bill_change(acc, elasticity=data.a("price_elasticity_short_run", sp["el"]))
        s = shock_pp(nb["elec_change_pct"], nb["water_change_pct"],
                     data.a("cpi_weight_electricity_pct", sp["e"]),
                     data.a("cpi_weight_water_pct", sp["w"]),
                     data.a("indirect_passthrough_ratio", sp["p"]))
        out[name] = scenario_path(base, s["total_pp"])
        summary.append({"scenario": name, **{k: round(v, 2) for k, v in s.items()}})
    out.attrs["summary"] = pd.DataFrame(summary)
    return out


def annual_average(paths: pd.DataFrame, col: str, year: int) -> float:
    m = paths["month"].str.startswith(str(year))
    return round(float(paths.loc[m, col].mean()), 2)


def monte_carlo(n: int = 2000, seed: int = 42, base: pd.DataFrame | None = None) -> pd.DataFrame:
    """Distribution of average 2027 inflation under input uncertainty."""
    rng = np.random.default_rng(seed)
    base = baseline() if base is None else base
    m27 = base["month"].str.startswith("2027").to_numpy()
    b27 = base.loc[m27, "baseline"].mean()
    # baseline uncertainty: average of the 80% band half-width converted to sd
    sd27 = ((base.loc[m27, "hi80"] - base.loc[m27, "lo80"]) / (2 * 1.2816)).mean()
    tri = lambda key: rng.triangular(data.a(key, "low"), data.a(key), data.a(key, "high"), n)
    w_e, w_w, pt = tri("cpi_weight_electricity_pct"), tri("cpi_weight_water_pct"), tri("indirect_passthrough_ratio")
    el = rng.triangular(data.a("price_elasticity_short_run", "high"), data.a("price_elasticity_short_run"),
                        data.a("price_elasticity_short_run", "low"), n)
    sig = rng.uniform(data.a("consumption_lognormal_sigma", "low"), data.a("consumption_lognormal_sigma", "high"), n)
    # bill changes are smooth in (elasticity, sigma): precompute on a small grid and interpolate
    eg = np.linspace(el.min(), el.max(), 4)
    sg = np.linspace(sig.min(), sig.max(), 4)
    E = np.zeros((4, 4)); W = np.zeros((4, 4))
    for i, e in enumerate(eg):
        for j, s in enumerate(sg):
            nb = national_bill_change(simulate_accounts(8000, seed=11, sigma=s), elasticity=e)
            E[i, j], W[i, j] = nb["elec_change_pct"], nb["water_change_pct"]
    from scipy.interpolate import RegularGridInterpolator
    fe = RegularGridInterpolator((eg, sg), E)
    fw = RegularGridInterpolator((eg, sg), W)
    pts = np.column_stack([el, sig])
    ec, wc = fe(pts), fw(pts)
    shock = (w_e / 100 * ec + w_w / 100 * wc) * (1 + pt)
    infl = b27 + shock + rng.normal(0, sd27, n)
    return pd.DataFrame({"w_elec": w_e, "w_water": w_w, "passthrough": pt, "elasticity": el,
                         "sigma": sig, "elec_change_pct": ec, "water_change_pct": wc,
                         "shock_pp": shock, "inflation_2027": infl})


def tornado(base_shock: float | None = None) -> pd.DataFrame:
    """One-at-a-time sensitivity of the 2027 shock (pp) to each input."""
    acc = simulate_accounts()
    nb = national_bill_change(acc, elasticity=data.a("price_elasticity_short_run"))
    ref = dict(ec=nb["elec_change_pct"], wc=nb["water_change_pct"],
               we=data.a("cpi_weight_electricity_pct"), ww=data.a("cpi_weight_water_pct"),
               pt=data.a("indirect_passthrough_ratio"))
    f = lambda d: (d["we"] / 100 * d["ec"] + d["ww"] / 100 * d["wc"]) * (1 + d["pt"])
    center = f(ref)
    rows = []
    for key, k, label_en, label_ar in [
        ("cpi_weight_electricity_pct", "we", "CPI weight: electricity", "وزن الكهرباء في السلة"),
        ("cpi_weight_water_pct", "ww", "CPI weight: water", "وزن المياه في السلة"),
        ("indirect_passthrough_ratio", "pt", "Second-round pass-through", "الأثر غير المباشر"),
    ]:
        lo = f({**ref, k: data.a(key, "low")})
        hi = f({**ref, k: data.a(key, "high")})
        rows.append({"input_en": label_en, "input_ar": label_ar, "low": round(lo, 2), "high": round(hi, 2)})
    for e_key, label_en, label_ar in [("low", "Elasticity (weak response)", "المرونة (استجابة ضعيفة)"),
                                       ("high", "Elasticity (strong response)", "المرونة (استجابة قوية)")]:
        nb2 = national_bill_change(acc, elasticity=data.a("price_elasticity_short_run", e_key))
        v = f({**ref, "ec": nb2["elec_change_pct"], "wc": nb2["water_change_pct"]})
        rows.append({"input_en": label_en, "input_ar": label_ar, "low": round(min(v, center), 2),
                     "high": round(max(v, center), 2)})
    out = pd.DataFrame(rows)
    out["center"] = round(center, 2)
    out["swing"] = out["high"] - out["low"]
    return out.sort_values("swing", ascending=False).reset_index(drop=True)
