// What-if arithmetic, kept apart from the page so the tests can run it directly.
// Inputs in TWh and g/kWh. Works in a browser (global) and in Node (module.exports).
(function (root) {
  var HOURS_PER_YEAR = 8760;

  /**
   * Replace a share of fossil generation with solar, holding total generation constant.
   * @param {object} c country figures: generation, fossil, lowCarbon, solar (TWh),
   *                   intensity (g CO2e per kWh of all generation)
   * @param {number} sharePct share of fossil generation replaced, 0-100
   * @param {number} capacityFactorPct average output of solar as % of nameplate, >0
   * @param {number} solarIntensity life-cycle g CO2e per kWh of solar
   */
  function solarSwap(c, sharePct, capacityFactorPct, solarIntensity) {
    if (!(c.generation > 0) || !(c.fossil >= 0) || !(capacityFactorPct > 0)) return null;
    var replaced = c.fossil * sharePct / 100;
    // All of the grid's emissions are assigned to fossil plants. This slightly overstates
    // fossil intensity, because low-carbon sources also have small life-cycle emissions.
    var fossilIntensity = c.fossil > 0 ? c.intensity * c.generation / c.fossil : 0;
    var saving = Math.max(fossilIntensity - solarIntensity, 0);
    return {
      replacedTwh: replaced,
      // TWh x 1000 = GWh; divide by the GWh one GW really delivers in a year.
      solarGw: replaced * 1000 / (HOURS_PER_YEAR * capacityFactorPct / 100),
      // TWh x g/kWh = 1e9 kWh x g/kWh = 1e9 g = 0.001 Mt.
      avoidedMt: replaced * saving / 1000,
      lowCarbonShareBefore: c.lowCarbon / c.generation * 100,
      lowCarbonShareAfter: (c.lowCarbon + replaced) / c.generation * 100,
      intensityAfter: c.intensity - replaced * saving / c.generation,
      // null when the country reports no solar at all: "x times zero" has no meaning.
      solarMultiple: c.solar > 0 ? (c.solar + replaced) / c.solar : null
    };
  }

  var api = { solarSwap: solarSwap };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AEECalc = api;
})(this);
