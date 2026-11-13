"""Formula tests, plus a check that site/calc.js gives the same numbers as popcalc.py."""
import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

import popcalc as pc

SITE = Path(__file__).resolve().parents[1] / "site"


def test_growth_multiple_and_cagr():
    assert pc.growth_multiple(10, 40) == 4
    # doubling in 10 years is ~7.18% a year
    assert pc.cagr(100, 200, 10) == pytest.approx(2 ** 0.1 - 1)
    assert pc.cagr(100, 100, 5) == 0


def test_doubling_time_known_values():
    assert pc.doubling_time(0.07) == pytest.approx(10.24, abs=0.01)
    assert pc.doubling_time(1.0) == pytest.approx(1.0)
    assert math.isinf(pc.doubling_time(0)) and math.isinf(pc.doubling_time(-0.01))


def test_rule_of_70_is_close_for_small_rates():
    for r in (0.005, 0.01, 0.02, 0.03):
        assert pc.rule_of_70(r) == pytest.approx(pc.doubling_time(r), rel=0.02)


def test_doubling_consistent_with_project():
    r = 0.025
    assert pc.project(1.0, r, pc.doubling_time(r)) == pytest.approx(2.0)


def test_added_per_day():
    assert pc.added_per_day(0, 365.25, 1) == pytest.approx(1.0)
    assert pc.added_per_day(1000, 0, 1) < 0


@pytest.mark.parametrize("bad", [lambda: pc.growth_multiple(0, 5), lambda: pc.cagr(1, 2, 0),
                                 lambda: pc.added_per_day(1, 2, 0)])
def test_invalid_inputs_raise(bad):
    with pytest.raises(ValueError):
        bad()


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_matches_python():
    cases = [(2.4e6, 37e6, 65), (91.5e6, 497.9e6, 65), (6.5e6, 5.85e6, 10), (1, 3, 7)]
    rates = [0.001, 0.0217, 0.0359, 0.1, 0, -0.01]
    script = f"""
      const C = require({json.dumps(str(SITE / 'calc.js'))});
      const cases = {json.dumps(cases)}, rates = {json.dumps(rates)};
      const fin = x => (isFinite(x) ? x : null);
      console.log(JSON.stringify({{
        m: cases.map(c => C.growthMultiple(c[0], c[1])),
        g: cases.map(c => C.cagr(c[0], c[1], c[2])),
        d: cases.map(c => C.addedPerDay(c[0], c[1], c[2])),
        dt: rates.map(r => fin(C.doublingTime(r))),
        r70: rates.map(r => fin(C.ruleOf70(r))),
        p: rates.map(r => C.project(100, r, 30)),
      }}));
    """
    out = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    fin = lambda x: None if math.isinf(x) else x  # noqa: E731
    assert out["m"] == pytest.approx([pc.growth_multiple(a, b) for a, b, _ in cases])
    assert out["g"] == pytest.approx([pc.cagr(a, b, y) for a, b, y in cases])
    assert out["d"] == pytest.approx([pc.added_per_day(a, b, y) for a, b, y in cases])
    assert out["dt"] == pytest.approx([fin(pc.doubling_time(r)) for r in rates])
    assert out["r70"] == pytest.approx([fin(pc.rule_of_70(r)) for r in rates])
    assert out["p"] == pytest.approx([pc.project(100, r, 30) for r in rates])
