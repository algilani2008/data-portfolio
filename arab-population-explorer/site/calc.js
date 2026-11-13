// Population growth helpers used by the page. Mirrors popcalc.py (the tests compare them).
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.PopCalc = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function growthMultiple(p0, p1) {
    if (!(p0 > 0)) throw new Error("starting population must be positive");
    return p1 / p0;
  }

  function cagr(p0, p1, years) {
    if (!(years > 0)) throw new Error("years must be positive");
    return Math.pow(growthMultiple(p0, p1), 1 / years) - 1;
  }

  function doublingTime(rate) {
    if (!(rate > 0)) return Infinity;
    return Math.log(2) / Math.log1p(rate);
  }

  function ruleOf70(rate) {
    if (!(rate > 0)) return Infinity;
    return 70 / (rate * 100);
  }

  function addedPerDay(p0, p1, years) {
    if (!(years > 0)) throw new Error("years must be positive");
    return (p1 - p0) / (years * 365.25);
  }

  function project(pNow, rate, years) {
    return pNow * Math.pow(1 + rate, years);
  }

  return { growthMultiple, cagr, doublingTime, ruleOf70, addedPerDay, project };
});
