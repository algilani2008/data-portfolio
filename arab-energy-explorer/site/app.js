/* Arab Energy Explorer. No libraries, no network calls, no storage: all data is in data.js. */
(function () {
  'use strict';
  var D = window.AEE_DATA, swap = window.AEECalc.solarSwap;
  var WORLD = 'WLD', MAX = 6, SLOTS = 6, SOLAR_G = 48;
  var LAST = D.years.length - 1, END = D.years[LAST], START = D.years[0];

  var METRICS = {
    electricity_generation: { ar: 'إنتاج الكهرباء', en: 'Electricity generation', ua: 'تيراواط ساعة', ue: 'TWh', total: true },
    per_capita_electricity: { ar: 'إنتاج الكهرباء للفرد', en: 'Electricity generation per person', ua: 'ك.و.س للفرد', ue: 'kWh per person' },
    low_carbon_share_elec: { ar: 'حصة الكهرباء منخفضة الكربون', en: 'Low-carbon share of electricity', ua: '%', ue: '%' },
    solar_share_elec: { ar: 'حصة الطاقة الشمسية', en: 'Solar share of electricity', ua: '%', ue: '%' },
    wind_share_elec: { ar: 'حصة طاقة الرياح', en: 'Wind share of electricity', ua: '%', ue: '%' },
    gas_share_elec: { ar: 'حصة الغاز', en: 'Gas share of electricity', ua: '%', ue: '%' },
    oil_share_elec: { ar: 'حصة النفط', en: 'Oil share of electricity', ua: '%', ue: '%' },
    carbon_intensity_elec: { ar: 'كثافة الكربون للكهرباء', en: 'Carbon intensity of electricity', ua: 'غ/ك.و.س', ue: 'g CO₂e/kWh' },
    co2: { ar: 'انبعاثات ثاني أكسيد الكربون', en: 'CO₂ emissions', ua: 'مليون طن', ue: 'Mt', total: true },
    co2_per_capita: { ar: 'انبعاثات الفرد', en: 'CO₂ emissions per person', ua: 'طن للفرد', ue: 't per person' }
  };
  var SOURCES = {
    gas: ['غاز', 'Gas'], oil: ['نفط', 'Oil'], hydro: ['مائية', 'Hydro'], solar: ['شمسية', 'Solar'],
    nuclear: ['نووية', 'Nuclear'], wind: ['رياح', 'Wind'], coal: ['فحم', 'Coal'], other: ['متجددة أخرى', 'Other renewables']
  };

  var T = {
    ar: {
      eyebrow: 'بيانات مفتوحة، بدون تتبع', title: 'مستكشف الطاقة العربي',
      lede: 'قارن كيف تنتج 22 دولة عربية كهرباءها وكم تطلق من الانبعاثات، من سنة 2000 إلى اليوم.',
      other: 'English', hHigh: 'أبرز ما في البيانات', hCompare: 'قارن بين الدول', metric: 'المؤشر',
      addCountry: 'أضف دولة', pick: 'اختر…', showWorld: 'أظهر متوسط العالم', csv: 'تنزيل CSV', share: 'نسخ رابط هذا العرض',
      copied: 'انسخ الرابط من شريط العنوان، صار يحفظ اختياراتك.', copiedOk: 'تم نسخ الرابط.',
      asTable: 'عرض الأرقام في جدول', hRank: 'ترتيب الدول', year: 'السنة', hProfile: 'بطاقة دولة', country: 'الدولة',
      hWhatif: 'ماذا لو؟ بدّل وقوداً بالشمس',
      whatifLede: 'جرّب: لو حلت الطاقة الشمسية محل جزء من كهرباء النفط والغاز والفحم، كم نحتاج من الألواح وكم تنخفض الانبعاثات؟',
      wiShare: 'الجزء المستبدل من الكهرباء الأحفورية', wiCf: 'عامل قدرة الألواح (افتراض)',
      wiNote: 'حساب تقريبي للتوضيح، وليس توقعاً أو خطة. يثبت إجمالي الإنتاج ويتجاهل التخزين ومتى تُنتج الشمس مقارنة بوقت الطلب. عامل القدرة 20% افتراض تقريبي تقدر تغيره، و48 غ/ك.و.س للشمسية هو وسيط دورة الحياة من الهيئة الحكومية الدولية المعنية بتغير المناخ (AR5).',
      hTerms: 'مصطلحات', hAbout: 'المصدر والحدود', world: 'العالم', noData: 'لا توجد بيانات',
      vsWorld: 'العالم', tGen: 'الإنتاج', tPer: 'إنتاج الفرد', tLow: 'منخفضة الكربون', tInt: 'كثافة الكربون',
      oLow: 'حصة منخفضة الكربون بعد التبديل', oGw: 'قدرة شمسية مطلوبة', oMt: 'انبعاثات يمكن تجنبها سنوياً', oMul: 'إنتاج الشمسية مقارنة باليوم',
      gw: 'غيغاواط', mt: 'مليون طن مكافئ', times: 'ضعف', wasP: 'الآن', noSolar: 'لا يوجد إنتاج شمسي مسجل',
      replaced: 'تيراواط ساعة مستبدلة', missing: 'بلا بيانات لهذه السنة: ', intAfter: 'كثافة الكربون بعدها',
      worldHidden: 'متوسط العالم ما يظهر هنا لأن إجمالي العالم أكبر بكثير من أي دولة.',
      maxNote: 'الحد 6 دول في الرسم حتى يبقى مقروءاً.', mixYear: 'مزيج الكهرباء',
      foot: 'البيانات: Our World in Data (رخصة CC BY 4.0). جزء من ملف أعمال عبدالكريم الجيلاني.'
    },
    en: {
      eyebrow: 'Open data, no tracking', title: 'Arab Energy Explorer',
      lede: 'Compare how 22 Arab countries make their electricity and how much CO₂ they emit, from 2000 to the latest data.',
      other: 'العربية', hHigh: 'What the data shows', hCompare: 'Compare countries', metric: 'Metric',
      addCountry: 'Add a country', pick: 'Choose…', showWorld: 'Show world average', csv: 'Download CSV', share: 'Copy link to this view',
      copied: 'Copy the link from the address bar; it now holds your choices.', copiedOk: 'Link copied.',
      asTable: 'Show the numbers as a table', hRank: 'Country ranking', year: 'Year', hProfile: 'Country card', country: 'Country',
      hWhatif: 'What if? Swap a fuel for sunlight',
      whatifLede: 'Try it: if solar replaced part of the electricity from oil, gas and coal, how much would be needed, and how far would emissions fall?',
      wiShare: 'Share of fossil electricity replaced', wiCf: 'Solar capacity factor (assumption)',
      wiNote: 'A rough illustration, not a forecast or a plan. It keeps total generation fixed and ignores storage and the timing of solar output against demand. The 20% capacity factor is a round assumption you can change; 48 g/kWh for solar is the IPCC AR5 life-cycle median.',
      hTerms: 'Terms', hAbout: 'Source and limits', world: 'World', noData: 'No data',
      vsWorld: 'World', tGen: 'Generation', tPer: 'Per person', tLow: 'Low-carbon', tInt: 'Carbon intensity',
      oLow: 'Low-carbon share after the swap', oGw: 'Solar capacity needed', oMt: 'Emissions avoided per year', oMul: 'Solar output against today',
      gw: 'GW', mt: 'Mt CO₂e', times: 'times', wasP: 'now', noSolar: 'No solar output on record',
      replaced: 'TWh replaced', missing: 'No data for this year: ', intAfter: 'Carbon intensity after',
      worldHidden: 'The world is left out here because its total dwarfs any single country.',
      maxNote: 'Limited to 6 countries so the chart stays readable.', mixYear: 'Electricity mix',
      foot: 'Data: Our World in Data (CC BY 4.0). Part of Abdulkarim Algilani\'s data portfolio.'
    }
  };
  var TERMS = {
    ar: [['تيراواط ساعة (TWh)', 'وحدة لكمية الكهرباء. تيراواط ساعة واحد يساوي مليار كيلوواط ساعة، والكيلوواط ساعة (ك.و.س) هو الوحدة اللي تشوفها في فاتورة بيتك.'],
      ['كهرباء منخفضة الكربون', 'الكهرباء من الشمس والرياح والماء والطاقة النووية والمتجددة الأخرى، يعني كل شيء غير النفط والغاز والفحم.'],
      ['كثافة الكربون', 'كم غرام من الغازات الدفيئة يصاحب إنتاج كل كيلوواط ساعة، محسوبة على دورة حياة المحطة. كلما قل الرقم كانت الكهرباء أنظف.'],
      ['عامل القدرة', 'نسبة ما تنتجه المحطة فعلياً من أقصى ما تقدر عليه. الألواح لا تنتج في الليل، فمحطة 1 غيغاواط بعامل 20% تنتج كأنها 0.2 غيغاواط طول السنة.']],
    en: [['Terawatt-hour (TWh)', 'A unit for an amount of electricity. One TWh is a billion kilowatt-hours; the kilowatt-hour (kWh) is the unit on a home bill.'],
      ['Low-carbon electricity', 'Electricity from solar, wind, hydro, nuclear and other renewables: everything except oil, gas and coal.'],
      ['Carbon intensity', 'Grams of greenhouse gases that go with each kWh generated, on a life-cycle basis. Lower is cleaner.'],
      ['Capacity factor', 'What a plant really delivers as a share of its maximum. Panels make nothing at night, so a 1 GW plant at 20% delivers like 0.2 GW running all year.']]
  };
  var NOTES = {
    ar: [
      'المصدر: <a href="https://github.com/owid/energy-data">Our World in Data، بيانات الطاقة</a> و<a href="https://github.com/owid/co2-data">بيانات ثاني أكسيد الكربون</a>، برخصة CC BY 4.0، وهي تجمع أرقاماً من Ember ومعهد الطاقة ومشروع الكربون العالمي.',
      'تتوقف البيانات عند ' + END + '، آخر سنة تغطي معظم الدول. الأرقام الناقصة تظهر فارغة، وما فيه أي تعبئة أو تقدير من هذا الموقع.',
      'أرقام الدول الصغيرة والدول اللي تأثرت بالنزاعات تعتمد غالباً على تقديرات مدورة، فتغير صغير فيها يبان كبير في النسبة. تعامل معها كاتجاه عام.',
      'نصيب الفرد هنا هو الإنتاج مقسوماً على السكان، ويشمل الصناعة وتحلية المياه، فهو ليس استهلاك البيوت. وهو لا يشمل المولدات الخاصة غير المسجلة.',
      'الانبعاثات هي انبعاثات الوقود الأحفوري والصناعة داخل حدود الدولة، ولا تشمل ما تحرقه دول أخرى من النفط والغاز المصدّرين.'],
    en: [
      'Source: <a href="https://github.com/owid/energy-data">Our World in Data energy</a> and <a href="https://github.com/owid/co2-data">CO₂</a> datasets, CC BY 4.0, which compile Ember, the Energy Institute and the Global Carbon Project.',
      'Data stops at ' + END + ', the latest year covering most countries. Missing values stay blank; this site fills in or estimates nothing.',
      'Figures for small and conflict-affected countries often rest on rounded estimates, so small changes look large in percentages. Read them as a general direction.',
      'Per-person figures are generation divided by population. They include industry and desalination, so they are not household use, and they miss unrecorded private generators.',
      'Emissions cover fossil fuels and industry inside national borders. They exclude oil and gas burned elsewhere after export.']
  };

  var state = { lang: 'ar', metric: 'low_carbon_share_elec', list: ['SAU', 'ARE', 'EGY', 'MAR'], world: true, year: END, profile: 'SAU', wi: 'SAU' };
  var slot = {};
  var $ = function (id) { return document.getElementById(id); };
  var byCode = {};
  D.countries.forEach(function (c) { byCode[c.code] = c; });

  function t(k) { return T[state.lang][k]; }
  function nameOf(code) { return code === WORLD ? t('world') : byCode[code][state.lang]; }
  function unit(m) { return state.lang === 'ar' ? METRICS[m].ua : METRICS[m].ue; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function num(v) {
    if (v === null || v === undefined) return '–';
    var a = Math.abs(v), d = a >= 100 ? 0 : a >= 10 ? 1 : a >= 1 ? 1 : 2;
    return v.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: d });
  }
  function pct(v) {
    if (v === null || v === undefined) return '–';
    return v.toFixed(v < 1 && v > 0 ? 2 : 1) + '%';
  }
  function withUnit(v, m) { return METRICS[m].ua === '%' ? pct(v) : num(v); }
  function val(code, m, i) { return D.values[code][m][i]; }

  /* ---- URL state ---- */
  function readHash() {
    var p = new URLSearchParams(location.hash.slice(1));
    if (p.get('l') === 'en' || p.get('l') === 'ar') state.lang = p.get('l');
    if (METRICS[p.get('m')]) state.metric = p.get('m');
    if (p.has('c')) state.list = p.get('c').split(',').filter(function (c) { return byCode[c]; }).slice(0, MAX);
    if (p.has('w')) state.world = p.get('w') !== '0';
    var y = +p.get('y');
    if (y >= START && y <= END) state.year = y;
    if (byCode[p.get('p')]) state.profile = p.get('p');
  }
  function writeHash() {
    var p = new URLSearchParams({ l: state.lang, m: state.metric, c: state.list.join(','), w: state.world ? '1' : '0', y: state.year, p: state.profile });
    history.replaceState(null, '', '#' + p.toString());
  }

  /* ---- Static text ---- */
  function applyLang() {
    var root = document.documentElement;
    root.lang = state.lang;
    root.dir = state.lang === 'ar' ? 'rtl' : 'ltr';
    document.title = t('title') + ' | ' + (state.lang === 'ar' ? 'Arab Energy Explorer' : 'مستكشف الطاقة العربي');
    document.querySelectorAll('[data-t]').forEach(function (el) { el.textContent = t(el.getAttribute('data-t')); });
    $('lang').textContent = t('other');
    $('lang').lang = state.lang === 'ar' ? 'en' : 'ar';
    $('highlights').innerHTML = D.highlights.map(function (h) { return '<li>' + esc(h[state.lang]) + '</li>'; }).join('');
    $('terms').innerHTML = TERMS[state.lang].map(function (x) { return '<dt>' + esc(x[0]) + '</dt><dd>' + esc(x[1]) + '</dd>'; }).join('');
    $('notes').innerHTML = NOTES[state.lang].map(function (n) { return '<li>' + n + '</li>'; }).join('');
    $('foot').textContent = t('foot');

    var sorted = D.countries.slice().sort(function (a, b) { return a[state.lang].localeCompare(b[state.lang], state.lang); });
    var opts = sorted.map(function (c) { return '<option value="' + c.code + '">' + esc(c[state.lang]) + '</option>'; }).join('');
    $('profile').innerHTML = opts; $('profile').value = state.profile;
    $('wi-country').innerHTML = opts; $('wi-country').value = state.wi;
    $('metric').innerHTML = Object.keys(METRICS).map(function (m) {
      return '<option value="' + m + '">' + esc(METRICS[m][state.lang]) + '</option>';
    }).join('');
    $('metric').value = state.metric;
  }

  function renderAdd() {
    var left = D.countries.filter(function (c) { return state.list.indexOf(c.code) < 0; })
      .sort(function (a, b) { return a[state.lang].localeCompare(b[state.lang], state.lang); });
    $('add').innerHTML = '<option value="">' + t('pick') + '</option>' + left.map(function (c) {
      return '<option value="' + c.code + '">' + esc(c[state.lang]) + '</option>';
    }).join('');
    $('add').disabled = state.list.length >= MAX;
  }

  /* Colour follows the country: a country keeps its slot until it is removed. */
  function assignSlots() {
    Object.keys(slot).forEach(function (c) { if (state.list.indexOf(c) < 0) delete slot[c]; });
    state.list.forEach(function (c) {
      if (slot[c]) return;
      for (var i = 1; i <= SLOTS; i++) {
        var used = Object.keys(slot).some(function (k) { return slot[k] === i; });
        if (!used) { slot[c] = i; return; }
      }
    });
  }
  function colour(code) { return code === WORLD ? 'var(--world)' : 'var(--s' + slot[code] + ')'; }

  function renderChips() {
    $('chips').innerHTML = state.list.map(function (c) {
      return '<li><button type="button" data-c="' + c + '" aria-label="' + esc(nameOf(c)) + ' ×"><span class="swatch" style="background:' + colour(c) + '"></span>' + esc(nameOf(c)) + ' <span class="x" aria-hidden="true">×</span></button></li>';
    }).join('');
    var notes = [];
    if (state.list.length >= MAX) notes.push(t('maxNote'));
    if (METRICS[state.metric].total && state.world) notes.push(t('worldHidden'));
    $('metric-note').textContent = notes.join(' ');
  }

  /* ---- Line chart ---- */
  function shown() { return state.world ? state.list.concat(WORLD) : state.list; }
  function niceMax(v) {
    if (!(v > 0)) return 1;
    var p = Math.pow(10, Math.floor(Math.log10(v))), f = v / p;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
  }
  function renderChart() {
    var box = $('chart'), W = Math.max(box.clientWidth, 280), narrow = W < 560;
    var m = state.metric, codes = shown(), H = narrow ? 280 : 340;
    // A world total would flatten every country line, so totals show countries only.
    var hideWorld = METRICS[m].total;
    var plotted = hideWorld ? codes.filter(function (c) { return c !== WORLD; }) : codes;
    var labels = plotted.length <= 5 && !narrow;
    var L = 46, R = labels ? 104 : 20, TOP = 12, B = 26, pw = W - L - R, ph = H - TOP - B;
    var max = 0;
    plotted.forEach(function (c) { D.values[c][m].forEach(function (v) { if (v > max) max = v; }); });
    max = niceMax(max);
    var x = function (i) { return L + pw * i / LAST; };
    var y = function (v) { return TOP + ph * (1 - v / max); };
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(METRICS[m][state.lang]) + '">';
    for (var g = 0; g <= 4; g++) {
      var gv = max * g / 4;
      s += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y(gv) + '" y2="' + y(gv) + '" stroke="var(--grid)"/>';
      s += '<text x="' + (L - 6) + '" y="' + (y(gv) + 4) + '" text-anchor="end">' + num(gv) + '</text>';
    }
    var step = narrow ? 8 : 4;
    for (var i = 0; i <= LAST; i++) {
      if ((D.years[i] - START) % step === 0) s += '<text x="' + x(i) + '" y="' + (H - 6) + '" text-anchor="middle">' + D.years[i] + '</text>';
    }
    var ends = [];
    plotted.forEach(function (c) {
      var d = '', pen = false, last = -1;
      D.values[c][m].forEach(function (v, i) {
        if (v === null) { pen = false; return; }
        d += (pen ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(v).toFixed(1); pen = true; last = i;
      });
      s += '<path d="' + d + '" fill="none" stroke="' + colour(c) + '" stroke-width="2" stroke-linejoin="round"' + (c === WORLD ? ' stroke-dasharray="5 4"' : '') + '/>';
      if (last >= 0) {
        var ly = y(D.values[c][m][last]);
        s += '<circle cx="' + x(last) + '" cy="' + ly + '" r="4" fill="' + colour(c) + '" stroke="var(--bg)" stroke-width="2"/>';
        ends.push({ c: c, x: x(last), y: ly });
      }
    });
    if (labels) {
      ends.sort(function (a, b) { return a.y - b.y; });
      ends.forEach(function (e, i) { if (i && e.y - ends[i - 1].y < 15) e.y = ends[i - 1].y + 15; });
      ends.forEach(function (e) { s += '<text class="end" x="' + (e.x + 9) + '" y="' + (e.y + 4) + '" direction="' + (state.lang === 'ar' ? 'rtl' : 'ltr') + '" text-anchor="' + (state.lang === 'ar' ? 'end' : 'start') + '">' + esc(nameOf(e.c)) + '</text>'; });
    }
    s += '<line id="cross" y1="' + TOP + '" y2="' + (TOP + ph) + '" stroke="var(--ink-3)" visibility="hidden"/>';
    s += '<rect id="hit" x="' + L + '" y="' + TOP + '" width="' + pw + '" height="' + ph + '" fill="transparent"/></svg>';
    var tip = $('tip');
    box.innerHTML = '';
    box.insertAdjacentHTML('afterbegin', s);
    box.appendChild(tip);
    bindHover(box, x, plotted, m, L, pw, W);

    $('legend').innerHTML = plotted.map(function (c) {
      var sw = c === WORLD ? '<span class="swatch dash"></span>' : '<span class="swatch" style="background:' + colour(c) + '"></span>';
      return '<li>' + sw + esc(nameOf(c)) + '</li>';
    }).join('') + '<li>' + esc(unit(m)) + '</li>';
    renderTable(plotted, m);
  }
  function bindHover(box, x, codes, m, L, pw, W) {
    var hit = box.querySelector('#hit'), cross = box.querySelector('#cross'), tip = $('tip');
    function move(e) {
      var r = box.getBoundingClientRect(), scale = W / r.width;
      var px = (e.clientX - r.left) * scale;
      var i = Math.max(0, Math.min(LAST, Math.round((px - L) / pw * LAST)));
      cross.setAttribute('x1', x(i)); cross.setAttribute('x2', x(i)); cross.setAttribute('visibility', 'visible');
      var rows = codes.map(function (c) { return { c: c, v: val(c, m, i) }; })
        .sort(function (a, b) { return (b.v === null ? -1 : b.v) - (a.v === null ? -1 : a.v); });
      tip.innerHTML = '<b>' + D.years[i] + '</b>' + rows.map(function (o) {
        return '<div><span><span class="swatch" style="background:' + colour(o.c) + '"></span>' + esc(nameOf(o.c)) + '</span><span class="v">' + withUnit(o.v, m) + '</span></div>';
      }).join('');
      tip.dir = state.lang === 'ar' ? 'rtl' : 'ltr';
      tip.hidden = false;
      var left = x(i) / scale, tw = tip.offsetWidth;
      tip.style.left = (left + 12 + tw > r.width ? Math.max(0, left - tw - 12) : left + 12) + 'px';
    }
    function hide() { tip.hidden = true; cross.setAttribute('visibility', 'hidden'); }
    hit.addEventListener('pointermove', move);
    hit.addEventListener('pointerdown', move);
    hit.addEventListener('pointerleave', hide);
  }
  function renderTable(codes, m) {
    var head = '<thead><tr><th>' + t('year') + '</th>' + codes.map(function (c) { return '<th>' + esc(nameOf(c)) + '</th>'; }).join('') + '</tr></thead>';
    var body = D.years.map(function (yr, i) {
      return '<tr><td>' + yr + '</td>' + codes.map(function (c) { return '<td>' + num(val(c, m, i)) + '</td>'; }).join('') + '</tr>';
    }).reverse().join('');
    $('table').innerHTML = head + '<tbody>' + body + '</tbody>';
  }
  function downloadCsv() {
    var m = state.metric, codes = shown();
    var rows = [['year'].concat(codes.map(function (c) { return c === WORLD ? 'World' : byCode[c].en; })).join(',')];
    D.years.forEach(function (yr, i) {
      rows.push([yr].concat(codes.map(function (c) { var v = val(c, m, i); return v === null ? '' : v; })).join(','));
    });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([rows.join('\n') + '\n'], { type: 'text/csv' }));
    a.download = 'arab-energy-' + m + '.csv';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  /* ---- Ranking ---- */
  function renderRank() {
    var m = state.metric, i = D.years.indexOf(state.year);
    $('rank-year').textContent = state.year;
    var pool = D.countries.map(function (c) { return c.code; });
    if (!METRICS[m].total) pool.push(WORLD);
    var has = pool.filter(function (c) { return val(c, m, i) !== null; });
    var none = pool.filter(function (c) { return val(c, m, i) === null; });
    has.sort(function (a, b) { return val(b, m, i) - val(a, m, i); });
    var top = has.length ? val(has[0], m, i) : 1;
    $('rank-title').textContent = METRICS[m][state.lang] + ' (' + unit(m) + ')';
    $('rank').innerHTML = has.map(function (c) {
      var v = val(c, m, i), w = top > 0 ? v / top * 100 : 0;
      return '<li class="' + (c === WORLD ? 'w' : '') + '"><span class="name">' + esc(nameOf(c)) + '</span><span class="track"><span class="bar" style="width:' + w.toFixed(1) + '%"></span></span><span class="val">' + withUnit(v, m) + '</span></li>';
    }).join('');
    $('rank-missing').textContent = none.length ? t('missing') + none.map(nameOf).join(state.lang === 'ar' ? '، ' : ', ') : '';
  }

  /* ---- Country card ---- */
  function tile(k, n, u, s) {
    return '<div class="tile"><div class="k">' + esc(k) + '</div><div class="n">' + n + ' <span class="u">' + esc(u) + '</span></div>' + (s ? '<div class="s">' + s + '</div>' : '') + '</div>';
  }
  function latestIndex(code, i) {
    for (; i >= 0; i--) if (val(code, 'electricity_generation', i) !== null) return i;
    return -1;
  }
  function mixRow(code, i) {
    var gen = val(code, 'electricity_generation', i);
    var segs = D.sources.map(function (s, n) {
      var v = D.values[code].mix[s][i] || 0, p = gen ? v / gen * 100 : 0;
      return p > 0 ? '<i style="flex:' + p.toFixed(2) + ' 1 0;background:var(--s' + (n + 1) + ')" title="' + esc(SOURCES[s][state.lang === 'ar' ? 0 : 1]) + ' ' + pct(p) + '"></i>' : '';
    }).join('');
    return '<div class="mixrow"><span>' + esc(nameOf(code)) + '</span><div class="mixbar" role="img" aria-label="' + esc(t('mixYear') + ': ' + nameOf(code)) + '">' + segs + '</div></div>';
  }
  function renderProfile() {
    var c = state.profile, i = latestIndex(c, D.years.indexOf(state.year));
    if (i < 0) { $('tiles').innerHTML = ''; $('mix').innerHTML = ''; $('mix-legend').innerHTML = ''; $('profile-text').textContent = t('noData'); return; }
    var wy = latestIndex(WORLD, i), gen = val(c, 'electricity_generation', i);
    var top = D.sources.map(function (s) { return { s: s, p: (D.values[c].mix[s][i] || 0) / gen * 100 }; })
      .sort(function (a, b) { return b.p - a.p; }).filter(function (o) { return o.p >= 0.5; }).slice(0, 3);
    var parts = top.map(function (o) { return SOURCES[o.s][state.lang === 'ar' ? 0 : 1] + ' ' + pct(o.p); });
    $('profile-text').textContent = state.lang === 'ar'
      ? nameOf(c) + ' في ' + D.years[i] + ': ' + parts.join('، ')
      : nameOf(c) + ' in ' + D.years[i] + ': ' + parts.join(', ');
    var cmp = function (m) { return t('vsWorld') + ': ' + withUnit(val(WORLD, m, wy), m); };
    var pair = [['tGen', 'electricity_generation'], ['tPer', 'per_capita_electricity'], ['tLow', 'low_carbon_share_elec'], ['tInt', 'carbon_intensity_elec']];
    $('tiles').innerHTML = pair.map(function (p) {
      var m = p[1], u = METRICS[m].ua === '%' ? '' : unit(m);
      return tile(t(p[0]), withUnit(val(c, m, i), m), u, METRICS[m].total ? '' : cmp(m));
    }).join('');
    $('mix').innerHTML = mixRow(c, i) + mixRow(WORLD, wy);
    $('mix-legend').innerHTML = D.sources.map(function (s, n) {
      var p = (D.values[c].mix[s][i] || 0) / gen * 100;
      return '<li><span class="swatch" style="background:var(--s' + (n + 1) + ')"></span>' + esc(SOURCES[s][state.lang === 'ar' ? 0 : 1]) + ' ' + pct(p) + '</li>';
    }).join('');
  }

  /* ---- What-if ---- */
  function renderWhatif() {
    var c = state.wi, i = latestIndex(c, LAST);
    var share = +$('wi-share').value, cf = +$('wi-cf').value;
    $('wi-share-v').textContent = share + '%'; $('wi-cf-v').textContent = cf + '%';
    var input = {
      generation: val(c, 'electricity_generation', i), fossil: val(c, 'fossil_electricity', i),
      lowCarbon: val(c, 'low_carbon_electricity', i), solar: D.values[c].mix.solar[i] || 0,
      intensity: val(c, 'carbon_intensity_elec', i)
    };
    var r = i >= 0 ? swap(input, share, cf, SOLAR_G) : null;
    if (!r) { $('wi-out').innerHTML = '<p>' + t('noData') + '</p>'; return; }
    $('wi-out').innerHTML =
      tile(t('oLow'), pct(r.lowCarbonShareAfter), '', t('wasP') + ': ' + pct(r.lowCarbonShareBefore) + ' (' + D.years[i] + ')') +
      tile(t('oGw'), num(r.solarGw), t('gw'), num(r.replacedTwh) + ' ' + t('replaced')) +
      tile(t('oMt'), num(r.avoidedMt), t('mt'), t('intAfter') + ': ' + num(r.intensityAfter) + ' ' + unit('carbon_intensity_elec')) +
      tile(t('oMul'), r.solarMultiple === null ? '–' : num(r.solarMultiple), r.solarMultiple === null ? '' : t('times'), r.solarMultiple === null ? t('noSolar') : '');
  }

  function renderDynamic() {
    assignSlots(); renderAdd(); renderChips(); renderChart(); renderRank(); renderProfile(); renderWhatif(); writeHash();
  }
  function renderAll() { applyLang(); $('world').checked = state.world; renderDynamic(); }

  /* ---- Events ---- */
  $('lang').addEventListener('click', function () { state.lang = state.lang === 'ar' ? 'en' : 'ar'; renderAll(); });
  $('metric').addEventListener('change', function (e) { state.metric = e.target.value; renderDynamic(); });
  $('add').addEventListener('change', function (e) {
    if (e.target.value && state.list.length < MAX) state.list.push(e.target.value);
    renderDynamic();
  });
  $('chips').addEventListener('click', function (e) {
    var b = e.target.closest('button');
    if (!b) return;
    state.list = state.list.filter(function (c) { return c !== b.getAttribute('data-c'); });
    renderDynamic();
  });
  $('world').addEventListener('change', function (e) { state.world = e.target.checked; renderDynamic(); });
  $('year').addEventListener('input', function (e) { state.year = +e.target.value; renderRank(); renderProfile(); writeHash(); });
  $('profile').addEventListener('change', function (e) { state.profile = e.target.value; renderProfile(); writeHash(); });
  $('wi-country').addEventListener('change', function (e) { state.wi = e.target.value; renderWhatif(); });
  $('wi-share').addEventListener('input', renderWhatif);
  $('wi-cf').addEventListener('input', renderWhatif);
  $('csv').addEventListener('click', downloadCsv);
  $('share').addEventListener('click', function () {
    writeHash();
    var done = function (k) { $('share-ok').textContent = t(k); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(location.href).then(function () { done('copiedOk'); }, function () { done('copied'); });
    } else done('copied');
  });
  var resizeTimer;
  window.addEventListener('resize', function () { clearTimeout(resizeTimer); resizeTimer = setTimeout(renderChart, 120); });

  readHash();
  $('year').min = START; $('year').max = END; $('year').step = 1; $('year').value = state.year;
  renderAll();
})();
