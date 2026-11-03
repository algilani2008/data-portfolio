"""Runs the site's real what-if code (site/calc.js) in Node and checks it against hand maths."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

CALC = Path(__file__).resolve().parents[1] / "site" / "calc.js"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def swap(country, share, cf, solar_g=48):
    script = (f"const c=require({json.dumps(str(CALC))});"
              f"console.log(JSON.stringify(c.solarSwap({json.dumps(country)},{share},{cf},{solar_g})))")
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


COUNTRY = {"generation": 100.0, "fossil": 80.0, "lowCarbon": 20.0, "solar": 10.0, "intensity": 500.0}


def test_hand_worked_example():
    r = swap(COUNTRY, 25, 20)
    assert r["replacedTwh"] == pytest.approx(20)
    # 20 TWh / (8760 h x 0.20) = 11.416 GW
    assert r["solarGw"] == pytest.approx(11.4155, abs=1e-3)
    # Fossil intensity 500 x 100 / 80 = 625 g/kWh; saving 577; 20 x 577 / 1000 = 11.54 Mt
    assert r["avoidedMt"] == pytest.approx(11.54)
    assert r["lowCarbonShareBefore"] == pytest.approx(20)
    assert r["lowCarbonShareAfter"] == pytest.approx(40)
    assert r["intensityAfter"] == pytest.approx(500 - 11.54e3 / 100 / 1, abs=1e-6)
    assert r["solarMultiple"] == pytest.approx(3)


def test_zero_share_changes_nothing():
    r = swap(COUNTRY, 0, 20)
    assert r["solarGw"] == 0
    assert r["avoidedMt"] == 0
    assert r["lowCarbonShareAfter"] == pytest.approx(r["lowCarbonShareBefore"])
    assert r["intensityAfter"] == pytest.approx(COUNTRY["intensity"])


def test_no_solar_today_has_no_multiple():
    assert swap({**COUNTRY, "solar": 0}, 10, 20)["solarMultiple"] is None


def test_fully_low_carbon_country_saves_nothing():
    clean = {"generation": 10.0, "fossil": 0.0, "lowCarbon": 10.0, "solar": 1.0, "intensity": 30.0}
    r = swap(clean, 50, 20)
    assert r["replacedTwh"] == 0
    assert r["avoidedMt"] == 0


def test_rejects_unusable_input():
    assert swap({**COUNTRY, "generation": 0}, 10, 20) is None
    assert swap(COUNTRY, 10, 0) is None
