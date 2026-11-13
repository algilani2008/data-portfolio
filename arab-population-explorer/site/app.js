// Arab Population Explorer: all rendering. Data comes from data.js (window.POP_DATA),
// formulas from calc.js (window.PopCalc). No network calls, no storage beyond the language choice.
(function () {
  "use strict";
  var D = window.POP_DATA, C = window.PopCalc;
  var YEARS = D.years, FIRST = D.meta.first_year, LAST = D.meta.last_year;
  var S = D.series;
  var COUNTRY_CODES = Object.keys(S).filter(function (k) { return S[k].country; });
  var AGG_CODES = ["GCC", "ARB", "WLD"];
  var MAX_SERIES = 6;

  var T = {
    ar: {
      title: "كم كنّا؟", subtitle: "مستكشف سكان الدول العربية الـ22 منذ 1960",
      sinceTitle: "من سنة ميلادك إلى اليوم",
      sinceHint: "اختر بلداً وسنة (مثلاً سنة ميلادك) وشف كيف تغيّر عدد السكان من وقتها.",
      country: "البلد", year: "السنة", compareTitle: "قارن بين الدول",
      compareHint: "اختر حتى 6 دول. «المؤشر» يبدأ كل دولة من 100 عشان تقارن سرعة النمو مهما كان حجمها.",
      mode: "طريقة العرض", modeIndex: "مؤشر (سنة البداية = 100)", modeAbs: "عدد السكان (مليون)",
      from: "من سنة", log: "مقياس لوغاريتمي (كل خط أفقي ضعف اللي تحته)",
      rankTitle: "الترتيب", measure: "المقياس", rankTimes: "كم ضعف كبر من سنة البداية",
      rankRate: "متوسط النمو السنوي %", rankPop: "عدد السكان في آخر سنة",
      dblTitle: "حاسبة التضاعف",
      dblHint: "إذا زاد شيء بنسبة ثابتة كل سنة، متى يصير ضعف؟ تنفع للسكان وللمدخرات وأي نمو.",
      rate: "النمو السنوي %", dblCountries: "لو استمرت كل دولة بنفس سرعة آخر 10 سنوات",
      dblCountriesHint: "توضيح حسابي فقط، مو توقع: معدلات النمو تتغير مع الزمن.",
      aboutTitle: "المصدر والملاحظات",
      footer: "بيانات مفتوحة · بدون تتبع · يعمل بدون إنترنت بعد التحميل",
      then: "في {y}", now: "في {y}", times: "كم ضعف", perDay: "زيادة صافية باليوم",
      avg: "متوسط النمو السنوي", million: "مليون", thousand: "ألف", noData: "ما فيه بيانات لهذي السنة",
      sentenceUp: "في {y0} كان سكان {c} حوالي {p0}، وفي {y1} صاروا {p1}: يعني {m} ضعف. هذا معناه بالمتوسط {d} شخص زيادة كل يوم (مواليد ناقص وفيات زائد الهجرة).",
      sentenceDown: "في {y0} كان سكان {c} حوالي {p0}، وفي {y1} صاروا {p1}: يعني نقصوا بالمتوسط {d} شخص كل يوم.",
      sameYear: "اختر سنة قبل {y} عشان تشوف التغيّر.",
      exact: "يتضاعف بعد (حساب دقيق)", r70: "قاعدة الـ70 (حساب ذهني سريع)", in30: "بعد 30 سنة يصير",
      never: "ما يتضاعف أبداً", years: "سنة", shrinkNote: "النمو سالب أو صفر: العدد ما يتضاعف.",
      thCountry: "البلد", thRate: "نمو آخر 10 سنوات", thDbl: "يتضاعف بعد", thPop: "السكان {y}",
      rankNote: "الأزرق = دول الخليج. الخطوط الرمادية للمقارنة (العالم والعالم العربي). {pse}",
      pseNote: "سلسلة فلسطين في المصدر تبدأ من 1990، فتغيب عن الترتيب إذا اخترت سنة قبلها.",
      langBtn: "English", gcc: "دول الخليج", others: "باقي الدول العربية",
      notes: [
        "المصدر: البنك الدولي، مؤشر إجمالي السكان (SP.POP.TOTL)، بترخيص CC BY 4.0، عبر نسخة مفتوحة على GitHub (datasets/population، ترخيص PDDL). آخر سنة: {last}.",
        "الرقم يشمل كل المقيمين في البلد، مواطنين وغير مواطنين. في دول الخليج جزء كبير من النمو جاء من العمالة الوافدة، فالرقم مو عدد المواطنين.",
        "أرقام السنوات الأخيرة تقديرات وقد يعدّلها البنك الدولي لاحقاً، وبعض القفزات أو الانخفاضات تكون بسبب تعداد سكاني جديد وليس تغيراً حقيقياً في سنة واحدة.",
        "«مجموع دول الخليج» محسوب هنا بجمع الدول الست. «العالم العربي» تجميع البنك الدولي نفسه.",
        "الحاسبة تفترض نمواً ثابتاً، وهذا تبسيط للتوضيح وليس توقعاً."
      ]
    },
    en: {
      title: "How many were we?", subtitle: "Population explorer for the 22 Arab countries since 1960",
      sinceTitle: "From your birth year to today",
      sinceHint: "Pick a country and a year (your birth year, say) and see how the population changed since.",
      country: "Country", year: "Year", compareTitle: "Compare countries",
      compareHint: "Pick up to 6. \"Index\" starts every country at 100 so you compare speed of growth regardless of size.",
      mode: "Show", modeIndex: "Index (start year = 100)", modeAbs: "Population (millions)",
      from: "From year", log: "Log scale (each gridline is double the one below)",
      rankTitle: "Ranking", measure: "Measure", rankTimes: "Times bigger since start year",
      rankRate: "Average yearly growth %", rankPop: "Population in latest year",
      dblTitle: "Doubling calculator",
      dblHint: "If something grows by a fixed percentage every year, when does it double? Works for population, savings, anything.",
      rate: "Yearly growth %", dblCountries: "If each country kept its last-10-year pace",
      dblCountriesHint: "An arithmetic illustration, not a forecast: growth rates change over time.",
      aboutTitle: "Source and notes",
      footer: "Open data · no tracking · works offline once loaded",
      then: "In {y}", now: "In {y}", times: "Times bigger", perDay: "Net added per day",
      avg: "Average yearly growth", million: "million", thousand: "thousand", noData: "No data for this year",
      sentenceUp: "In {y0}, {c} had about {p0} people; in {y1}, {p1}: {m} times as many. That is on average {d} more people every day (births minus deaths plus migration).",
      sentenceDown: "In {y0}, {c} had about {p0} people; in {y1}, {p1}: on average {d} fewer people every day.",
      sameYear: "Pick a year before {y} to see the change.",
      exact: "Doubles in (exact)", r70: "Rule of 70 (quick mental math)", in30: "After 30 years it is",
      never: "Never doubles", years: "years", shrinkNote: "Growth is zero or negative: it never doubles.",
      thCountry: "Country", thRate: "Growth, last 10 years", thDbl: "Doubles in", thPop: "Population {y}",
      rankNote: "Blue = GCC states. Grey rows are references (World, Arab World). {pse}",
      pseNote: "The source's Palestine series starts in 1990, so it is left out when you pick an earlier year.",
      langBtn: "العربية", gcc: "GCC states", others: "Other Arab countries",
      notes: [
        "Source: World Bank, Population, total (SP.POP.TOTL), licensed CC BY 4.0, via the open GitHub mirror datasets/population (PDDL). Latest year: {last}.",
        "Counts every resident, citizens and non-citizens. In the Gulf a large part of the growth came from foreign workers, so this is not the number of citizens.",
        "Recent years are estimates the World Bank may revise; some jumps or dips reflect a new census rather than real change in one year.",
        "\"GCC total\" is computed here as the sum of the six states. \"Arab World\" is the World Bank's own aggregate.",
        "The calculator assumes constant growth, a simplification for illustration, not a forecast."
      ]
    }
  };

  var lang = "ar";
  try { lang = localStorage.getItem("pop-lang") || (navigator.language || "ar").slice(0, 2); } catch (e) { /* storage blocked */ }
  if (lang !== "en") lang = "ar";

  var state = {
    sinceCountry: "SAU", sinceYear: 1990,
    picked: ["SAU", "ARE", "EGY", "WLD"], mode: "index", fromYear: 1960, log: true,
    rankMeasure: "times", rankFrom: 1960, rate: 2
  };

  function $(id) { return document.getElementById(id); }
  function t(key, vars) {
    var s = T[lang][key];
    if (vars) Object.keys(vars).forEach(function (k) { s = s.split("{" + k + "}").join(vars[k]); });
    return s;
  }
  function locale() { return lang === "ar" ? "ar-SA-u-nu-latn" : "en-US"; }
  function fmt(n, digits) {
    return new Intl.NumberFormat(locale(), { maximumFractionDigits: digits || 0, minimumFractionDigits: digits || 0 }).format(n);
  }
  function people(n) {
    if (Math.abs(n) >= 1e6) return fmt(n / 1e6, n >= 1e7 ? 1 : 2) + " " + t("million");
    if (Math.abs(n) >= 1e4) return fmt(n / 1e3, 0) + " " + t("thousand");
    return fmt(n, 0);
  }
  function name(code) { return S[code][lang]; }
  function val(code, year) { var i = year - FIRST; return (i >= 0 && i < YEARS.length) ? S[code].v[i] : null; }
  function el(tag, attrs, text) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (text != null) e.textContent = text;
    return e;
  }
  function sortedCountries() {
    return COUNTRY_CODES.slice().sort(function (a, b) { return name(a).localeCompare(name(b), locale()); });
  }
  function fillSelect(sel, items, selected) {
    sel.innerHTML = "";
    items.forEach(function (it) {
      var o = el("option", { value: it[0] }, it[1]);
      if (String(it[0]) === String(selected)) o.selected = true;
      sel.appendChild(o);
    });
  }
  function yearItems(from, to) { var r = []; for (var y = to; y >= from; y--) r.push([y, String(y)]); return r; }

  // ---------- language ----------
  function applyLang() {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.title = lang === "ar" ? "كم كنّا؟ مستكشف سكان الدول العربية" : "How many were we? Arab population explorer";
    document.querySelectorAll("[data-i18n]").forEach(function (n) { n.textContent = t(n.getAttribute("data-i18n")); });
    $("lang").textContent = t("langBtn");
    var notes = $("notes"); notes.innerHTML = "";
    T[lang].notes.forEach(function (s) { notes.appendChild(el("li", null, s.split("{last}").join(LAST))); });
    var countryItems = sortedCountries().map(function (c) { return [c, name(c)]; })
      .concat(AGG_CODES.map(function (c) { return [c, name(c)]; }));
    fillSelect($("sinceCountry"), countryItems, state.sinceCountry);
    renderAll();
  }

  // ---------- since-year card ----------
  function renderSince() {
    var c = state.sinceCountry;
    var firstYear = FIRST; while (val(c, firstYear) == null && firstYear < LAST) firstYear++;
    if (state.sinceYear < firstYear) state.sinceYear = firstYear;
    fillSelect($("sinceYear"), yearItems(firstYear, LAST), state.sinceYear);
    var y0 = state.sinceYear, p0 = val(c, y0), p1 = val(c, LAST), box = $("sinceStats");
    box.innerHTML = "";
    if (p0 == null) { $("sinceSentence").textContent = t("noData"); return; }
    function stat(k, v) { var d = el("div", { "class": "stat" }); d.appendChild(el("div", { "class": "k" }, k)); d.appendChild(el("div", { "class": "v" }, v)); box.appendChild(d); }
    stat(t("then", { y: y0 }), people(p0));
    stat(t("now", { y: LAST }), people(p1));
    if (y0 === LAST) { $("sinceSentence").textContent = t("sameYear", { y: LAST }); return; }
    var yrs = LAST - y0, m = C.growthMultiple(p0, p1), perDay = C.addedPerDay(p0, p1, yrs);
    stat(t("times"), "×" + fmt(m, m < 10 ? 2 : 1));
    stat(t("avg"), fmt(100 * C.cagr(p0, p1, yrs), 2) + "%");
    stat(t("perDay"), fmt(perDay, 0));
    $("sinceSentence").textContent = t(perDay >= 0 ? "sentenceUp" : "sentenceDown", {
      y0: y0, y1: LAST, c: name(c), p0: people(p0), p1: people(p1), m: fmt(m, m < 10 ? 2 : 1), d: fmt(Math.abs(perDay), 0)
    });
  }

  // ---------- comparison chart ----------
  function renderChips() {
    var box = $("chips"); box.innerHTML = "";
    sortedCountries().concat(AGG_CODES).forEach(function (c) {
      var on = state.picked.indexOf(c) >= 0;
      var b = el("button", { type: "button", "class": "chip" + (S[c].country ? "" : " agg"), "aria-pressed": on ? "true" : "false" }, name(c));
      b.addEventListener("click", function () {
        var i = state.picked.indexOf(c);
        if (i >= 0) { if (state.picked.length > 1) state.picked.splice(i, 1); }
        else { if (state.picked.length >= MAX_SERIES) state.picked.shift(); state.picked.push(c); }
        renderChips(); renderChart();
      });
      box.appendChild(b);
    });
  }

  function niceTicks(lo, hi, log, base) {
    var ticks = [];
    if (log) {
      // Powers of two times `base`, so an index chart reads 100, 200, 400 ...
      var start = base * Math.pow(2, Math.floor(Math.log2(lo / base)));
      for (var v = start; v <= hi * 1.0001; v *= 2) if (v >= lo / 1.0001) ticks.push(v);
      if (ticks.length > 8) ticks = ticks.filter(function (_, i) { return i % 2 === 0; });
      if (ticks.length < 2) ticks = [lo, hi];
      return ticks;
    }
    var span = hi - lo || 1, step = Math.pow(10, Math.floor(Math.log10(span / 5)));
    [1, 2, 2.5, 5, 10].some(function (m) { if (span / (step * m) <= 6) { step *= m; return true; } return false; });
    for (var x = Math.ceil(lo / step) * step; x <= hi + 1e-9; x += step) ticks.push(x);
    return ticks;
  }

  function renderChart() {
    // Draw at the box's real width so labels stay readable on phones.
    var W = Math.round(Math.min(860, Math.max(300, $("chart").clientWidth || 860)));
    var H = W < 560 ? 300 : 380, L = W < 560 ? 44 : 56, R = 12, Tp = 12, B = 30;
    var from = state.fromYear, mode = state.mode, log = state.log;
    var lines = state.picked.map(function (c, i) {
      var pts = [], base = null;
      for (var y = from; y <= LAST; y++) {
        var v = val(c, y); if (v == null) continue;
        if (base == null) base = v;
        pts.push([y, mode === "index" ? 100 * v / base : v / 1e6]);
      }
      return { code: c, pts: pts, color: "var(--s" + (i + 1) + ")" };
    }).filter(function (l) { return l.pts.length > 1; });
    var all = [].concat.apply([], lines.map(function (l) { return l.pts.map(function (p) { return p[1]; }); }));
    var box = $("chart"); box.innerHTML = "";
    if (!all.length) return;
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
    if (!log) lo = Math.min(0, lo);
    var useLog = log && lo > 0;
    var f = useLog ? Math.log : function (x) { return x; };
    var y0 = f(lo), y1 = f(hi); if (y1 === y0) y1 = y0 + 1;
    function X(year) { return L + (W - L - R) * (year - from) / Math.max(1, LAST - from); }
    function Y(v) { return Tp + (H - Tp - B) * (1 - (f(v) - y0) / (y1 - y0)); }
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.setAttribute("direction", "ltr");
    function add(tag, a, txt) { var e = document.createElementNS(ns, tag); Object.keys(a).forEach(function (k) { e.setAttribute(k, a[k]); }); if (txt != null) e.textContent = txt; svg.appendChild(e); return e; }
    niceTicks(lo, hi, useLog, mode === "index" ? 100 : 1).forEach(function (v) {
      add("line", { x1: L, x2: W - R, y1: Y(v), y2: Y(v), "class": "gridline" });
      add("text", { x: L - 6, y: Y(v) + 4, "text-anchor": "end" }, fmt(v, v < 10 && mode === "abs" ? 1 : 0));
    });
    var yrsSpan = LAST - from, narrow = W < 560;
    var step = yrsSpan > 40 ? (narrow ? 20 : 10) : yrsSpan > 15 ? (narrow ? 10 : 5) : yrsSpan > 6 ? (narrow ? 4 : 2) : 1;
    for (var yr = Math.ceil(from / step) * step; yr <= LAST; yr += step) {
      add("text", { x: X(yr), y: H - 8, "text-anchor": "middle" }, String(yr));
    }
    lines.forEach(function (l) {
      var d = l.pts.map(function (p, i) { return (i ? "L" : "M") + X(p[0]).toFixed(1) + "," + Y(p[1]).toFixed(1); }).join("");
      add("path", { d: d, fill: "none", stroke: l.color, "stroke-width": 2.4, "stroke-linejoin": "round" });
      var last = l.pts[l.pts.length - 1];
      add("circle", { cx: X(last[0]), cy: Y(last[1]), r: 3.5, fill: l.color });
    });
    box.appendChild(svg);
    box.setAttribute("aria-label", lines.map(function (l) {
      var p = l.pts[l.pts.length - 1]; return name(l.code) + " " + LAST + ": " + fmt(p[1], 1);
    }).join("; "));
    var lg = $("legend"); lg.innerHTML = "";
    lines.forEach(function (l) {
      var p = l.pts[l.pts.length - 1], s = el("span"), i = el("i"); i.style.background = l.color;
      s.appendChild(i);
      s.appendChild(document.createTextNode(name(l.code) + " · " + fmt(p[1], mode === "abs" ? 1 : 0) + (mode === "abs" ? " " + t("million") : "")));
      lg.appendChild(s);
    });
  }

  // ---------- ranking ----------
  function renderRanking() {
    var from = state.rankFrom, m = state.rankMeasure, yrs = LAST - from;
    var rows = COUNTRY_CODES.concat(["ARB", "WLD"]).map(function (c) {
      var p0 = val(c, from), p1 = val(c, LAST);
      if (p1 == null || (m !== "pop" && (p0 == null || yrs <= 0))) return null;
      var v = m === "pop" ? p1 : m === "times" ? C.growthMultiple(p0, p1) : 100 * C.cagr(p0, p1, yrs);
      return { c: c, v: v };
    }).filter(Boolean);
    if (m === "pop") rows = rows.filter(function (r) { return S[r.c].country; });
    rows.sort(function (a, b) { return b.v - a.v; });
    var max = Math.max.apply(null, rows.map(function (r) { return Math.abs(r.v); })) || 1;
    var ol = $("bars"); ol.innerHTML = "";
    rows.forEach(function (r) {
      var li = el("li", { "class": S[r.c].gcc ? "gcc" : (S[r.c].country ? "" : "ref") });
      li.appendChild(el("span", null, name(r.c)));
      var tr = el("span", { "class": "track" }), fl = el("span", { "class": "fill" });
      fl.style.display = "block"; fl.style.width = Math.max(1, 100 * Math.abs(r.v) / max) + "%";
      tr.appendChild(fl); li.appendChild(tr);
      var txt = m === "pop" ? people(r.v) : m === "times" ? "×" + fmt(r.v, r.v < 10 ? 2 : 1) : fmt(r.v, 2) + "%";
      li.appendChild(el("span", { "class": "num" }, txt));
      ol.appendChild(li);
    });
    $("rankNote").textContent = t("rankNote", { pse: (from < 1990 && m !== "pop") ? t("pseNote") : "" });
  }

  // ---------- doubling calculator ----------
  function renderDoubling() {
    var r = state.rate / 100, box = $("dblStats"); box.innerHTML = "";
    function stat(k, v) { var d = el("div", { "class": "stat" }); d.appendChild(el("div", { "class": "k" }, k)); d.appendChild(el("div", { "class": "v" }, v)); box.appendChild(d); }
    var dt = C.doublingTime(r);
    if (!isFinite(dt)) { stat(t("exact"), t("never")); }
    else {
      stat(t("exact"), fmt(dt, 1) + " " + t("years"));
      stat(t("r70"), fmt(C.ruleOf70(r), 1) + " " + t("years"));
    }
    stat(t("in30"), "×" + fmt(C.project(1, r, 30), 2));
    var table = $("dblTable"); table.innerHTML = "";
    var head = el("tr");
    [["thCountry", ""], ["thPop", "n"], ["thRate", "n"], ["thDbl", "n"]].forEach(function (h) {
      head.appendChild(el("th", { "class": h[1] }, t(h[0], { y: LAST })));
    });
    var thead = el("thead"); thead.appendChild(head); table.appendChild(thead);
    var tb = el("tbody");
    COUNTRY_CODES.concat(["GCC", "WLD"]).map(function (c) {
      return { c: c, r: C.cagr(val(c, LAST - 10), val(c, LAST), 10) };
    }).sort(function (a, b) { return b.r - a.r; }).forEach(function (row) {
      var tr = el("tr"), d = C.doublingTime(row.r);
      tr.appendChild(el("td", null, name(row.c)));
      tr.appendChild(el("td", { "class": "n" }, people(val(row.c, LAST))));
      tr.appendChild(el("td", { "class": "n" }, fmt(100 * row.r, 2) + "%"));
      tr.appendChild(el("td", { "class": "n" }, isFinite(d) ? fmt(d, 0) + " " + t("years") : "—"));
      tb.appendChild(tr);
    });
    table.appendChild(tb);
  }

  function renderAll() { renderSince(); renderChips(); renderChart(); renderRanking(); renderDoubling(); }

  // ---------- wiring ----------
  function init() {
    fillSelect($("fromYear"), yearItems(FIRST, LAST - 5), state.fromYear);
    fillSelect($("rankFrom"), yearItems(FIRST, LAST - 1), state.rankFrom);
    $("lang").addEventListener("click", function () {
      lang = lang === "ar" ? "en" : "ar";
      try { localStorage.setItem("pop-lang", lang); } catch (e) { /* ignore */ }
      applyLang();
    });
    $("sinceCountry").addEventListener("change", function (e) { state.sinceCountry = e.target.value; renderSince(); });
    $("sinceYear").addEventListener("change", function (e) { state.sinceYear = +e.target.value; renderSince(); });
    $("mode").addEventListener("change", function (e) { state.mode = e.target.value; renderChart(); });
    $("fromYear").addEventListener("change", function (e) { state.fromYear = +e.target.value; renderChart(); });
    $("logScale").checked = state.log;
    $("logScale").addEventListener("change", function (e) { state.log = e.target.checked; renderChart(); });
    $("rankMeasure").addEventListener("change", function (e) { state.rankMeasure = e.target.value; renderRanking(); });
    $("rankFrom").addEventListener("change", function (e) { state.rankFrom = +e.target.value; renderRanking(); });
    $("rate").addEventListener("input", function (e) {
      var v = parseFloat(e.target.value); if (!isNaN(v)) { state.rate = Math.max(-10, Math.min(50, v)); renderDoubling(); }
    });
    var lastW = 0;
    window.addEventListener("resize", function () {
      var w = $("chart").clientWidth; if (Math.abs(w - lastW) > 40) { lastW = w; renderChart(); }
    });
    applyLang();
  }
  init();
})();
