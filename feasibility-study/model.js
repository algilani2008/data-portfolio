const fmt=n=>Math.round(n).toLocaleString('en-US');
const money=n=>(n<0?'−':'')+fmt(Math.abs(n));
// الافتراضات
const DEF={orders:180,ticket:25,cogs:30,delivery:15,commission:22,rent:150000,saudi:3,expat:3,saudiSal:5000,expatSal:3500,capexFit:220000};
const SCEN={low:{orders:130,ticket:23,cogs:33,rent:150000},base:{orders:180,ticket:25,cogs:30,rent:150000},high:{orders:240,ticket:27,cogs:28,rent:150000}};
const FIELDS=[
 ['orders','عدد الطلبات يوميًا',60,400,5,'',''],
 ['ticket','متوسط الفاتورة',15,45,1,' ريال',''],
 ['cogs','تكلفة المواد من المبيعات',20,45,1,'%','بن، حليب، أكواب، حلويات'],
 ['delivery','نسبة الطلبات من تطبيقات التوصيل',0,60,5,'%',''],
 ['commission','عمولة التطبيقات',10,30,1,'%',''],
 ['rent','الإيجار السنوي',60000,300000,5000,' ريال',''],
 ['saudi','موظفين سعوديين',0,6,1,'','يشمل المدير'],
 ['expat','موظفين غير سعوديين',0,8,1,'','باريستا وخدمة'],
 ['capexFit','الديكور والتجهيز',100000,450000,10000,' ريال',''],
];
let S={...DEF};
function model(s){
  // رأس المال
  const capex=[
    ['الديكور والتشطيب والتكييف',s.capexFit],
    ['المعدات (مكينة إسبريسو، مطاحن، ثلاجات، فرن، نقاط بيع)',165000],
    ['الأثاث والجلسات',45000],
    ['التراخيص والدفاع المدني والتصميم',25000],
    ['مخزون البداية',20000],
    ['تسويق الافتتاح',20000],
    ['إيجار أول 6 أشهر (يدفع مقدم)',s.rent/2],
    ['احتياطي تشغيل أول شهرين (رواتب ومصاريف)',0],
  ];
  const fixedStaff=s.saudi>0?(8000+(s.saudi-1)*s.saudiSal)*1.12:0; // المدير 8,000 + التأمينات 12%
  const expatCost=s.expat*(s.expatSal+1000+800+450); // سكن ومواصلات + مقابل مالي + إقامة وتأمين طبي
  const cleaner=2500;
  const staff=fixedStaff+expatCost+cleaner;
  const fixed={rent:s.rent/12,staff,util:3200,maint:2000,systems:900,acct:1500,gov:1000};
  const fixedSum=Object.values(fixed).reduce((a,b)=>a+b,0);
  capex[7][1]=Math.round(fixedSum*2/1000)*1000;
  const capexSum=capex.reduce((a,c)=>a+c[1],0)*1.0;
  const contingency=Math.round(capexSum*0.05/1000)*1000;
  capex.push(['احتياطي طوارئ 5%',contingency]);
  const capexTotal=capexSum+contingency;
  // نسب متغيرة من المبيعات
  const varPct=s.cogs/100+(s.delivery/100)*(s.commission/100)+0.012+0.03; // مواد + عمولة + رسوم بطاقات + تسويق
  function month(orders){
    const rev=orders*s.ticket*30;
    const cogs=rev*s.cogs/100, comm=rev*(s.delivery/100)*(s.commission/100), card=rev*0.012, mkt=rev*0.03;
    const ebitda=rev-cogs-comm-card-mkt-fixedSum;
    const dep=(capexTotal-s.rent/2-capex[7][1]-20000)/60; // استهلاك الأصول 5 سنوات
    const zakat=Math.max(0,(ebitda-dep))*0.025;
    return {rev,cogs,comm,card,mkt,ebitda,dep,zakat,net:ebitda-dep-zakat,cash:ebitda-zakat};
  }
  const steady=month(s.orders);
  const be=fixedSum/(s.ticket*30*(1-varPct)); // طلبات يومية للتعادل (قبل الاستهلاك)
  // تدفق 60 شهر: صعود تدريجي 6 أشهر، نمو 5% سنويًا بعد السنة الأولى، تضخم تكاليف ثابتة 2%
  let cum=-capexTotal+capex[7][1]; // الاحتياطي يبقى نقد في الحساب حتى يُصرف
  const series=[-capexTotal]; let payback=null;
  const ramp=[.55,.62,.7,.78,.86,.94];
  for(let m=1;m<=60;m++){
    const y=Math.floor((m-1)/12);
    const o=s.orders*(m<=6?ramp[m-1]:1)*Math.pow(1.05,y);
    const mm=month(o); const extraFixed=fixedSum*(Math.pow(1.02,y)-1);
    // الإيجار المدفوع مقدمًا لأول 6 أشهر محسوب في رأس المال، والاحتياطي كذلك يغطي أول 3 أشهر
    let cash=mm.cash-extraFixed;
    if(m<=6) cash+=fixed.rent;
    cum+=cash; series.push(cum);
    if(payback===null&&cum>=0) payback=m;
  }
  const yr1=series[12]-series[0];
  const npv=(()=>{let v=-capexTotal;for(let m=1;m<=60;m++)v+=(series[m]-series[m-1])/Math.pow(1.12,m/12);return v})();
  return {capex,capexTotal,fixed,fixedSum,staff,steady,be,series,payback,varPct,npv,yr1};
}

