"""Restaurant food cost & menu engineering model (sample data, Saudi restaurant).
Builds food_cost_model.xlsx with live Excel formulas."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.chart import BarChart, Reference
from openpyxl.worksheet.datavalidation import DataValidation

F = "Arial"; H = PatternFill("solid", fgColor="1F3A5F"); IN = Font(name=F, color="0000FF")
thin = Side(style="thin", color="D0D5DD"); B = Border(bottom=thin)
def head(ws, row, cols):
    for i, c in enumerate(cols, 1):
        x = ws.cell(row, i, c); x.font = Font(name=F, bold=True, color="FFFFFF"); x.fill = H
        x.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

wb = Workbook()
# ---------- Ingredients ----------
ing = wb.active; ing.title = "المكونات"; ing.sheet_view.rightToLeft = True
ing["A1"] = "أسعار المكونات (أدخل سعر الشراء – الخلايا الزرقاء قابلة للتعديل)"; ing["A1"].font = Font(name=F, bold=True, size=13)
head(ing, 3, ["الكود", "المكون", "وحدة الشراء", "سعر الشراء (ريال)", "كمية الوحدة (جم/مل)", "نسبة الهدر %", "التكلفة لكل جم بعد الهدر"])
items = [
 ("R01","أرز بسمتي","كيس 10 كجم",95,10000,3),("C01","دجاج كامل","كرتون 10 حبات (1100جم)",140,11000,10),
 ("L01","لحم غنم","كجم",62,1000,25),("O01","زيت نباتي","جالون 4.5 لتر",48,4500,0),
 ("S01","بهارات كبسة","كجم",38,1000,0),("V01","بصل","كيس 10 كجم",22,10000,10),
 ("V02","طماطم","صندوق 5 كجم",18,5000,12),("D01","لبن","لتر",6,1000,0),
 ("B01","خبز صامولي","كيس 6 حبات (420جم)",4,420,5),("P01","بطاطس مجمدة","كيس 2.5 كجم",21,2500,4),
 ("H01","حمص","علبة 400جم",3.5,400,0),("T01","طحينة","علبة 500جم",11,500,0),
 ("Y01","زبادي","علبة 1 كجم",9,1000,0),("Q01","خيار","كجم",5,1000,8),
]
for r, it in enumerate(items, 4):
    for c, v in enumerate(it, 1):
        x = ing.cell(r, c, v); x.font = IN if c in (4,5,6) else Font(name=F); x.border = B
    ing.cell(r, 7, f"=D{r}/E{r}/(1-F{r}/100)").number_format = "0.0000"
    ing.cell(r, 7).font = Font(name=F)
for col, w in zip("ABCDEFG", [8,18,22,16,18,13,20]): ing.column_dimensions[col].width = w
last_ing = 3 + len(items)

# ---------- Recipes ----------
rec = wb.create_sheet("الوصفات"); rec.sheet_view.rightToLeft = True
rec["A1"] = "تكلفة كل طبق (الكمية بالجرام/مل لكل حصة)"; rec["A1"].font = Font(name=F, bold=True, size=13)
head(rec, 3, ["الطبق", "كود المكون", "المكون", "الكمية (جم)", "التكلفة (ريال)"])
recipes = {
 "كبسة دجاج": [("R01",250),("C01",550),("O01",20),("S01",8),("V01",60),("V02",50)],
 "مندي لحم": [("R01",250),("L01",400),("O01",15),("S01",8),("V01",40)],
 "شاورما عربي": [("C01",120),("B01",140),("P01",120),("T01",25),("Q01",30)],
 "صحن حمص": [("H01",200),("T01",30),("O01",10)],
 "لبن": [("D01",250)],
 "سلطة زبادي": [("Y01",150),("Q01",60)],
}
r = 4; dish_rows = {}
dv = DataValidation(type="list", formula1=f"=المكونات!$A$4:$A${last_ing}", allow_blank=False); rec.add_data_validation(dv)
for dish, lines in recipes.items():
    start = r
    for code, q in lines:
        rec.cell(r,1,dish); c = rec.cell(r,2,code); c.font = IN; dv.add(c)
        rec.cell(r,3,f"=INDEX(المكونات!$B$4:$B${last_ing},MATCH(B{r},المكونات!$A$4:$A${last_ing},0))")
        q_ = rec.cell(r,4,q); q_.font = IN
        rec.cell(r,5,f"=D{r}*INDEX(المكونات!$G$4:$G${last_ing},MATCH(B{r},المكونات!$A$4:$A${last_ing},0))").number_format = "0.00"
        r += 1
    dish_rows[dish] = (start, r-1)
for col, w in zip("ABCDE", [16,12,18,13,14]): rec.column_dimensions[col].width = w
last_rec = r-1

# ---------- Menu engineering ----------
mn = wb.create_sheet("هندسة المنيو"); mn.sheet_view.rightToLeft = True
mn["A1"] = "تكلفة الطبق ونسبة تكلفة الأكل وتصنيف المنيو (شهر واحد)"; mn["A1"].font = Font(name=F, bold=True, size=13)
mn["A2"] = "هدف نسبة تكلفة الأكل %"; mn["C2"] = 32; mn["C2"].font = IN
head(mn, 4, ["الطبق","تكلفة الحصة","سعر البيع","نسبة تكلفة الأكل","هامش الربح للحصة","المبيعات الشهرية (حصة)","إجمالي الربح","الشعبية","الربحية","التصنيف","السعر المقترح للهدف"])
prices = {"كبسة دجاج":32,"مندي لحم":70,"شاورما عربي":15,"صحن حمص":12,"لبن":5,"سلطة زبادي":8}
sales = {"كبسة دجاج":1450,"مندي لحم":620,"شاورما عربي":2100,"صحن حمص":380,"لبن":1700,"سلطة زبادي":260}
r = 5
for dish,(s,e) in dish_rows.items():
    mn.cell(r,1,dish)
    mn.cell(r,2,f"=SUM(الوصفات!E{s}:E{e})").number_format = "0.00"
    p = mn.cell(r,3,prices[dish]); p.font = IN
    mn.cell(r,4,f"=B{r}/C{r}").number_format = "0.0%"
    mn.cell(r,5,f"=C{r}-B{r}").number_format = "0.00"
    q = mn.cell(r,6,sales[dish]); q.font = IN
    mn.cell(r,7,f"=E{r}*F{r}").number_format = "#,##0"
    r += 1
lr = r-1
for rr in range(5, lr+1):
    # Kasavana-Smith: popularity >= 70% of average mix share; profitability >= weighted avg margin
    mn.cell(rr,8,f'=IF(F{rr}/SUM($F$5:$F${lr})>=0.7/COUNT($F$5:$F${lr}),"عالية","منخفضة")')
    mn.cell(rr,9,f'=IF(E{rr}>=SUMPRODUCT($E$5:$E${lr},$F$5:$F${lr})/SUM($F$5:$F${lr}),"عالية","منخفضة")')
    mn.cell(rr,10,f'=IF(AND(H{rr}="عالية",I{rr}="عالية"),"نجمة ⭐",IF(H{rr}="عالية","حصان عمل",IF(I{rr}="عالية","لغز","كلب")))')
    mn.cell(rr,11,f"=ROUNDUP(B{rr}/($C$2/100),0)").number_format = "0"
tot = lr+2
mn.cell(tot,1,"الإجمالي").font = Font(name=F,bold=True)
mn.cell(tot,7,f"=SUM(G5:G{lr})").number_format = "#,##0"
mn.cell(tot+1,1,"نسبة تكلفة الأكل المرجحة"); mn.cell(tot+1,4,f"=SUMPRODUCT(B5:B{lr},F5:F{lr})/SUMPRODUCT(C5:C{lr},F5:F{lr})").number_format="0.0%"
red = PatternFill("solid", fgColor="F8D7DA"); green = PatternFill("solid", fgColor="D1F2DD")
mn.conditional_formatting.add(f"D5:D{lr}", FormulaRule(formula=[f"D5>$C$2/100"], fill=red))
mn.conditional_formatting.add(f"D5:D{lr}", FormulaRule(formula=[f"D5<=$C$2/100"], fill=green))
for col, w in zip("ABCDEFGHIJK", [14,12,10,14,15,17,13,10,10,13,16]): mn.column_dimensions[col].width = w
ch = BarChart(); ch.title = "نسبة تكلفة الأكل لكل طبق"; ch.y_axis.numFmt = "0%"
ch.add_data(Reference(mn, min_col=4, min_row=4, max_row=lr), titles_from_data=True)
ch.set_categories(Reference(mn, min_col=1, min_row=5, max_row=lr)); ch.height = 7; ch.width = 16
mn.add_chart(ch, f"A{tot+4}")

# ---------- Notes ----------
nt = wb.create_sheet("طريقة الاستخدام"); nt.sheet_view.rightToLeft = True
for i, line in enumerate([
 "طريقة الاستخدام",
 "1) حدّث أسعار الشراء ونسبة الهدر في ورقة «المكونات» (الخلايا الزرقاء).",
 "2) عدّل كميات كل وصفة في ورقة «الوصفات»، أو أضف سطر جديد واختر كود المكون من القائمة.",
 "3) ورقة «هندسة المنيو» تحسب تكلفة الحصة ونسبة تكلفة الأكل والربح، وتصنف كل طبق:",
 "   نجمة = مبيعات عالية وربح عالي · حصان عمل = مبيعات عالية وربح أقل · لغز = ربح عالي ومبيعات قليلة · كلب = الاثنين منخفض.",
 "4) «السعر المقترح» = أقل سعر يحقق نسبة تكلفة الأكل المستهدفة في الخلية C2.",
 "ملاحظة: الأسعار والكميات والمبيعات أمثلة تقريبية للتوضيح، وليست بيانات مطعم حقيقي."]):
    c = nt.cell(i+1, 1, line); c.font = Font(name=F, bold=(i==0), size=13 if i==0 else 11)
nt.column_dimensions["A"].width = 110
wb.move_sheet("طريقة الاستخدام", offset=-3)
wb.save("food_cost_model.xlsx"); print("ok")
