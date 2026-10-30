const D = window.LABOR_DATA;
const Q = D.quarters;
const last = Q.length - 1;
const qLabel = (q) => { const [y, n] = q.split(" Q"); return `الربع ${["", "الأول", "الثاني", "الثالث", "الرابع"][n]} ${y}`; };
const qShort = (q) => { const [y, n] = q.split(" Q"); return `ر${n} ${y}`; };

// derived per activity
const acts = D.activities.map(a => {
  const saudi = a.total.map((t, i) => t == null ? null : t - a.nonSaudi[i]);
  const rate = a.total.map((t, i) => t ? saudi[i] / t * 100 : null);
  return { ...a, saudi, rate,
    change: rate[last] - rate[0],
    growth: saudi[0] ? (saudi[last] / saudi[0] - 1) * 100 : null,
    saudiUpRateDown: saudi[last] > saudi[0] && rate[last] < rate[0] };
});
const sumAt = (key, i) => acts.reduce((s, a) => s + (a[key][i] || 0), 0);
const total = Q.map((_, i) => sumAt("total", i));
const saudi = Q.map((_, i) => sumAt("saudi", i));
const rate = Q.map((_, i) => saudi[i] / total[i] * 100);
const shortName = (s) => s.replace(" وإصلاح المركبات", "").replace(" والضمان الاجتماعي", "").replace(" والحراجة وصيد الأسماك", "").replace(" واستغلال المحاجر", "").replace(" والعلمية والتقنية", "").replace(" بصفتها صاحبة عمل", "");
const mil = (n) => (n / 1e6).toFixed(2);

// ---------------- KPIs & findings ----------------
function renderKpis() {
  document.getElementById("firstQ").textContent = qLabel(Q[0]);
  document.getElementById("lastQ").textContent = qLabel(Q[last]);
  const ch = rate[last] - rate[0];
  const k = [
    ["إجمالي المشتغلين", PF.fmt(total[last]), qLabel(Q[last])],
    ["السعوديون", PF.fmt(saudi[last]), `<span class="good">+${((saudi[last] / saudi[0] - 1) * 100).toFixed(1)}%</span> منذ ${qShort(Q[0])}`],
    ["نسبة التوطين", PF.pct(rate[last]), `كانت ${PF.pct(rate[0])} في ${qShort(Q[0])}`],
    ["التغير في التوطين", `${ch > 0 ? "+" : ""}${ch.toFixed(1)}`, "نقطة مئوية منذ 2021"],
  ];
  document.getElementById("kpis").innerHTML = k.map(([l, v, d]) =>
    `<div class="card kpi"><p class="l">${l}</p><p class="v">${v}</p><p class="d">${d}</p></div>`).join("");

  const big = acts.filter(a => a.total[last] > 50000 && a.code !== "NotSpecified").sort((a, b) => b.rate[last] - a.rate[last]);
  const nsGrowth = ((total[last] - saudi[last]) / (total[0] - saudi[0]) - 1) * 100;
  const upDown = acts.filter(a => a.saudiUpRateDown && a.total[last] > 50000).sort((a, b) => a.change - b.change);
  document.getElementById("findingsSub").textContent = `${qLabel(Q[last])} مقارنة بـ${qLabel(Q[0])}`;
  document.getElementById("findings").innerHTML = [
    `<b>عدد السعوديين ارتفع ${((saudi[last] / saudi[0] - 1) * 100).toFixed(0)}%، لكن نسبة التوطين انخفضت ${Math.abs(ch).toFixed(1)} نقطة</b>، لأن غير السعوديين نموا أسرع (+${nsGrowth.toFixed(0)}%).`,
    `<b>أعلى الأنشطة توطيناً</b> (بين الأنشطة الكبيرة): ${big.slice(0, 3).map(a => `${PF.esc(shortName(a.ar))} (${PF.pct(a.rate[last])})`).join("، ")}.`,
    `<b>أقلها:</b> ${big.slice(-3).reverse().map(a => `${PF.esc(shortName(a.ar))} (${PF.pct(a.rate[last])})`).join("، ")}.`,
    `<b>في ${acts.filter(a => a.saudiUpRateDown).length} أنشطة زاد عدد السعوديين لكن نسبة التوطين نزلت</b>، أبرزها ${upDown.slice(0, 3).map(a => `${PF.esc(shortName(a.ar))} (${a.change.toFixed(1)} نقطة)`).join("، ")}.`,
  ].map(t => `<li>${t}</li>`).join("");
}

// ---------------- quarterly trend ----------------
let trendChart;
function renderTrend() {
  if (trendChart) trendChart.destroy();
  trendChart = PF.chart(document.getElementById("trendChart"), {
    data: {
      labels: Q.map(qShort),
      datasets: [
        { type: "line", label: "نسبة التوطين %", data: rate, borderColor: PF.css("--c2"), backgroundColor: PF.css("--c2"), yAxisID: "y2", tension: .3, pointRadius: 3 },
        { type: "bar", label: "السعوديون (مليون)", data: saudi.map(v => v / 1e6), backgroundColor: PF.css("--accent"), stack: "s", borderRadius: 2 },
        { type: "bar", label: "غير السعوديين (مليون)", data: total.map((t, i) => (t - saudi[i]) / 1e6), backgroundColor: PF.css("--c1"), stack: "s", borderRadius: 2 },
      ],
    },
    options: {
      interaction: { mode: "index", intersect: false },
      plugins: { tooltip: { callbacks: { label: c => ` ${c.dataset.label}: ${c.dataset.yAxisID === "y2" ? c.parsed.y.toFixed(1) + "%" : c.parsed.y.toFixed(2)}` } } },
      scales: {
        y: { stacked: true, position: "right", title: { display: true, text: "مليون مشتغل" }, grid: { color: PF.css("--line") } },
        y2: { position: "left", min: 15, max: 30, grid: { display: false }, title: { display: true, text: "التوطين %" } },
        x: { stacked: true, grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true } },
      },
    },
  });
}

// ---------------- ranking ----------------
let rankMetric = "rate", rankChart;
function renderRanking() {
  const bigOnly = document.getElementById("bigOnly").checked;
  const list = acts.filter(a => (!bigOnly || a.total[last] > 50000) && a.code !== "NotSpecified" && a[rankMetric === "rate" ? "rate" : rankMetric] != null);
  const val = (a) => rankMetric === "rate" ? a.rate[last] : a[rankMetric];
  list.sort((a, b) => val(b) - val(a));
  const labels = { rate: "نسبة التوطين %", change: "التغير (نقطة مئوية)", growth: "نمو عدد السعوديين %" };
  document.getElementById("rankSub").textContent = `${labels[rankMetric]} — ${qLabel(Q[last])}${rankMetric === "rate" ? "" : " مقارنة بـ" + qLabel(Q[0])}. المتوسط العام ${PF.pct(rate[last])}.`;
  const colors = list.map(a => rankMetric === "rate" ? (a.rate[last] >= rate[last] ? PF.css("--accent") : PF.css("--c1")) : val(a) < 0 ? PF.css("--c2") : PF.css("--accent"));
  if (rankChart) rankChart.destroy();
  rankChart = PF.chart(document.getElementById("rankChart"), {
    type: "bar",
    data: { labels: list.map(a => shortName(a.ar)), datasets: [{ label: labels[rankMetric], data: list.map(val), backgroundColor: colors, borderRadius: 4, maxBarThickness: 24 }] },
    options: {
      indexAxis: "y",
      onClick: (e, els) => { if (els.length) selectActivity(list[els[0].index].id, true); },
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ` ${labels[rankMetric]}: ${c.parsed.x.toFixed(1)}`, afterLabel: c => ` المشتغلون: ${PF.fmt(list[c.dataIndex].total[last])}` } } },
      scales: { x: { grid: { color: PF.css("--line") }, ticks: { callback: v => v + (rankMetric === "change" ? "" : "%") } }, y: { position: "right", grid: { display: false }, ticks: { autoSkip: false } } },
    },
  });
}
document.querySelectorAll("#rankMetric button").forEach(b => b.addEventListener("click", () => {
  rankMetric = b.dataset.m;
  document.querySelectorAll("#rankMetric button").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
  renderRanking();
}));
document.getElementById("bigOnly").addEventListener("change", renderRanking);

// ---------------- activity explorer ----------------
let current = acts.find(a => a.code === "Construction") ? acts.find(a => a.code === "Construction").id : acts[0].id;
let actChart;
function selectActivity(id, scroll) {
  current = Number(id);
  document.getElementById("activitySelect").value = current;
  renderActivity();
  renderTable();
  if (scroll) document.getElementById("explore").scrollIntoView({ behavior: "smooth" });
}
function renderActivity() {
  const a = acts.find(x => x.id === current);
  document.getElementById("actKpis").innerHTML = [
    ["المشتغلون", PF.fmt(a.total[last]), `${(a.total[last] / total[last] * 100).toFixed(1)}% من الإجمالي`],
    ["السعوديون", PF.fmt(a.saudi[last]), a.growth != null ? `<span class="${a.growth >= 0 ? "good" : "bad"}">${a.growth > 0 ? "+" : ""}${a.growth.toFixed(1)}%</span> منذ 2021` : ""],
    ["نسبة التوطين", PF.pct(a.rate[last]), `المتوسط العام ${PF.pct(rate[last])}`],
    ["التغير في التوطين", `${a.change > 0 ? "+" : ""}${a.change.toFixed(1)}`, a.saudiUpRateDown ? `<span class="warn">السعوديون زادوا والنسبة نزلت</span>` : "نقطة مئوية منذ 2021"],
  ].map(([l, v, d]) => `<div class="card kpi" style="background: var(--panel-2)"><p class="l">${l}</p><p class="v" style="font-size: 21px">${v}</p><p class="d">${d}</p></div>`).join("");
  if (actChart) actChart.destroy();
  actChart = PF.chart(document.getElementById("actChart"), {
    data: {
      labels: Q.map(qShort),
      datasets: [
        { type: "line", label: "نسبة التوطين %", data: a.rate, borderColor: PF.css("--c2"), backgroundColor: PF.css("--c2"), yAxisID: "y2", tension: .3, pointRadius: 3 },
        { type: "bar", label: "السعوديون", data: a.saudi, backgroundColor: PF.css("--accent"), stack: "s", borderRadius: 2 },
        { type: "bar", label: "غير السعوديين", data: a.total.map((t, i) => t - a.saudi[i]), backgroundColor: PF.css("--c1"), stack: "s", borderRadius: 2 },
      ],
    },
    options: {
      interaction: { mode: "index", intersect: false },
      plugins: { tooltip: { callbacks: { label: c => ` ${c.dataset.label}: ${c.dataset.yAxisID === "y2" ? c.parsed.y.toFixed(1) + "%" : PF.fmt(c.parsed.y)}` } } },
      scales: {
        y: { stacked: true, position: "right", grid: { color: PF.css("--line") }, ticks: { callback: v => v >= 1e6 ? (v / 1e6) + "M" : v >= 1e3 ? (v / 1e3) + "K" : v } },
        y2: { position: "left", min: 0, max: 100, grid: { display: false }, ticks: { callback: v => v + "%" } },
        x: { stacked: true, grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true } },
      },
    },
  });
}
function renderTable() {
  document.querySelector("#actTable tbody").innerHTML = [...acts].sort((a, b) => b.total[last] - a.total[last]).map(a => `
    <tr class="${a.saudiUpRateDown ? "hl" : ""}" data-id="${a.id}" style="cursor: pointer; ${a.id === current ? "outline: 2px solid var(--accent); outline-offset: -2px" : ""}">
      <td>${PF.esc(a.ar)}</td><td class="n">${PF.fmt(a.total[last])}</td><td class="n">${PF.fmt(a.saudi[last])}</td><td class="n">${PF.pct(a.rate[last])}</td>
      <td class="n ${a.change < 0 ? "bad" : "good"}">${a.change > 0 ? "+" : ""}${a.change.toFixed(1)}</td>
      <td class="n">${a.growth == null ? "—" : (a.growth > 0 ? "+" : "") + a.growth.toFixed(1) + "%"}</td>
    </tr>`).join("") + `<tr><td><b>الإجمالي</b></td><td class="n"><b>${PF.fmt(total[last])}</b></td><td class="n"><b>${PF.fmt(saudi[last])}</b></td><td class="n"><b>${PF.pct(rate[last])}</b></td><td class="n bad">${(rate[last] - rate[0]).toFixed(1)}</td><td class="n">+${((saudi[last] / saudi[0] - 1) * 100).toFixed(1)}%</td></tr>`;
  document.querySelectorAll("#actTable tbody tr[data-id]").forEach(tr => tr.addEventListener("click", () => selectActivity(tr.dataset.id, true)));
}

document.addEventListener("DOMContentLoaded", () => {
  const sel = document.getElementById("activitySelect");
  sel.innerHTML = [...acts].sort((a, b) => a.ar.localeCompare(b.ar, "ar")).map(a => `<option value="${a.id}">${PF.esc(a.ar)}</option>`).join("");
  sel.addEventListener("change", () => selectActivity(sel.value));
  renderKpis();
  renderTrend();
  renderRanking();
  selectActivity(current);
  PF.onTheme.push(() => { renderTrend(); renderRanking(); renderActivity(); });
});
