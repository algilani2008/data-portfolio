const D = window.CPI_DATA;
const G = D.general;
const divs = D.divisions;
const short = (s) => s.replace("والحماية الاجتماعية وسلع متنوعة", "وسلع متنوعة").replace(" والمياه والكهرباء والغاز", " والمرافق");

// ---------------- KPIs & findings ----------------
function renderKpis() {
  const withYoy = D.monthly.filter(m => m.yoy != null);
  const peak = withYoy.reduce((a, b) => (b.yoy > a.yoy ? b : a));
  const low = Math.min(...withYoy.map(m => m.yoy));
  const lowMonths = withYoy.filter(m => m.yoy === low).map(m => monthName(m.m)).join(" و");
  const k = [
    ["التضخم السنوي — Q1 2026", PF.pct(G.yoy), `الرقم العام ${G.cpi[2]}`],
    ["التضخم خلال 2025", PF.pct(G.y2025), "ديسمبر 2025 مقابل ديسمبر 2024"],
    ["أعلى تضخم سنوي", PF.pct(peak.yoy), monthName(peak.m)],
    ["أدنى تضخم سنوي", PF.pct(low), lowMonths],
  ];
  document.getElementById("kpis").innerHTML = k.map(([l, v, d]) =>
    `<div class="card kpi"><p class="l">${l}</p><p class="v">${v}</p><p class="d">${PF.esc(d)}</p></div>`).join("");

  const byContrib = [...divs].sort((a, b) => b.contrib - a.contrib);
  const total = divs.reduce((s, d) => s + d.contrib, 0);
  const top3 = byContrib.slice(0, 3);
  const above = divs.filter(d => d.yoy > G.yoy);
  const fell = divs.filter(d => d.yoy < 0);
  const fastest = [...divs].sort((a, b) => b.yoy - a.yoy)[0];
  const h = byContrib[0];
  document.getElementById("findings").innerHTML = [
    `<b>${PF.esc(h.ar)}</b> هو المحرك الأكبر: ارتفع ${PF.pct(h.yoy)} ووزنه ${h.weight}% من السلة، فساهم بنحو <b>${h.contrib.toFixed(1)} نقطة</b> من التضخم العام البالغ ${PF.pct(G.yoy)}.`,
    `أعلى فئة تضخماً: <b>${PF.esc(fastest.ar)}</b> بارتفاع ${PF.pct(fastest.yoy)}.`,
    `<b>3 فئات فقط تفسّر ${Math.round(top3.reduce((s, d) => s + d.contrib, 0) / total * 100)}% من التضخم:</b> ${top3.map(d => PF.esc(short(d.ar))).join("، ")}.`,
    `<b>${above.length} فئات</b> تضخمها أعلى من العام، ووزنها مجتمعة ${above.reduce((s, d) => s + d.weight, 0).toFixed(1)}% من إنفاق الأسرة.`,
    fell.length ? `فئات انخفضت أسعارها: ${fell.map(d => `${PF.esc(d.ar)} (${PF.pct(d.yoy)})`).join("، ")}.` : "",
  ].filter(Boolean).map(t => `<li>${t}</li>`).join("");
}

function monthName(m) {
  const [y, mo] = m.split("-").map(Number);
  return new Date(y, mo - 1, 1).toLocaleDateString("ar-SA-u-nu-latn-ca-gregory", { month: "long", year: "numeric" });
}

// ---------------- divisions chart & table ----------------
let metric = "yoy";
let divChart;
function renderDivisions() {
  const sorted = [...divs].sort((a, b) => b[metric] - a[metric]);
  const accent = PF.css("--accent"), bad = PF.css("--c2"), good = PF.css("--c3");
  const colors = sorted.map(d => metric === "weight" ? accent : d[metric] < 0 ? good : d[metric] > (metric === "yoy" ? G.yoy : 0.3) ? bad : accent);
  const labels = { yoy: "التغير السنوي %", contrib: "المساهمة (نقطة مئوية)", weight: "الوزن %" };
  document.getElementById("divNote").textContent = metric === "yoy" ? `البرتقالي: أعلى من التضخم العام (${PF.pct(G.yoy)})` : metric === "contrib" ? `المجموع ${divs.reduce((s, d) => s + d.contrib, 0).toFixed(2)} نقطة` : "مجموع الأوزان 100%";
  if (divChart) divChart.destroy();
  divChart = PF.chart(document.getElementById("divChart"), {
    type: "bar",
    data: { labels: sorted.map(d => short(d.ar)), datasets: [{ label: labels[metric], data: sorted.map(d => d[metric]), backgroundColor: colors, borderRadius: 4, maxBarThickness: 26 }] },
    options: {
      indexAxis: "y",
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` ${labels[metric]}: ${c.parsed.x.toFixed(metric === "contrib" ? 2 : 1)}` } } },
      scales: { x: { grid: { color: PF.css("--line") }, ticks: { callback: v => v + (metric === "contrib" ? "" : "%") } }, y: { position: "right", grid: { display: false }, ticks: { autoSkip: false } } },
    },
  });

  document.querySelector("#divTable tbody").innerHTML = [...divs].sort((a, b) => b.contrib - a.contrib).map(d => `
    <tr class="${d.yoy > G.yoy ? "hl" : ""}">
      <td>${PF.esc(d.ar)}</td><td class="n">${d.weight.toFixed(1)}%</td><td class="n">${d.cpi[0].toFixed(1)}</td><td class="n">${d.cpi[2].toFixed(1)}</td>
      <td class="n ${d.qoq < 0 ? "good" : ""}">${PF.pct(d.qoq, 1, true)}</td><td class="n ${d.yoy < 0 ? "good" : d.yoy > G.yoy ? "bad" : ""}">${PF.pct(d.yoy, 1, true)}</td><td class="n">${d.contrib.toFixed(2)}</td>
    </tr>`).join("") + `<tr><td><b>الرقم العام</b></td><td class="n">100%</td><td class="n">${G.cpi[0]}</td><td class="n">${G.cpi[2]}</td><td class="n">${PF.pct(G.qoq, 1, true)}</td><td class="n"><b>${PF.pct(G.yoy, 1, true)}</b></td><td class="n">—</td></tr>`;
}

document.querySelectorAll("#divMetric button").forEach(b => b.addEventListener("click", () => {
  metric = b.dataset.m;
  document.querySelectorAll("#divMetric button").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
  renderDivisions();
}));

// ---------------- monthly trend ----------------
let trendChart;
function renderTrend() {
  if (trendChart) trendChart.destroy();
  const m = D.monthly;
  trendChart = PF.chart(document.getElementById("trendChart"), {
    data: {
      labels: m.map(x => monthName(x.m)),
      datasets: [
        { type: "line", label: "التضخم السنوي %", data: m.map(x => x.yoy), borderColor: PF.css("--accent"), backgroundColor: PF.css("--accent"), tension: .3, pointRadius: 3, yAxisID: "y", spanGaps: true },
        { type: "bar", label: "التغير الشهري %", data: m.map(x => x.mom), backgroundColor: PF.css("--c4"), borderRadius: 3, maxBarThickness: 18, yAxisID: "y2" },
      ],
    },
    options: {
      interaction: { mode: "index", intersect: false },
      scales: {
        y: { position: "right", min: 0, max: 3, title: { display: true, text: "سنوي %" }, grid: { color: PF.css("--line") } },
        y2: { position: "left", min: -0.4, max: 1.2, grid: { display: false }, title: { display: true, text: "شهري %" } },
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 9 } },
      },
    },
  });
}

// ---------------- calculator ----------------
const spend = {};
function distribute() {
  const total = Math.max(0, Number(document.getElementById("totalSpend").value) || 0);
  divs.forEach(d => spend[d.code] = Math.round(total * d.weight / 100));
  renderCalcRows();
}
function renderCalcRows() {
  document.getElementById("calcRows").innerHTML = divs.map(d => `
    <tr><td>${PF.esc(d.ar)}</td>
      <td class="n"><input type="number" min="0" step="50" value="${spend[d.code]}" data-code="${d.code}" aria-label="إنفاق ${PF.esc(d.ar)}"></td>
      <td class="n ${d.yoy < 0 ? "good" : d.yoy > G.yoy ? "bad" : ""}">${PF.pct(d.yoy, 1, true)}</td></tr>`).join("");
  document.querySelectorAll("#calcRows input").forEach(inp => inp.addEventListener("input", () => {
    spend[inp.dataset.code] = Math.max(0, Number(inp.value) || 0);
    document.getElementById("totalSpend").value = Object.values(spend).reduce((s, v) => s + v, 0);
    renderCalcResult();
  }));
  renderCalcResult();
}
function renderCalcResult() {
  const monthTotal = Object.values(spend).reduce((s, v) => s + v, 0);
  const items = divs.map(d => ({ d, extra: spend[d.code] * 12 * d.yoy / 100 }));
  const extra = items.reduce((s, x) => s + x.extra, 0);
  const rate = monthTotal ? extra / (monthTotal * 12) * 100 : 0;
  document.getElementById("extraYear").textContent = PF.fmt(Math.round(extra));
  document.getElementById("extraMonth").textContent = PF.fmt(Math.round(extra / 12));
  document.getElementById("personalRate").textContent = PF.pct(rate, 2);
  const diff = rate - G.yoy;
  document.getElementById("vsGeneral").innerHTML = monthTotal
    ? `${Math.abs(diff) < 0.05 ? "قريب من" : diff > 0 ? `<span class="bad">أعلى بـ ${diff.toFixed(2)} نقطة من</span>` : `<span class="good">أقل بـ ${Math.abs(diff).toFixed(2)} نقطة من</span>`} التضخم العام (${PF.pct(G.yoy)})`
    : "";
  document.getElementById("calcTop").innerHTML = items.filter(x => x.extra > 0).sort((a, b) => b.extra - a.extra).slice(0, 3)
    .map(x => `<li>${PF.esc(x.d.ar)}: <b class="mono">+${PF.fmt(Math.round(x.extra))}</b> ريال/سنة</li>`).join("") || `<li>لا توجد زيادة</li>`;
}
document.getElementById("distribute").addEventListener("click", distribute);
document.getElementById("totalSpend").addEventListener("change", distribute);

// ---------------- boot ----------------
document.addEventListener("DOMContentLoaded", () => {
  renderKpis();
  renderDivisions();
  renderTrend();
  distribute();
  PF.onTheme.push(() => { renderDivisions(); renderTrend(); });
});
