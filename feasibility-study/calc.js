let FIELDS=[];let SC=SCEN;
const qs=new URLSearchParams(location.search).get('type');
function setType(t){
  S={type:t,...BASE,...TYPES[t]};SC=scen(t);FIELDS=fieldsFor(t);
  document.querySelectorAll('#types button').forEach(b=>b.classList.toggle('on',b.dataset.t===t));
  document.querySelectorAll('#scen button').forEach(b=>b.classList.toggle('on',b.dataset.s==='base'));
  const box=document.getElementById('inputs');
  box.innerHTML=FIELDS.map(([k,l,mn,mx,st,u,h])=>`<div class="inp"><label for="i_${k}">${l}<output id="o_${k}"></output></label><input type="range" id="i_${k}" min="${mn}" max="${mx}" step="${st}" value="${S[k]}">${h?`<div class="hint">${h}</div>`:''}</div>`).join('');
  FIELDS.forEach(([k])=>{const el=document.getElementById('i_'+k);el.oninput=()=>{S[k]=+el.value;document.querySelectorAll('#scen button').forEach(b=>b.classList.remove('on'));render()};});
  document.getElementById('ptitle').textContent=TYPES[t].ic+' '+TYPES[t].name;
  document.getElementById('parea').textContent=TYPES[t].area;
  try{history.replaceState(null,'','?type='+t)}catch(e){}
  render();
}
document.getElementById('types').innerHTML=Object.entries(TYPES).map(([k,p])=>`<button data-t="${k}">${p.ic} ${p.name}</button>`).join('');
document.querySelectorAll('#types button').forEach(b=>b.onclick=()=>setType(b.dataset.t));
document.querySelectorAll('#scen button').forEach(b=>b.onclick=()=>{Object.assign(S,SC[b.dataset.s]);document.querySelectorAll('#scen button').forEach(x=>x.classList.toggle('on',x===b));FIELDS.forEach(([k])=>document.getElementById('i_'+k).value=S[k]);render()});

let charts={};
function render(){
  FIELDS.forEach(([k,,,,,u])=>document.getElementById('o_'+k)&&(document.getElementById('o_'+k).textContent=(k==='rent'||k==='capexFit'?fmt(S[k]):S[k])+u));
  const M=model(S), st=M.steady;
  const yA=n=>n===1?'سنة':n===2?'سنتين':n+' سنوات', mA=n=>n===1?'شهر':n===2?'شهرين':n<=10?n+' أشهر':n+' شهر';
  const pb=M.payback?[Math.floor(M.payback/12)?yA(Math.floor(M.payback/12)):'',M.payback%12?mA(M.payback%12):''].filter(Boolean).join(' و'):'أكثر من 5 سنوات';
  document.getElementById('kpis').innerHTML=[
    ['رأس المال المطلوب',fmt(M.capexTotal)+' ريال','شامل الإيجار المقدم والاحتياطي'],
    ['صافي الربح الشهري',`<span class="${st.net<0?'neg':'pos'}">${money(st.net)}</span> ريال`,'بعد ما يستقر المشروع'],
    ['نقطة التعادل',fmt(M.be)+' '+TYPES[S.type].unit+' يوميًا',`من ${S.orders} متوقع`],
    ['استرداد رأس المال',pb,'من يوم الافتتاح'],
  ].map(([a,b,c])=>`<div class="k"><span>${a}</span><b>${b}</b><small>${c}</small></div>`).join('');
  const margin=st.net/st.rev*100, safety=(S.orders-M.be)/S.orders*100;
  const v=document.getElementById('verdict');
  v.className='verdict'+(st.net<0?' bad':(!M.payback||M.payback>36?' warn':''));
  v.innerHTML=st.net<0?`<b>المشروع يخسر بهالأرقام.</b> تحتاج ${fmt(M.be)} ${TYPES[S.type].unit} يوميًا عشان تغطي المصاريف، والمتوقع ${S.orders} فقط.`
   :`<b>${!M.payback||M.payback>36?'مربح لكن الاسترداد بطيء':'المشروع مجدي بهالأرقام'}.</b> هامش صافي ${margin.toFixed(0)}%، وهامش الأمان ${safety.toFixed(0)}%: يعني المبيعات تقدر تنزل ${safety.toFixed(0)}% قبل ما يبدأ المشروع يخسر.`;
  // قائمة الدخل
  const R=[
    ['المبيعات',st.rev,'sub'],
    ['تكلفة البضاعة والمواد',-st.cogs],
    ['عمولة تطبيقات التوصيل',-st.comm],
    ['رسوم الدفع بالبطاقة (1.2%)',-st.card],
    ['مجمل الربح',st.rev-st.cogs-st.comm-st.card,'sub'],
    [`رواتب ${S.saudi+S.expat+1} موظفين (شامل التأمينات والمقابل المالي والسكن)`,-M.staff],
    ['الإيجار',-M.fixed.rent],
    ['الكهرباء والمياه والإنترنت',-M.fixed.util],
    ['التسويق (3%)',-st.mkt],
    ['الصيانة والمستهلكات',-M.fixed.maint],
    ['أنظمة ومحاسبة ورسوم بلدية',-(M.fixed.systems+M.fixed.acct+M.fixed.gov)],
    ['الربح التشغيلي',st.ebitda,'sub'],
    ['استهلاك الأصول (5 سنوات)',-st.dep],
    ['الزكاة (2.5%)',-st.zakat],
    ['صافي الربح',st.net,'tot'],
  ];
  document.getElementById('pl').innerHTML='<tr><th>البند</th><th class="n">ريال/شهر</th><th class="n">من المبيعات</th></tr>'+R.map(([a,b,c])=>`<tr class="${c||''}"><td>${a}</td><td class="n ${b<0&&c?'neg':''}">${money(b)}</td><td class="n">${(b/st.rev*100).toFixed(1)}%</td></tr>`).join('');
  document.getElementById('capex').innerHTML='<tr><th>البند</th><th class="n">ريال</th></tr>'+M.capex.map(([a,b])=>`<tr><td>${a}</td><td class="n">${fmt(b)}</td></tr>`).join('')+`<tr class="tot"><td>الإجمالي</td><td class="n">${fmt(M.capexTotal)}</td></tr>`;
  // السيناريوهات
  const sc=Object.entries(SC).map(([k,v])=>[k,model({...S,...v})]);
  const names={low:'متشائم',base:'متوقع',high:'متفائل'};
  document.getElementById('scTable').innerHTML=`<tr><th></th>${sc.map(([k])=>`<th class="n">${names[k]}</th>`).join('')}</tr>`+[
    ['العدد يوميًا',([k])=>SC[k].orders],['متوسط الفاتورة',([k])=>SC[k].ticket+' ريال'],['تكلفة البضاعة',([k])=>SC[k].cogs+'%'],
    ['المبيعات الشهرية',([,m])=>fmt(m.steady.rev)],['صافي الربح الشهري',([,m])=>`<span class="${m.steady.net<0?'neg':'pos'}">${money(m.steady.net)}</span>`],
    ['الاسترداد',([,m])=>m.payback?m.payback+' شهر':'أكثر من 60 شهر'],['صافي القيمة الحالية (خصم 12%)',([,m])=>`<span class="${m.npv<0?'neg':'pos'}">${money(m.npv)}</span>`],
  ].map(([l,f])=>`<tr><td>${l}</td>${sc.map(x=>`<td class="n">${f(x)}</td>`).join('')}</tr>`).join('')+`<tr><td colspan="4" class="note">السيناريوهات تغير العدد اليومي والفاتورة وتكلفة البضاعة فقط، والباقي من اختياراتك.</td></tr>`;
  // الرسوم
  Chart.defaults.font.family='Tajawal,"Segoe UI",Tahoma';Chart.defaults.color='#7a6a5c';
  const labels=[...Array(61).keys()].map(m=>m%12===0?('سنة '+m/12):'');
  const cols={low:'#b42318',base:'#6f4518',high:'#1f7a4d'};
  const ds=sc.map(([k,m])=>({label:names[k],data:m.series,borderColor:cols[k],backgroundColor:cols[k],pointRadius:0,borderWidth:k==='base'?3:2,tension:.2}));
  const baseS=sc.find(x=>x[0]==='base')[1].series, yMax=Math.ceil(Math.max(250000,...baseS)*1.5/250000)*250000;
  if(charts.cash){charts.cash.data.datasets=ds;charts.cash.options.scales.y.max=yMax;charts.cash.update()}else charts.cash=new Chart(cCash,{type:'line',data:{labels,datasets:ds},options:{maintainAspectRatio:false,layout:{padding:{left:18}},interaction:{mode:'index',intersect:false},scales:{x:{reverse:true,ticks:{autoSkip:false,maxRotation:0},grid:{display:false}},y:{position:'right',max:yMax,ticks:{maxTicksLimit:7,callback:v=>(v/1000)+' ألف'},grid:{color:c=>c.tick.value===0?'#2a1f17':'#eee'}}},plugins:{legend:{position:'bottom'},tooltip:{callbacks:{title:i=>'الشهر '+i[0].dataIndex,label:c=>c.dataset.label+': '+money(c.raw)+' ريال'}}}}});
  const split=[['البضاعة والمواد',st.cogs],['الرواتب',M.staff],['الإيجار',M.fixed.rent],['التطبيقات والبطاقات',st.comm+st.card],['تشغيل وتسويق',st.mkt+M.fixed.util+M.fixed.maint+M.fixed.systems+M.fixed.acct+M.fixed.gov],['استهلاك وزكاة',st.dep+st.zakat],['صافي الربح',Math.max(0,st.net)]];
  const sd={labels:split.map(x=>x[0]),datasets:[{data:split.map(x=>+(x[1]/st.rev*100).toFixed(1)),backgroundColor:['#b9824a','#6f4518','#a0522d','#d97706','#c9b8a6','#8c7b6b','#1f7a4d']}]};
  if(charts.split){charts.split.data=sd;charts.split.update()}else charts.split=new Chart(cSplit,{type:'doughnut',data:sd,options:{maintainAspectRatio:false,plugins:{legend:{position:'right'},tooltip:{callbacks:{label:c=>c.label+': '+c.raw+'%'}}}}});
  // الحساسية
  const baseNet=st.net*12, tests=[['المبيعات اليومية','orders',1],['متوسط الفاتورة','ticket',1],['تكلفة البضاعة','cogs',-1],['الرواتب','expatSal',-1],['الإيجار','rent',-1]];
  const sens=tests.map(([l,k,d])=>{const up=model({...S,[k]:S[k]*(1+.1*d),...(k==='expatSal'?{saudiSal:S.saudiSal*0.9}:{})}).steady.net*12-baseNet;return [l,Math.round(up)]}).sort((a,b)=>Math.abs(b[1])-Math.abs(a[1]));
  const sv={labels:sens.map(x=>x[0]),datasets:[{label:'تحسن 10%',data:sens.map(x=>x[1]),backgroundColor:'#1f7a4d'},{label:'تراجع 10%',data:sens.map(x=>-x[1]),backgroundColor:'#b42318'}]};
  if(charts.sens){charts.sens.data=sv;charts.sens.update()}else charts.sens=new Chart(cSens,{type:'bar',data:sv,options:{indexAxis:'y',maintainAspectRatio:false,scales:{x:{stacked:true,ticks:{maxTicksLimit:5,callback:v=>(v/1000)+' ألف'}},y:{stacked:true,position:'right'}},plugins:{legend:{position:'bottom'},tooltip:{callbacks:{label:c=>c.dataset.label+': '+money(c.raw)+' ريال/سنة'}}}}});
  // التوصيات
  const appCost=st.comm*12, top=sens[0][0];
  document.getElementById('recs').innerHTML=[
    `<b>أهم رقم في المشروع هو ${top}:</b> تغيره 10% يحرك صافي الربح ${fmt(Math.abs(sens[0][1]))} ريال في السنة. ركّز عليه قبل أي شي ثاني.`,
    `<b>نقطة التعادل ${fmt(M.be)} ${TYPES[S.type].unit} يوميًا.</b> قبل ما توقع عقد الإيجار، عدّ الزباين اللي يمرون قدام الموقع في ساعات الذروة وتأكد إن ${fmt(M.be)} ${TYPES[S.type].unit} رقم واقعي.`,
    S.delivery>0&&S.commission>0?`<b>تطبيقات التوصيل تاخذ نحو ${fmt(appCost)} ريال في السنة.</b> ${TYPES[S.type].food?'موقع طلبات خاص (<a href="https://algilani2008.github.io/quickorder-menu/">مثل هذا</a>) يحول جزء منها لطلبات مباشرة بدون عمولة.':'قناة بيع مباشرة (واتساب أو متجر إلكتروني) تقلل الاعتماد عليها.'}`:'',
    `<b>جهز رأس مال يكفي أول 6 أشهر.</b> المشروع يبدأ بنحو نصف مبيعاته المتوقعة، فلا تحسب الربح من أول شهر.`,
    `<b>الرسوم الحكومية:</b> المقابل المالي 800 ريال شهريًا لكل عامل غير سعودي محسوب في الرواتب، وإعفاء المنشآت الصغيرة ينتهي 21 يناير 2027. الموظف السعودي يحسب في نطاقات إذا راتبه 5,000 ريال فأكثر من 25 أبريل 2027.`,
  ].filter(Boolean).map(x=>`<li>${x}</li>`).join('');
}
setType(TYPES[qs]?qs:'cafe');
