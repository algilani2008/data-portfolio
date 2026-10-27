"""What can be done: household measures and paybacks, solar, and policy options compared."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data
from .household import PROFILES, seasonality, simulate_accounts, _account_elec_year
from .tariffs import BREAKER_CLASSES, electricity_bill_vec, water_bill_vec

SOLAR_SHAPE = np.array([0.80, 0.88, 0.98, 1.05, 1.12, 1.15, 1.13, 1.10, 1.05, 0.95, 0.85, 0.78])
SOLAR_SHAPE = SOLAR_SHAPE / SOLAR_SHAPE.mean()


def _elec_year(kwh_month: float, amps: float, sched: str, saving_frac: float = 0.0,
               solar_kwp: float = 0.0) -> float:
    q = kwh_month * seasonality() * (1 - saving_frac)
    export_credit = 0.0
    if solar_kwp:
        gen = solar_kwp * data.a("solar_yield_kwh_per_kwp_year") / 12 * SOLAR_SHAPE
        self_used = np.minimum(gen * data.a("solar_self_consumption"), q)
        exported = gen - self_used
        q = q - self_used
        export_credit = float(exported.sum()) * data.a("solar_export_sar_per_kwh")
    return float(electricity_bill_vec(q, amps, sched).sum()) - export_credit


def measure_table() -> pd.DataFrame:
    """Annual saving and payback of each measure, per household profile, old vs new tariff."""
    rows = []
    for p in PROFILES:
        amps = BREAKER_CLASSES[p["breaker"]]
        for _, m in data.savings_measures().iterrows():
            if m["target"] == "electricity":
                frac = float(m["end_use_share"]) * float(m["saving_of_end_use"])
                kwp = 5.0 if m["id"] == "solar" else 0.0
                s_old = _elec_year(p["kwh_month"], amps, "2018") - _elec_year(p["kwh_month"], amps, "2018", frac, kwp)
                s_new = _elec_year(p["kwh_month"], amps, "2027") - _elec_year(p["kwh_month"], amps, "2027", frac, kwp)
            else:
                frac = float(m["end_use_share"]) * float(m["saving_of_end_use"])
                m3 = np.array([p["water_m3"]])
                s_old = 12 * float(water_bill_vec(m3, "2016", vat=0.15)[0] - water_bill_vec(m3 * (1 - frac), "2016", vat=0.15)[0])
                s_new = 12 * float(water_bill_vec(m3, "2027")[0] - water_bill_vec(m3 * (1 - frac), "2027")[0])
            cost = float(m["cost_sar"])
            pay = lambda s: round(cost / s, 1) if s > 0 and cost > 0 else (0.0 if cost == 0 else None)
            rows.append({"profile": p["id"], "measure": m["id"], "name_ar": m["name_ar"], "name_en": m["name_en"],
                         "target": m["target"], "cost_sar": cost, "saving_old_year": round(s_old),
                         "saving_new_year": round(s_new), "payback_old_years": pay(s_old),
                         "payback_new_years": pay(s_new), "life_years": int(m["life_years"])})
    return pd.DataFrame(rows)


def best_bundle(profile_id: str = "typical") -> dict:
    """Zero/low-cost bundle (thermostat + LED + standby + aerators + leaks) for one profile."""
    t = measure_table()
    t = t[(t.profile == profile_id) & t.measure.isin(["thermostat", "led", "smart_plugs", "aerators", "leaks"])]
    prof = next(p for p in PROFILES if p["id"] == profile_id)
    from .household import profile_summary
    inc = float(profile_summary().set_index("id").loc[profile_id, "increase_year"])
    s = float(t.saving_new_year.sum())
    return {"profile": profile_id, "bundle_cost": float(t.cost_sar.sum()), "bundle_saving_year": round(s),
            "bill_increase_year": round(inc), "offset_pct": round(100 * s / inc, 0)}


def policy_options() -> pd.DataFrame:
    """Cost and reach of alternative ways to soften the increase (bn SAR a year)."""
    acc = simulate_accounts()
    n = data.a("residential_accounts_million") * 1e6
    old, new = _account_elec_year(acc)
    increase = new - old
    rows = []
    # 1. the announced package
    from .fiscal import support_cost
    sc = support_cost()
    rows.append({"id": "package", "name_ar": "الحزمة المعلنة: 500 ريال للمستحقين", "name_en": "Announced package: 500 SAR to eligible groups",
                 "cost_bn": sc["cost_bn_sar_year"], "households_helped_m": round(data.a("saudi_households_m") * data.a("saudi_hh_with_allowance_share"), 2),
                 "covers_expats": False, "covers_private_sector": False,
                 "note_en": "Cash to individuals; helps beyond the bill increase", "note_ar": "نقد للأفراد يتجاوز زيادة الفاتورة"})
    # 2. lifeline block: first 1,000 kWh at the old 18 halalas
    q = np.concatenate([acc["kwh_month"].to_numpy() * f for f in seasonality()])
    life = np.minimum(q, 1000).sum() / len(acc) * 0.03 * 1.15  # SAR per account per year
    rows.append({"id": "lifeline", "name_ar": "شريحة حماية: أول 1,000 كيلوواط بالسعر القديم", "name_en": "Lifeline block: first 1,000 kWh at the old price",
                 "cost_bn": round(life * n / 1e9, 1), "households_helped_m": round(n / 1e6, 2), "covers_expats": True, "covers_private_sector": True,
                 "note_en": "Helps every account; keeps the price signal above 1,000 kWh", "note_ar": "يشمل كل الحسابات ويُبقي إشارة السعر للاستهلاك الأعلى"})
    # 3. fixed-charge relief for small breakers: 30 instead of 70 SAR
    mix = data.a("breaker_mix")
    small = n * mix["20-99A"]
    rows.append({"id": "small_fixed", "name_ar": "خفض الرسم الثابت للقواطع الصغيرة إلى 30 ريالاً", "name_en": "Cut the small-breaker fixed charge to 30 SAR",
                 "cost_bn": round(small * 40 * 12 * 1.15 / 1e9, 1), "households_helped_m": round(small / 1e6, 2), "covers_expats": True, "covers_private_sector": True,
                 "note_en": "Targets the most regressive part of the reform", "note_ar": "يعالج الجزء الأكثر عبئاً على صغار المستهلكين"})
    # 4. targeted rebate: refund the full increase to the smallest 30% of users
    cut = np.quantile(acc["kwh_month"], 0.3)
    low = acc["kwh_month"].to_numpy() <= cut
    rows.append({"id": "rebate_low", "name_ar": "استرداد كامل الزيادة لأصغر 30% من المستهلكين", "name_en": "Refund the increase to the smallest 30% of users",
                 "cost_bn": round(increase[low].sum() / len(acc) * n / 1e9, 1), "households_helped_m": round(0.3 * n / 1e6, 2),
                 "covers_expats": True, "covers_private_sector": True,
                 "note_en": "Cheapest way to protect low users; needs bill-level targeting", "note_ar": "أرخص طريقة لحماية صغار المستهلكين وتحتاج استهدافاً عبر الفاتورة"})
    # 5. wage-support: HRDF-style subsidy of half the Nitaqat raise for the first year
    from .wages import threshold_impact
    w = threshold_impact(5000, 0.4, 1.0)
    rows.append({"id": "hrdf", "name_ar": "دعم نصف زيادة الأجر عبر صندوق الموارد البشرية (السنة الأولى)", "name_en": "Subsidise half the Nitaqat raise for a year (HRDF-style)",
                 "cost_bn": round(0.5 * w["worker_gain_bn_sar_year"], 1), "households_helped_m": round(w["workers_below"] / 1e6, 2),
                 "covers_expats": False, "covers_private_sector": True,
                 "note_en": "Eases phase 1 for small firms; cost shared with employers", "note_ar": "يخفف المرحلة الأولى على المنشآت الصغيرة"})
    df = pd.DataFrame(rows)
    df["cost_per_household_sar"] = (df["cost_bn"] * 1e9 / (df["households_helped_m"] * 1e6)).round()
    return df
