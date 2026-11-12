"""HR KPI dashboard on synthetic data for a 180-employee Saudi services company.
Outputs employees.csv, kpis.json and index.html (Chart.js)."""
import random, json, csv, datetime as dt
random.seed(7)
depts = {"العمليات":70,"المبيعات":30,"المالية":12,"الموارد البشرية":8,"تقنية المعلومات":10,"خدمة العملاء":35,"المشتريات والمخازن":15}
nats = [("سعودي",0.42),("يمني",0.12),("مصري",0.14),("هندي",0.12),("باكستاني",0.08),("فلبيني",0.07),("سوداني",0.05)]
def pick(w): r=random.random(); a=0
for _ in [0]: pass
def wpick(lst):
    r=random.random(); a=0
    for v,p in lst:
        a+=p
        if r<=a: return v
    return lst[-1][0]
base = {"العمليات":5200,"المبيعات":6500,"المالية":9000,"الموارد البشرية":8500,"تقنية المعلومات":11000,"خدمة العملاء":4800,"المشتريات والمخازن":5600}
rows=[]; eid=1000
start = dt.date(2025,1,1)
for d,n in depts.items():
    for i in range(int(n*1.25)):  # include leavers
        eid+=1
        hire = start - dt.timedelta(days=random.randint(0,6*365))
        left = None
        if random.random()<0.2:
            left = start + dt.timedelta(days=random.randint(10,660))
        nat = wpick(nats)
        sal = round(base[d]*random.uniform(0.8,1.5)/50)*50
        absent = max(0, int(random.gauss(5 if d!="العمليات" else 8, 3)))
        ot = max(0, int(random.gauss(14 if d in ("العمليات","خدمة العملاء") else 4, 6)))
        rows.append(dict(id=eid,dept=d,nationality=nat,hire=hire.isoformat(),leave=left.isoformat() if left else "",salary=sal,absent_days=absent,overtime_hours_m=ot,gender=random.choice(["ذكر"]*4+["أنثى"])))
with open("employees.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
end = dt.date(2026,10,31)
active=[r for r in rows if not r["leave"] or r["leave"]>end.isoformat()]
leavers=[r for r in rows if r["leave"] and "2025-11-01"<=r["leave"]<=end.isoformat()]
avg_head=(len(active)+len(active)+len(leavers))/2
k = {
 "headcount":len(active),
 "saudization":round(100*sum(r["nationality"]=="سعودي" for r in active)/len(active),1),
 "turnover_12m":round(100*len(leavers)/avg_head,1),
 "avg_salary":round(sum(r["salary"] for r in active)/len(active)),
 "payroll_m":round(sum(r["salary"] for r in active)/1e6,2),
 "absence_rate":round(100*sum(r["absent_days"] for r in active)/(len(active)*260),2),
 "women_pct":round(100*sum(r["gender"]=="أنثى" for r in active)/len(active),1),
}
by=lambda key: {d:[r for r in active if r[key]==d] for d in sorted({r[key] for r in active})}
k["dept"]=[{"name":d,"head":len(v),"saudi":round(100*sum(x["nationality"]=="سعودي" for x in v)/len(v),1),
            "avg_sal":round(sum(x["salary"] for x in v)/len(v)),"ot":round(sum(x["overtime_hours_m"] for x in v)/len(v),1),
            "turn":round(100*sum(1 for x in leavers if x["dept"]==d)/max(1,len(v)),1)} for d,v in by("dept").items()]
k["nat"]=[{"name":d,"n":len(v)} for d,v in sorted(by("nationality").items(), key=lambda t:-len(t[1]))]
months=[]
m=dt.date(2025,11,1)
while m<=end:
    nm=(m.replace(day=28)+dt.timedelta(days=4)).replace(day=1)
    hires=sum(1 for r in rows if m.isoformat()<=r["hire"]<nm.isoformat()); lv=sum(1 for r in rows if r["leave"] and m.isoformat()<=r["leave"]<nm.isoformat())
    months.append({"m":m.strftime("%Y-%m"),"leavers":lv}); m=nm
k["months"]=months
json.dump(k,open("kpis.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
html=open("template.html",encoding="utf-8").read().replace("__DATA__",json.dumps(k,ensure_ascii=False))
open("index.html","w",encoding="utf-8").write(html); print(json.dumps({x:k[x] for x in k if x not in("dept","nat","months")},ensure_ascii=False))
