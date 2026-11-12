const fmt=n=>Math.round(n).toLocaleString('en-US');
const money=n=>(n<0?'−':'')+fmt(Math.abs(n));
const r5=n=>Math.round(n/5)*5;

// أنواع المشاريع: افتراضات تقديرية لسوق جدة 2026–2027، وكلها قابلة للتعديل
// unit: اسم وحدة البيع، cogsHint: وش تشمل تكلفة البضاعة، food: هل يناسبه موقع طلبات خاص
const TYPES={
 cafe:{name:'مقهى مختص',ic:'☕',unit:'طلب',orders:180,ticket:25,cogs:30,delivery:15,commission:22,rent:150000,saudi:3,expat:3,capexFit:220000,
   equip:165000,equipL:'المعدات (مكينة إسبريسو، مطاحن، ثلاجات، فرن، نقاط بيع)',furn:45000,furnL:'الأثاث والجلسات',lic:25000,inv:20000,mktOpen:20000,util:3200,maint:2000,
   cogsHint:'بن، حليب، أكواب، حلويات',staffHint:'باريستا وخدمة',area:'90 م²',food:true},
 restaurant:{name:'مطعم',ic:'🍽️',unit:'طلب',orders:165,ticket:45,cogs:32,delivery:35,commission:22,rent:180000,saudi:3,expat:7,capexFit:280000,
   equip:240000,equipL:'معدات المطبخ (أفران، شوايات، ثلاجات، شفاطات، نقاط بيع)',furn:60000,furnL:'الأثاث والجلسات',lic:35000,inv:30000,mktOpen:25000,util:6500,maint:3000,
   cogsHint:'لحوم، أرز، خضار، تغليف',staffHint:'طباخين وخدمة',area:'150 م²',food:true},
 laundry:{name:'مغسلة ملابس',ic:'🧺',unit:'فاتورة',orders:70,ticket:45,cogs:12,delivery:0,commission:0,rent:72000,saudi:1,expat:4,capexFit:80000,
   equip:190000,equipL:'المعدات (غسالات صناعية، نشافات، مكاوي بخار، غلاية)',furn:12000,furnL:'الكاونتر والرفوف',lic:15000,inv:8000,mktOpen:10000,util:7500,maint:3000,
   cogsHint:'منظفات، تغليف، علاقات',staffHint:'عمال غسيل وكي',area:'100 م²',food:false},
 salon:{name:'صالون حلاقة رجالي',ic:'💈',unit:'زبون',orders:45,ticket:55,cogs:8,delivery:0,commission:0,rent:60000,saudi:1,expat:4,capexFit:90000,
   equip:55000,equipL:'المعدات (كراسي حلاقة، مغاسل، أدوات، تعقيم)',furn:25000,furnL:'الأثاث وصالة الانتظار',lic:15000,inv:5000,mktOpen:10000,util:2200,maint:1000,
   cogsHint:'منتجات العناية والمستهلكات',staffHint:'حلاقين',area:'60 م²',food:false},
 grocery:{name:'بقالة / ميني ماركت',ic:'🛒',unit:'فاتورة',orders:380,ticket:32,cogs:76,delivery:10,commission:15,rent:90000,saudi:1,expat:3,capexFit:60000,
   equip:110000,equipL:'المعدات (ثلاجات عرض، رفوف، كاشير، كاميرات)',furn:0,furnL:'الأثاث',lic:15000,inv:150000,mktOpen:8000,util:5500,maint:1500,
   cogsHint:'تكلفة شراء البضاعة',staffHint:'كاشير وعمال',area:'120 م²',food:false},
 retail:{name:'محل تجزئة (ملابس / عطور)',ic:'🛍️',unit:'فاتورة',orders:28,ticket:190,cogs:52,delivery:5,commission:15,rent:140000,saudi:2,expat:1,capexFit:140000,
   equip:20000,equipL:'المعدات (كاشير، كاميرات، إنارة عرض)',furn:40000,furnL:'الرفوف وفترينات العرض',lic:15000,inv:120000,mktOpen:20000,util:2500,maint:1000,
   cogsHint:'تكلفة شراء البضاعة',staffHint:'بائعين',area:'70 م²',food:false},
};
const BASE={saudiSal:5000,expatSal:3500};
const DEF={type:'cafe',...BASE,...TYPES.cafe};
function scen(t){const p=TYPES[t];return {low:{orders:r5(p.orders*.72),ticket:Math.round(p.ticket*.92),cogs:p.cogs+3},base:{orders:p.orders,ticket:p.ticket,cogs:p.cogs},high:{orders:r5(p.orders*1.33),ticket:Math.round(p.ticket*1.08),cogs:Math.max(1,p.cogs-2)}}}
const SCEN=scen('cafe');
function fieldsFor(t){const p=TYPES[t];return [
 ['orders',`عدد ${p.unit==='زبون'?'الزباين':p.unit==='طلب'?'الطلبات':'الفواتير'} يوميًا`,r5(p.orders*.3),r5(p.orders*2.2),p.orders>100?5:1,'',''],
 ['ticket','متوسط الفاتورة',Math.max(5,Math.round(p.ticket*.5)),Math.round(p.ticket*2),p.ticket>100?5:1,' ريال',''],
 ['cogs','تكلفة البضاعة والمواد من المبيعات',Math.max(1,p.cogs-15),Math.min(92,p.cogs+15),1,'%',p.cogsHint],
 ['delivery','نسبة المبيعات من تطبيقات التوصيل',0,60,5,'%',''],
 ['commission','عمولة التطبيقات',0,30,1,'%',''],
 ['rent','الإيجار السنوي',20000,400000,5000,' ريال',''],
 ['saudi','موظفين سعوديين',0,8,1,'','يشمل المدير'],
 ['expat','موظفين غير سعوديين',0,12,1,'',p.staffHint],
 ['capexFit','الديكور والتجهيز',20000,600000,10000,' ريال',''],
]}
let S={...DEF};

function model(s){
  const capex=[
    ['الديكور والتشطيب والتكييف',s.capexFit],
    [s.equipL,s.equip],
    ...(s.furn?[[s.furnL,s.furn]]:[]),
    ['التراخيص والدفاع المدني والتصميم',s.lic],
    ['مخزون البداية',s.inv],
    ['تسويق الافتتاح',s.mktOpen],
    ['إيجار أول 6 أشهر (يدفع مقدم)',s.rent/2],
    ['احتياطي تشغيل أول شهرين (رواتب ومصاريف)',0],
  ];
  const resIdx=capex.length-1;
  const fixedStaff=s.saudi>0?(8000+(s.saudi-1)*s.saudiSal)*1.12:0; // المدير 8,000 + التأمينات 12%
  const expatCost=s.expat*(s.expatSal+1000+800+450); // سكن ومواصلات + مقابل مالي + إقامة وتأمين طبي
  const cleaner=2500;
  const staff=fixedStaff+expatCost+cleaner;
  const fixed={rent:s.rent/12,staff,util:s.util,maint:s.maint,systems:900,acct:1500,gov:1000};
  const fixedSum=Object.values(fixed).reduce((a,b)=>a+b,0);
  capex[resIdx][1]=Math.round(fixedSum*2/1000)*1000;
  const capexSum=capex.reduce((a,c)=>a+c[1],0);
  const contingency=Math.round(capexSum*0.05/1000)*1000;
  capex.push(['احتياطي طوارئ 5%',contingency]);
  const capexTotal=capexSum+contingency;
  const varPct=s.cogs/100+(s.delivery/100)*(s.commission/100)+0.012+0.03; // بضاعة + عمولة + رسوم بطاقات + تسويق
  const dep=(capexTotal-s.rent/2-capex[resIdx][1]-s.inv)/60; // استهلاك الأصول 5 سنوات
  function month(orders){
    const rev=orders*s.ticket*30;
    const cogs=rev*s.cogs/100, comm=rev*(s.delivery/100)*(s.commission/100), card=rev*0.012, mkt=rev*0.03;
    const ebitda=rev-cogs-comm-card-mkt-fixedSum;
    const zakat=Math.max(0,(ebitda-dep))*0.025;
    return {rev,cogs,comm,card,mkt,ebitda,dep,zakat,net:ebitda-dep-zakat,cash:ebitda-zakat};
  }
  const steady=month(s.orders);
  const be=fixedSum/(s.ticket*30*(1-varPct)); // عدد يومي للتعادل (قبل الاستهلاك)
  // تدفق 60 شهر: صعود تدريجي 6 أشهر، نمو 5% سنويًا بعد السنة الأولى، تضخم تكاليف ثابتة 2%
  let cum=-capexTotal+capex[resIdx][1]; // الاحتياطي يبقى نقد في الحساب حتى يُصرف
  const series=[-capexTotal]; let payback=null;
  const ramp=[.55,.62,.7,.78,.86,.94];
  for(let m=1;m<=60;m++){
    const y=Math.floor((m-1)/12);
    const o=s.orders*(m<=6?ramp[m-1]:1)*Math.pow(1.05,y);
    const mm=month(o); const extraFixed=fixedSum*(Math.pow(1.02,y)-1);
    let cash=mm.cash-extraFixed;
    if(m<=6) cash+=fixed.rent; // إيجار أول 6 أشهر مدفوع ضمن رأس المال
    cum+=cash; series.push(cum);
    if(payback===null&&cum>=0) payback=m;
  }
  const npv=(()=>{let v=-capexTotal;for(let m=1;m<=60;m++)v+=(series[m]-series[m-1])/Math.pow(1.12,m/12);return v})();
  return {capex,capexTotal,fixed,fixedSum,staff,steady,be,series,payback,varPct,npv};
}
