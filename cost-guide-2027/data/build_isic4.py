"""Build data/raw/isic4_classes.csv: every ISIC Rev.4 class (4-digit) licensable in Saudi Arabia,
in Arabic and English, linked to a cost profile (activity_catalog.csv) and a Nitaqat activity
(nitaqat_activities.csv).

The Saudi national classification (used by the Saudi Business Center) extends these classes to
6-digit activities; every 6-digit activity sits under one of these classes, so its first four
digits find its profile here. Excluded: classes not licensable in the Kingdom (alcoholic drinks,
pig farming, gambling), public administration (84), households (97-98) and extraterritorial
bodies (99).

Run: python data/build_isic4.py
"""
import csv
from pathlib import Path

RAW = Path(__file__).resolve().parent / "raw"

SECTIONS = {
    "A": ("الزراعة والحراجة وصيد الأسماك", "Agriculture, forestry & fishing"),
    "B": ("التعدين واستغلال المحاجر", "Mining & quarrying"),
    "C": ("الصناعات التحويلية", "Manufacturing"),
    "D": ("إمدادات الكهرباء والغاز والبخار والتكييف", "Electricity, gas, steam & air conditioning"),
    "E": ("إمدادات المياه والصرف الصحي وإدارة النفايات", "Water supply, sewerage & waste"),
    "F": ("التشييد", "Construction"),
    "G": ("تجارة الجملة والتجزئة وإصلاح المركبات", "Wholesale & retail trade, vehicle repair"),
    "H": ("النقل والتخزين", "Transport & storage"),
    "I": ("أنشطة الإقامة والخدمات الغذائية", "Accommodation & food services"),
    "J": ("المعلومات والاتصالات", "Information & communication"),
    "K": ("الأنشطة المالية وأنشطة التأمين", "Finance & insurance"),
    "L": ("الأنشطة العقارية", "Real estate"),
    "M": ("الأنشطة المهنية والعلمية والتقنية", "Professional, scientific & technical"),
    "N": ("الخدمات الإدارية وخدمات الدعم", "Administrative & support services"),
    "P": ("التعليم", "Education"),
    "Q": ("الصحة البشرية والعمل الاجتماعي", "Human health & social work"),
    "R": ("الفنون والترفيه والتسلية", "Arts, entertainment & recreation"),
    "S": ("أنشطة الخدمات الأخرى", "Other service activities"),
}

def section(code):
    d = int(code[:2])
    for s, lo, hi in [("A", 1, 3), ("B", 5, 9), ("C", 10, 33), ("D", 35, 35), ("E", 36, 39), ("F", 41, 43), ("G", 45, 47),
                      ("H", 49, 53), ("I", 55, 56), ("J", 58, 63), ("K", 64, 66), ("L", 68, 68), ("M", 69, 75),
                      ("N", 77, 82), ("P", 85, 85), ("Q", 86, 88), ("R", 90, 93), ("S", 94, 96)]:
        if lo <= d <= hi:
            return s
    raise ValueError(code)

# code | English | Arabic
CLASSES = """
0111|Growing of cereals, leguminous crops and oil seeds|زراعة الحبوب والبقوليات والبذور الزيتية
0112|Growing of rice|زراعة الأرز
0113|Growing of vegetables, melons, roots and tubers|زراعة الخضروات والبطيخ والجذور والدرنات
0114|Growing of sugar cane|زراعة قصب السكر
0115|Growing of tobacco|زراعة التبغ
0116|Growing of fibre crops|زراعة المحاصيل الليفية
0119|Growing of other non-perennial crops (incl. fodder and flowers)|زراعة المحاصيل غير الدائمة الأخرى (منها الأعلاف والزهور)
0121|Growing of grapes|زراعة العنب
0122|Growing of tropical and subtropical fruits (incl. dates)|زراعة الفواكه الاستوائية وشبه الاستوائية (منها التمور)
0123|Growing of citrus fruits|زراعة الحمضيات
0124|Growing of pome and stone fruits|زراعة التفاحيات وذات النوى
0125|Growing of other tree and bush fruits and nuts|زراعة فواكه الأشجار والشجيرات والمكسرات الأخرى
0126|Growing of oleaginous fruits (incl. olives)|زراعة الثمار الزيتية (منها الزيتون)
0127|Growing of beverage crops (incl. coffee)|زراعة محاصيل المشروبات (منها البن)
0128|Growing of spices, aromatic, drug and pharmaceutical crops|زراعة التوابل والنباتات العطرية والطبية
0129|Growing of other perennial crops|زراعة المحاصيل الدائمة الأخرى
0130|Plant propagation and nurseries|إكثار النباتات والمشاتل
0141|Raising of cattle and buffaloes|تربية الأبقار والجاموس
0142|Raising of horses|تربية الخيول
0143|Raising of camels|تربية الإبل
0144|Raising of sheep and goats|تربية الأغنام والماعز
0146|Raising of poultry|تربية الدواجن
0149|Raising of other animals (incl. bees)|تربية الحيوانات الأخرى (منها النحل)
0150|Mixed farming|الزراعة المختلطة
0161|Support activities for crop production|الأنشطة الداعمة للإنتاج النباتي
0162|Support activities for animal production|الأنشطة الداعمة للإنتاج الحيواني
0163|Post-harvest crop activities|أنشطة ما بعد الحصاد
0164|Seed processing for propagation|معالجة البذور للإكثار
0170|Hunting, trapping and related services|الصيد البري وخدماته
0210|Silviculture and forestry|زراعة الغابات وأنشطة الحراجة
0220|Logging|قطع الأخشاب
0230|Gathering of non-wood forest products|جمع المنتجات الحرجية غير الخشبية
0240|Support services to forestry|خدمات دعم الحراجة
0311|Marine fishing|صيد الأسماك البحرية
0312|Freshwater fishing|صيد أسماك المياه العذبة
0321|Marine aquaculture|الاستزراع المائي البحري
0322|Freshwater aquaculture|الاستزراع المائي في المياه العذبة
0510|Mining of hard coal|تعدين الفحم الحجري
0520|Mining of lignite|تعدين الليغنيت
0610|Extraction of crude petroleum|استخراج النفط الخام
0620|Extraction of natural gas|استخراج الغاز الطبيعي
0710|Mining of iron ores|تعدين خامات الحديد
0721|Mining of uranium and thorium ores|تعدين خامات اليورانيوم والثوريوم
0729|Mining of other non-ferrous metal ores (incl. gold, copper)|تعدين خامات المعادن غير الحديدية الأخرى (منها الذهب والنحاس)
0810|Quarrying of stone, sand and clay|استغلال محاجر الأحجار والرمل والطين
0891|Mining of chemical and fertilizer minerals (incl. phosphate)|تعدين المعادن الكيميائية ومعادن الأسمدة (منها الفوسفات)
0892|Extraction of peat|استخراج الخث
0893|Extraction of salt|استخراج الملح
0899|Other mining and quarrying n.e.c.|أنشطة التعدين واستغلال المحاجر الأخرى
0910|Support activities for petroleum and natural gas extraction|الأنشطة الداعمة لاستخراج النفط والغاز
0990|Support activities for other mining and quarrying|الأنشطة الداعمة للتعدين الآخر
1010|Processing and preserving of meat|تجهيز اللحوم وحفظها
1020|Processing and preserving of fish|تجهيز الأسماك وحفظها
1030|Processing and preserving of fruit and vegetables|تجهيز الفواكه والخضروات وحفظها
1040|Manufacture of vegetable and animal oils and fats|صناعة الزيوت والدهون النباتية والحيوانية
1050|Manufacture of dairy products|صناعة منتجات الألبان
1061|Manufacture of grain mill products|صناعة منتجات المطاحن
1062|Manufacture of starches and starch products|صناعة النشا ومنتجاته
1071|Manufacture of bakery products|صناعة منتجات المخابز
1072|Manufacture of sugar|صناعة السكر
1073|Manufacture of cocoa, chocolate and sugar confectionery|صناعة الكاكاو والشوكولاتة والحلويات السكرية
1074|Manufacture of macaroni, noodles and similar products|صناعة المعكرونة والشعيرية وما شابهها
1075|Manufacture of prepared meals and dishes|صناعة الوجبات والأطباق الجاهزة
1079|Manufacture of other food products n.e.c. (incl. dates processing, ice)|صناعة المنتجات الغذائية الأخرى (منها تعبئة التمور والثلج)
1080|Manufacture of prepared animal feeds|صناعة الأعلاف الحيوانية
1104|Manufacture of soft drinks and bottled waters|صناعة المشروبات الغازية والمياه المعبأة
1200|Manufacture of tobacco products|صناعة منتجات التبغ
1311|Preparation and spinning of textile fibres|تحضير الألياف النسيجية وغزلها
1312|Weaving of textiles|نسج المنسوجات
1313|Finishing of textiles|تجهيز المنسوجات وتشطيبها
1391|Manufacture of knitted and crocheted fabrics|صناعة الأقمشة المحبوكة
1392|Manufacture of made-up textile articles|صناعة المصنوعات النسيجية الجاهزة
1393|Manufacture of carpets and rugs|صناعة السجاد والبسط
1394|Manufacture of cordage, rope and netting|صناعة الحبال والشباك
1399|Manufacture of other textiles n.e.c.|صناعة المنسوجات الأخرى
1410|Manufacture of wearing apparel|صناعة الملابس
1420|Manufacture of articles of fur|صناعة المصنوعات الفرائية
1430|Manufacture of knitted apparel|صناعة الملابس المحبوكة
1511|Tanning and dressing of leather|دباغة الجلود وتهيئتها
1512|Manufacture of luggage, handbags and saddlery|صناعة الحقائب ومستلزمات السروج
1520|Manufacture of footwear|صناعة الأحذية
1610|Sawmilling and planing of wood|نشر الخشب وتسويته
1621|Manufacture of veneer sheets and wood-based panels|صناعة القشرة الخشبية والألواح
1622|Manufacture of builders' carpentry and joinery|صناعة منتجات النجارة للمباني
1623|Manufacture of wooden containers|صناعة العبوات الخشبية
1629|Manufacture of other wood products|صناعة المنتجات الخشبية الأخرى
1701|Manufacture of pulp, paper and paperboard|صناعة العجينة الورقية والورق والكرتون
1702|Manufacture of corrugated paper and containers|صناعة الورق المضلع والعبوات الورقية
1709|Manufacture of other articles of paper|صناعة المنتجات الورقية الأخرى
1811|Printing|الطباعة
1812|Service activities related to printing|الخدمات المتصلة بالطباعة
1820|Reproduction of recorded media|استنساخ الوسائط المسجلة
1910|Manufacture of coke oven products|صناعة منتجات أفران الكوك
1920|Manufacture of refined petroleum products|صناعة المنتجات النفطية المكررة
2011|Manufacture of basic chemicals|صناعة الكيماويات الأساسية
2012|Manufacture of fertilizers and nitrogen compounds|صناعة الأسمدة ومركبات النيتروجين
2013|Manufacture of plastics and synthetic rubber in primary forms|صناعة اللدائن والمطاط الصناعي في أشكالها الأولية
2021|Manufacture of pesticides and agrochemicals|صناعة المبيدات والكيماويات الزراعية
2022|Manufacture of paints, varnishes, inks and mastics|صناعة الدهانات والورنيش والأحبار والمعاجين
2023|Manufacture of soap, detergents, cleaning and toilet preparations|صناعة الصابون والمنظفات ومستحضرات التجميل
2029|Manufacture of other chemical products n.e.c.|صناعة المنتجات الكيميائية الأخرى
2030|Manufacture of man-made fibres|صناعة الألياف الاصطناعية
2100|Manufacture of pharmaceuticals and medicinal products|صناعة المستحضرات الصيدلانية والأدوية
2211|Manufacture of rubber tyres and tubes|صناعة الإطارات والأنابيب المطاطية
2219|Manufacture of other rubber products|صناعة المنتجات المطاطية الأخرى
2220|Manufacture of plastics products|صناعة المنتجات البلاستيكية
2310|Manufacture of glass and glass products|صناعة الزجاج ومنتجاته
2391|Manufacture of refractory products|صناعة المنتجات الحرارية
2392|Manufacture of clay building materials|صناعة مواد البناء الطينية
2393|Manufacture of other porcelain and ceramic products|صناعة منتجات البورسلين والخزف الأخرى
2394|Manufacture of cement, lime and plaster|صناعة الإسمنت والجير والجبس
2395|Manufacture of articles of concrete, cement and plaster|صناعة منتجات الخرسانة والإسمنت والجبس
2396|Cutting, shaping and finishing of stone|قطع الأحجار وتشكيلها وتشطيبها
2399|Manufacture of other non-metallic mineral products|صناعة منتجات المعادن اللافلزية الأخرى
2410|Manufacture of basic iron and steel|صناعة الحديد والصلب الأساسية
2420|Manufacture of basic precious and non-ferrous metals|صناعة المعادن الثمينة وغير الحديدية الأساسية
2431|Casting of iron and steel|سبك الحديد والصلب
2432|Casting of non-ferrous metals|سبك المعادن غير الحديدية
2511|Manufacture of structural metal products|صناعة المنتجات المعدنية الإنشائية
2512|Manufacture of tanks, reservoirs and containers of metal|صناعة الخزانات والصهاريج المعدنية
2513|Manufacture of steam generators|صناعة مولدات البخار
2520|Manufacture of weapons and ammunition|صناعة الأسلحة والذخائر
2591|Forging, pressing, stamping and roll-forming of metal|طرق المعادن وكبسها وختمها ودرفلتها
2592|Treatment and coating of metals; machining|معالجة المعادن وطلاؤها؛ التشغيل الآلي
2593|Manufacture of cutlery, hand tools and general hardware|صناعة أدوات المائدة والعدد اليدوية والخردوات
2599|Manufacture of other fabricated metal products|صناعة المنتجات المعدنية المشكلة الأخرى
2610|Manufacture of electronic components and boards|صناعة المكونات واللوحات الإلكترونية
2620|Manufacture of computers and peripheral equipment|صناعة الحواسيب وملحقاتها
2630|Manufacture of communication equipment|صناعة معدات الاتصالات
2640|Manufacture of consumer electronics|صناعة الإلكترونيات الاستهلاكية
2651|Manufacture of measuring, testing and control equipment|صناعة معدات القياس والاختبار والتحكم
2652|Manufacture of watches and clocks|صناعة الساعات
2660|Manufacture of irradiation and electromedical equipment|صناعة معدات الإشعاع والأجهزة الطبية الكهربائية
2670|Manufacture of optical instruments and photographic equipment|صناعة الأجهزة البصرية ومعدات التصوير
2680|Manufacture of magnetic and optical media|صناعة الوسائط المغناطيسية والبصرية
2710|Manufacture of electric motors, generators and transformers|صناعة المحركات والمولدات والمحولات الكهربائية
2720|Manufacture of batteries and accumulators|صناعة البطاريات والمراكم
2731|Manufacture of fibre optic cables|صناعة كابلات الألياف البصرية
2732|Manufacture of other electronic and electric wires and cables|صناعة الأسلاك والكابلات الكهربائية الأخرى
2733|Manufacture of wiring devices|صناعة أجهزة التوصيلات الكهربائية
2740|Manufacture of electric lighting equipment|صناعة معدات الإنارة الكهربائية
2750|Manufacture of domestic appliances (incl. air conditioners)|صناعة الأجهزة المنزلية (منها المكيفات)
2790|Manufacture of other electrical equipment|صناعة المعدات الكهربائية الأخرى
2811|Manufacture of engines and turbines|صناعة المحركات والتوربينات
2812|Manufacture of fluid power equipment|صناعة معدات القدرة الهيدروليكية
2813|Manufacture of other pumps, compressors, taps and valves|صناعة المضخات والضواغط والصمامات
2814|Manufacture of bearings, gears and driving elements|صناعة المحامل والتروس وعناصر الإدارة
2815|Manufacture of ovens, furnaces and furnace burners|صناعة الأفران والمواقد
2816|Manufacture of lifting and handling equipment|صناعة معدات الرفع والمناولة
2817|Manufacture of office machinery|صناعة الآلات المكتبية
2818|Manufacture of power-driven hand tools|صناعة العدد اليدوية الكهربائية
2819|Manufacture of other general-purpose machinery (incl. cooling)|صناعة الآلات العامة الأخرى (منها معدات التبريد)
2821|Manufacture of agricultural and forestry machinery|صناعة الآلات الزراعية
2822|Manufacture of metal-forming machinery and machine tools|صناعة آلات تشكيل المعادن والعدد الآلية
2823|Manufacture of machinery for metallurgy|صناعة آلات التعدين والفلزات
2824|Manufacture of mining, quarrying and construction machinery|صناعة آلات التعدين والمحاجر والتشييد
2825|Manufacture of food, beverage and tobacco processing machinery|صناعة آلات تجهيز الأغذية والمشروبات
2826|Manufacture of textile, apparel and leather machinery|صناعة آلات النسيج والملابس والجلود
2829|Manufacture of other special-purpose machinery|صناعة الآلات الخاصة الأخرى
2910|Manufacture of motor vehicles|صناعة المركبات ذات المحركات
2920|Manufacture of vehicle bodies, trailers and semi-trailers|صناعة هياكل المركبات والمقطورات
2930|Manufacture of parts and accessories for motor vehicles|صناعة قطع غيار المركبات وملحقاتها
3011|Building of ships and floating structures|بناء السفن والهياكل العائمة
3012|Building of pleasure and sporting boats|بناء قوارب النزهة والرياضة
3020|Manufacture of railway locomotives and rolling stock|صناعة القاطرات وعربات السكك الحديدية
3030|Manufacture of air and spacecraft|صناعة الطائرات والمركبات الفضائية
3040|Manufacture of military fighting vehicles|صناعة المركبات العسكرية القتالية
3091|Manufacture of motorcycles|صناعة الدراجات النارية
3092|Manufacture of bicycles and invalid carriages|صناعة الدراجات الهوائية وعربات المعاقين
3099|Manufacture of other transport equipment|صناعة معدات النقل الأخرى
3100|Manufacture of furniture|صناعة الأثاث
3211|Manufacture of jewellery|صناعة المجوهرات
3212|Manufacture of imitation jewellery|صناعة المجوهرات المقلدة
3220|Manufacture of musical instruments|صناعة الآلات الموسيقية
3230|Manufacture of sports goods|صناعة الأدوات الرياضية
3240|Manufacture of games and toys|صناعة الألعاب
3250|Manufacture of medical and dental instruments and supplies|صناعة الأدوات والمستلزمات الطبية وطب الأسنان
3290|Other manufacturing n.e.c.|الصناعات التحويلية الأخرى
3311|Repair of fabricated metal products|إصلاح المنتجات المعدنية المشكلة
3312|Repair of machinery|إصلاح الآلات
3313|Repair of electronic and optical equipment|إصلاح المعدات الإلكترونية والبصرية
3314|Repair of electrical equipment|إصلاح المعدات الكهربائية
3315|Repair of transport equipment (except vehicles)|إصلاح معدات النقل عدا المركبات
3319|Repair of other equipment|إصلاح المعدات الأخرى
3320|Installation of industrial machinery and equipment|تركيب الآلات والمعدات الصناعية
3510|Electric power generation, transmission and distribution|توليد الكهرباء ونقلها وتوزيعها
3520|Manufacture of gas; distribution of gaseous fuels|صناعة الغاز وتوزيع الوقود الغازي
3530|Steam and air conditioning supply (incl. district cooling)|إمدادات البخار والتكييف (منها التبريد المركزي)
3600|Water collection, treatment and supply (incl. desalination)|تجميع المياه ومعالجتها وتوزيعها (منها التحلية)
3700|Sewerage|الصرف الصحي
3811|Collection of non-hazardous waste|جمع النفايات غير الخطرة
3812|Collection of hazardous waste|جمع النفايات الخطرة
3821|Treatment and disposal of non-hazardous waste|معالجة النفايات غير الخطرة والتخلص منها
3822|Treatment and disposal of hazardous waste|معالجة النفايات الخطرة والتخلص منها
3830|Materials recovery (recycling)|استرجاع المواد (إعادة التدوير)
3900|Remediation and other waste management services|أنشطة المعالجة وخدمات إدارة النفايات الأخرى
4100|Construction of buildings|تشييد المباني
4210|Construction of roads and railways|إنشاء الطرق والسكك الحديدية
4220|Construction of utility projects|إنشاء مشاريع المرافق
4290|Construction of other civil engineering projects|إنشاء مشاريع الهندسة المدنية الأخرى
4311|Demolition|الهدم
4312|Site preparation|تجهيز المواقع
4321|Electrical installation|التمديدات الكهربائية
4322|Plumbing, heat and air-conditioning installation|تمديدات السباكة والتدفئة والتكييف
4329|Other construction installation|التركيبات الإنشائية الأخرى
4330|Building completion and finishing|إكمال المباني وتشطيبها
4390|Other specialized construction activities|أنشطة التشييد المتخصصة الأخرى
4510|Sale of motor vehicles|بيع المركبات
4520|Maintenance and repair of motor vehicles|صيانة المركبات وإصلاحها
4530|Sale of motor vehicle parts and accessories|بيع قطع غيار المركبات وملحقاتها
4540|Sale, maintenance and repair of motorcycles|بيع الدراجات النارية وصيانتها
4610|Wholesale on a fee or contract basis|البيع بالجملة مقابل رسم أو عقد
4620|Wholesale of agricultural raw materials and live animals|البيع بالجملة للمواد الخام الزراعية والحيوانات الحية
4630|Wholesale of food, beverages and tobacco|البيع بالجملة للأغذية والمشروبات والتبغ
4641|Wholesale of textiles, clothing and footwear|البيع بالجملة للمنسوجات والملابس والأحذية
4649|Wholesale of other household goods|البيع بالجملة للسلع المنزلية الأخرى
4651|Wholesale of computers and software|البيع بالجملة للحواسيب والبرمجيات
4652|Wholesale of electronic and telecom equipment|البيع بالجملة لمعدات الإلكترونيات والاتصالات
4653|Wholesale of agricultural machinery|البيع بالجملة للآلات الزراعية
4659|Wholesale of other machinery and equipment|البيع بالجملة للآلات والمعدات الأخرى
4661|Wholesale of fuels|البيع بالجملة للوقود
4662|Wholesale of metals and metal ores|البيع بالجملة للمعادن وخاماتها
4663|Wholesale of construction materials and hardware|البيع بالجملة لمواد البناء والأدوات الصحية
4669|Wholesale of waste, scrap and other products|البيع بالجملة للخردة والمنتجات الأخرى
4690|Non-specialized wholesale trade|البيع بالجملة غير المتخصص
4711|Retail in non-specialized stores, food predominating|البيع بالتجزئة في المتاجر غير المتخصصة يغلب عليها الغذاء
4719|Other retail sale in non-specialized stores|البيع بالتجزئة الآخر في المتاجر غير المتخصصة
4721|Retail sale of food in specialized stores|البيع بالتجزئة للأغذية في متاجر متخصصة
4722|Retail sale of beverages in specialized stores|البيع بالتجزئة للمشروبات في متاجر متخصصة
4723|Retail sale of tobacco products|البيع بالتجزئة لمنتجات التبغ
4730|Retail sale of automotive fuel|البيع بالتجزئة لوقود المركبات
4741|Retail sale of computers, software and telecom equipment|البيع بالتجزئة للحواسيب والجوالات ومعدات الاتصالات
4742|Retail sale of audio and video equipment|البيع بالتجزئة للأجهزة الصوتية والمرئية
4751|Retail sale of textiles|البيع بالتجزئة للأقمشة
4752|Retail sale of hardware, paints and glass|البيع بالتجزئة للأدوات والدهانات والزجاج
4753|Retail sale of carpets, rugs, wall and floor coverings|البيع بالتجزئة للسجاد وأغطية الجدران والأرضيات
4759|Retail sale of electrical household appliances, furniture and lighting|البيع بالتجزئة للأجهزة المنزلية والأثاث والإنارة
4761|Retail sale of books, newspapers and stationery|البيع بالتجزئة للكتب والصحف والقرطاسية
4762|Retail sale of music and video recordings|البيع بالتجزئة للتسجيلات الصوتية والمرئية
4763|Retail sale of sporting equipment|البيع بالتجزئة للأدوات الرياضية
4764|Retail sale of games and toys|البيع بالتجزئة للألعاب
4771|Retail sale of clothing, footwear and leather articles|البيع بالتجزئة للملابس والأحذية والمصنوعات الجلدية
4772|Retail sale of pharmaceutical and medical goods, cosmetics|البيع بالتجزئة للأدوية والمستلزمات الطبية ومستحضرات التجميل
4773|Other retail sale of new goods (incl. perfumes, watches, jewellery, gifts)|البيع بالتجزئة للسلع الجديدة الأخرى (منها العطور والساعات والمجوهرات والهدايا)
4774|Retail sale of second-hand goods|البيع بالتجزئة للسلع المستعملة
4781|Retail sale via stalls and markets of food|البيع بالتجزئة للأغذية في الأكشاك والأسواق
4782|Retail sale via stalls and markets of textiles and clothing|البيع بالتجزئة للأقمشة والملابس في الأكشاك والأسواق
4789|Retail sale via stalls and markets of other goods|البيع بالتجزئة للسلع الأخرى في الأكشاك والأسواق
4791|Retail sale via mail order houses or the internet|البيع بالتجزئة عبر الإنترنت والطلب البريدي
4799|Other retail sale not in stores, stalls or markets|البيع بالتجزئة الآخر خارج المتاجر
4911|Passenger rail transport, interurban|النقل بالسكك الحديدية للركاب بين المدن
4912|Freight rail transport|نقل البضائع بالسكك الحديدية
4921|Urban and suburban passenger land transport|النقل البري للركاب داخل المدن وضواحيها
4922|Other passenger land transport (incl. taxis, buses)|النقل البري الآخر للركاب (منه الأجرة والحافلات)
4923|Freight transport by road|نقل البضائع على الطرق
4930|Transport via pipeline|النقل عبر خطوط الأنابيب
5011|Sea and coastal passenger water transport|النقل البحري والساحلي للركاب
5012|Sea and coastal freight water transport|النقل البحري والساحلي للبضائع
5021|Inland passenger water transport|النقل المائي الداخلي للركاب
5022|Inland freight water transport|النقل المائي الداخلي للبضائع
5110|Passenger air transport|النقل الجوي للركاب
5120|Freight air transport|النقل الجوي للبضائع
5210|Warehousing and storage (incl. cold storage)|التخزين والمستودعات (منها التبريد)
5221|Service activities incidental to land transportation|الخدمات المتصلة بالنقل البري
5222|Service activities incidental to water transportation|الخدمات المتصلة بالنقل المائي
5223|Service activities incidental to air transportation|الخدمات المتصلة بالنقل الجوي
5224|Cargo handling|مناولة البضائع
5229|Other transportation support activities (incl. customs clearance)|أنشطة دعم النقل الأخرى (منها التخليص الجمركي)
5310|Postal activities|أنشطة البريد
5320|Courier and delivery activities|أنشطة البريد السريع والتوصيل
5510|Short-term accommodation (hotels, serviced apartments)|الإقامة قصيرة المدى (الفنادق والشقق المخدومة)
5520|Camping grounds and recreational vehicle parks|المخيمات ومواقف المركبات الترفيهية
5590|Other accommodation (incl. workers' and student housing)|الإقامة الأخرى (منها سكن العمال والطلاب)
5610|Restaurants and mobile food service|المطاعم وخدمات الطعام المتنقلة
5621|Event catering|تموين الحفلات والمناسبات
5629|Other food service activities (contract catering)|أنشطة خدمات الطعام الأخرى (الإعاشة)
5630|Beverage serving activities (cafés, juice shops)|تقديم المشروبات (المقاهي ومحلات العصير)
5811|Book publishing|نشر الكتب
5812|Publishing of directories and mailing lists|نشر الأدلة وقوائم العناوين
5813|Publishing of newspapers, journals and periodicals|نشر الصحف والمجلات والدوريات
5819|Other publishing activities|أنشطة النشر الأخرى
5820|Software publishing|نشر البرمجيات
5911|Motion picture, video and TV programme production|إنتاج الأفلام والفيديو والبرامج التلفزيونية
5912|Post-production activities|أنشطة ما بعد الإنتاج
5913|Motion picture, video and TV programme distribution|توزيع الأفلام والفيديو والبرامج
5914|Motion picture projection (cinemas)|عرض الأفلام (دور السينما)
5920|Sound recording and music publishing|التسجيل الصوتي ونشر الموسيقى
6010|Radio broadcasting|البث الإذاعي
6020|Television programming and broadcasting|البرمجة والبث التلفزيوني
6110|Wired telecommunications|الاتصالات السلكية
6120|Wireless telecommunications|الاتصالات اللاسلكية
6130|Satellite telecommunications|الاتصالات الفضائية
6190|Other telecommunications activities|أنشطة الاتصالات الأخرى
6201|Computer programming|البرمجة الحاسوبية
6202|IT consultancy and facilities management|الاستشارات الحاسوبية وإدارة المرافق الحاسوبية
6209|Other IT and computer service activities|أنشطة الخدمات الحاسوبية الأخرى
6311|Data processing, hosting and data centres|معالجة البيانات والاستضافة ومراكز البيانات
6312|Web portals|بوابات الويب
6391|News agency activities|أنشطة وكالات الأنباء
6399|Other information service activities|أنشطة خدمات المعلومات الأخرى
6419|Other monetary intermediation (banks)|الوساطة النقدية الأخرى (البنوك)
6420|Activities of holding companies|أنشطة الشركات القابضة
6430|Trusts, funds and similar financial entities|الصناديق والكيانات المالية المماثلة
6491|Financial leasing|التأجير التمويلي
6492|Other credit granting (finance companies)|منح الائتمان الآخر (شركات التمويل)
6499|Other financial service activities|أنشطة الخدمات المالية الأخرى
6511|Life insurance (family takaful)|التأمين على الحياة (التكافل العائلي)
6512|Non-life insurance|التأمين على غير الحياة
6520|Reinsurance|إعادة التأمين
6530|Pension funding|صناديق التقاعد
6611|Administration of financial markets|إدارة الأسواق المالية
6612|Security and commodity contracts brokerage|الوساطة في الأوراق المالية والسلع
6619|Other activities auxiliary to financial services (incl. money exchange)|الأنشطة المساعدة للخدمات المالية (منها الصرافة)
6621|Risk and damage evaluation|تقييم المخاطر والأضرار
6622|Activities of insurance agents and brokers|أنشطة وكلاء التأمين ووسطائه
6629|Other activities auxiliary to insurance|الأنشطة المساعدة للتأمين الأخرى
6630|Fund management activities|أنشطة إدارة الصناديق
6810|Real estate activities with own or leased property|الأنشطة العقارية في الممتلكات المملوكة أو المؤجرة
6820|Real estate activities on a fee or contract basis|الأنشطة العقارية مقابل رسم أو عقد (الوساطة)
6910|Legal activities|الأنشطة القانونية (المحاماة)
6920|Accounting, bookkeeping, auditing and tax consultancy|المحاسبة والتدقيق والاستشارات الضريبية
7010|Activities of head offices|أنشطة المكاتب الرئيسية
7020|Management consultancy activities|الاستشارات الإدارية
7110|Architectural and engineering activities|الأنشطة المعمارية والهندسية
7120|Technical testing and analysis|الاختبارات والتحاليل الفنية
7210|R&D on natural sciences and engineering|البحث والتطوير في العلوم الطبيعية والهندسة
7220|R&D on social sciences and humanities|البحث والتطوير في العلوم الاجتماعية والإنسانية
7310|Advertising|الدعاية والإعلان
7320|Market research and public opinion polling|أبحاث السوق واستطلاعات الرأي
7410|Specialized design activities|أنشطة التصميم المتخصصة
7420|Photographic activities|أنشطة التصوير الفوتوغرافي
7490|Other professional, scientific and technical activities (incl. translation)|الأنشطة المهنية والعلمية الأخرى (منها الترجمة)
7500|Veterinary activities|الأنشطة البيطرية
7710|Renting and leasing of motor vehicles|تأجير المركبات
7721|Renting of recreational and sports goods|تأجير السلع الترفيهية والرياضية
7722|Renting of video tapes and disks|تأجير أشرطة وأقراص الفيديو
7729|Renting of other personal and household goods|تأجير السلع الشخصية والمنزلية الأخرى
7730|Renting of other machinery, equipment and goods|تأجير الآلات والمعدات الأخرى
7740|Leasing of intellectual property|تأجير الملكية الفكرية
7810|Activities of employment placement agencies|أنشطة وكالات التوظيف
7820|Temporary employment agency activities|أنشطة وكالات التوظيف المؤقت
7830|Other human resources provision (manpower companies)|توفير الموارد البشرية الأخرى (شركات الاستقدام)
7911|Travel agency activities|أنشطة وكالات السفر
7912|Tour operator activities|أنشطة منظمي الرحلات
7990|Other reservation service activities (incl. Hajj and Umrah services)|خدمات الحجز الأخرى (منها خدمات الحج والعمرة)
8010|Private security activities|أنشطة الحراسات الأمنية الخاصة
8020|Security systems service activities|خدمات أنظمة الأمن
8030|Investigation activities|أنشطة التحري
8110|Combined facilities support activities|أنشطة الدعم المتكاملة للمرافق
8121|General cleaning of buildings|التنظيف العام للمباني
8129|Other building and industrial cleaning activities|أنشطة التنظيف الأخرى للمباني والمنشآت الصناعية
8130|Landscape care and maintenance|تنسيق الحدائق وصيانتها
8211|Combined office administrative service activities|الخدمات الإدارية المكتبية المتكاملة
8219|Photocopying and document preparation (incl. government services offices)|التصوير وإعداد المستندات (منها مكاتب الخدمات العامة)
8220|Activities of call centres|أنشطة مراكز الاتصال
8230|Organization of conventions and trade shows|تنظيم المؤتمرات والمعارض
8291|Collection agencies and credit bureaus|وكالات التحصيل ومكاتب الائتمان
8292|Packaging activities|أنشطة التعبئة والتغليف
8299|Other business support service activities|أنشطة خدمات دعم الأعمال الأخرى
8510|Pre-primary and primary education|التعليم ما قبل الابتدائي والابتدائي
8521|General secondary education|التعليم الثانوي العام
8522|Technical and vocational secondary education|التعليم الثانوي الفني والمهني
8530|Higher education|التعليم العالي
8541|Sports and recreation education|التعليم الرياضي والترفيهي
8542|Cultural education|التعليم الثقافي
8549|Other education n.e.c. (incl. training centres, driving schools)|التعليم الآخر (منه مراكز التدريب ومدارس القيادة)
8550|Educational support activities|أنشطة دعم التعليم
8610|Hospital activities|أنشطة المستشفيات
8620|Medical and dental practice activities|أنشطة العيادات الطبية وعيادات الأسنان
8690|Other human health activities (incl. labs, radiology, home care)|أنشطة الصحة البشرية الأخرى (منها المختبرات والأشعة والرعاية المنزلية)
8710|Residential nursing care facilities|مرافق الرعاية التمريضية الإيوائية
8720|Residential care for mental health and substance abuse|الرعاية الإيوائية للصحة النفسية والإدمان
8730|Residential care for the elderly and disabled|الرعاية الإيوائية لكبار السن وذوي الإعاقة
8790|Other residential care activities|أنشطة الرعاية الإيوائية الأخرى
8810|Social work without accommodation for the elderly and disabled|العمل الاجتماعي بدون إيواء لكبار السن وذوي الإعاقة
8890|Other social work without accommodation (incl. child day care)|العمل الاجتماعي الآخر بدون إيواء (منه حضانات الأطفال)
9000|Creative, arts and entertainment activities|الأنشطة الإبداعية والفنون والترفيه
9101|Library and archives activities|أنشطة المكتبات ودور المحفوظات
9102|Museums and historical sites|المتاحف والمواقع التاريخية
9103|Botanical and zoological gardens and nature reserves|الحدائق النباتية والحيوانية والمحميات
9311|Operation of sports facilities|تشغيل المرافق الرياضية
9312|Activities of sports clubs|أنشطة الأندية الرياضية
9319|Other sports activities|الأنشطة الرياضية الأخرى
9321|Activities of amusement and theme parks|أنشطة مدن الملاهي والحدائق الترفيهية
9329|Other amusement and recreation activities|أنشطة التسلية والترفيه الأخرى
9411|Activities of business and employers membership organizations|أنشطة منظمات الأعمال وأصحاب العمل
9412|Activities of professional membership organizations|أنشطة المنظمات المهنية
9491|Activities of religious organizations|أنشطة المنظمات الدينية
9499|Activities of other membership organizations (incl. charities)|أنشطة المنظمات الأخرى (منها الجمعيات الخيرية)
9511|Repair of computers and peripheral equipment|إصلاح الحواسيب وملحقاتها
9512|Repair of communication equipment (incl. mobile phones)|إصلاح معدات الاتصالات (منها الجوالات)
9521|Repair of consumer electronics|إصلاح الإلكترونيات الاستهلاكية
9522|Repair of household appliances and home and garden equipment|إصلاح الأجهزة المنزلية ومعدات الحدائق
9523|Repair of footwear and leather goods|إصلاح الأحذية والمصنوعات الجلدية
9524|Repair of furniture and home furnishings|إصلاح الأثاث والمفروشات
9529|Repair of other personal and household goods (incl. tailoring)|إصلاح السلع الشخصية والمنزلية الأخرى (منها الخياطة)
9601|Washing and dry-cleaning of textile and fur products|غسيل المنسوجات وكيّها
9602|Hairdressing and other beauty treatment|الحلاقة والتجميل
9603|Funeral and related activities|أنشطة تجهيز الموتى
9609|Other personal service activities n.e.c.|أنشطة الخدمات الشخصية الأخرى
"""

# Cost profile per class: explicit overrides first, then by division
PROFILE_BY_CLASS = {
    "0113": "greenhouse", "0119": "fodder", "0111": "fodder", "0122": "dates", "0141": "dairy_farm", "0146": "poultry",
    "0144": "livestock", "0143": "livestock", "0142": "livestock", "0149": "livestock", "0321": "fish_farm", "0322": "fish_farm",
    "0610": "petrochemicals", "0620": "petrochemicals", "0910": "mining_quarry",
    "1010": "meat_poultry_proc", "1050": "dairy", "1071": "bakery_ind", "1104": "beverages", "1079": "food_processing",
    "1701": "paper", "1702": "paper", "1709": "paper", "1811": "printing", "1812": "printing", "1820": "printing",
    "1910": "petrochemicals", "1920": "petrochemicals", "2011": "chemicals", "2012": "fertilizers", "2013": "petrochemicals",
    "2022": "paints", "2023": "detergents", "2100": "pharma", "2220": "plastics", "2211": "plastics", "2219": "plastics",
    "2310": "glass", "2391": "ceramics", "2392": "ceramics", "2393": "ceramics", "2394": "cement", "2395": "concrete",
    "2396": "concrete", "2399": "ceramics", "2410": "steel", "2431": "steel", "2420": "aluminium", "2432": "aluminium",
    "2732": "electrical_eq", "2731": "electrical_eq", "2710": "electrical_eq", "2910": "auto_parts_ind", "2920": "auto_parts_ind",
    "2930": "auto_parts_ind", "3100": "furniture_ind", "1622": "furniture_ind", "1629": "furniture_ind", "3830": "recycling",
    "3510": "utility_services", "3520": "utility_services", "3530": "utility_services", "3600": "utility_services", "3700": "utility_services",
    "4510": "car_showroom", "4520": "car_workshop", "4530": "auto_parts", "4540": "car_workshop",
    "4711": "supermarket", "4719": "supermarket", "4721": "butcher", "4722": "grocery", "4723": "grocery", "4730": "fuel_station",
    "4741": "telecom_shop", "4742": "electronics", "4751": "clothing", "4752": "building_materials", "4753": "furniture_shop",
    "4759": "furniture_shop", "4761": "clothing", "4762": "electronics", "4763": "clothing", "4764": "clothing", "4771": "clothing",
    "4772": "pharmacy", "4773": "optics_perfume", "4774": "furniture_shop", "4781": "butcher", "4782": "clothing", "4789": "clothing",
    "4791": "logistics", "4799": "grocery",
    "4923": "transport", "4921": "transport", "4922": "car_rental", "5210": "cold_storage", "5224": "logistics", "5229": "logistics",
    "5310": "logistics", "5320": "logistics", "5221": "logistics", "5222": "logistics", "5223": "logistics",
    "5510": "hotel", "5520": "furnished_apts", "5590": "furnished_apts", "5610": "restaurant", "5621": "catering", "5629": "catering",
    "5630": "cafe", "5914": "entertainment",
    "6110": "telecom_operator", "6120": "telecom_operator", "6130": "telecom_operator", "6190": "telecom_operator",
    "6201": "it_company", "6202": "it_company", "6209": "it_company", "5820": "it_company", "6311": "data_center", "6312": "it_company",
    "6810": "mall", "6820": "real_estate", "7710": "car_rental", "7810": "security_cleaning", "7820": "security_cleaning",
    "7830": "security_cleaning", "8010": "security_cleaning", "8110": "security_cleaning", "8121": "security_cleaning",
    "8129": "security_cleaning", "8130": "security_cleaning", "8292": "printing",
    "8510": "private_school", "8521": "private_school", "8522": "private_school", "8530": "private_school",
    "8610": "hospital", "8620": "clinic", "8690": "lab_radiology", "7500": "clinic",
    "9311": "gym", "9312": "gym", "9319": "gym", "9321": "entertainment", "9329": "entertainment", "9000": "entertainment",
    "9601": "laundry", "9602": "salon", "9529": "salon", "9512": "telecom_shop", "9511": "telecom_shop", "9521": "car_workshop",
    "9522": "car_workshop", "9499": "charity", "9491": "charity",
}
PROFILE_BY_DIV = {
    "01": "greenhouse", "02": "fodder", "03": "fish_farm", "05": "mining_quarry", "06": "petrochemicals", "07": "mining_quarry",
    "08": "mining_quarry", "09": "mining_quarry", "10": "food_processing", "11": "beverages", "12": "food_processing",
    "13": "textiles", "14": "textiles", "15": "textiles", "16": "furniture_ind", "17": "paper", "18": "printing",
    "19": "petrochemicals", "20": "chemicals", "21": "pharma", "22": "plastics", "23": "ceramics", "24": "steel",
    "25": "metal_products", "26": "electrical_eq", "27": "electrical_eq", "28": "machinery", "29": "auto_parts_ind",
    "30": "machinery", "31": "furniture_ind", "32": "metal_products", "33": "machinery", "35": "utility_services",
    "36": "utility_services", "37": "utility_services", "38": "recycling", "39": "recycling", "41": "contracting",
    "42": "contracting", "43": "contracting", "45": "auto_parts", "46": "wholesale", "47": "grocery", "49": "transport",
    "50": "transport", "51": "transport", "52": "logistics", "53": "logistics", "55": "hotel", "56": "restaurant",
    "58": "consulting", "59": "consulting", "60": "consulting", "61": "telecom_operator", "62": "it_company", "63": "it_company",
    "64": "bank_branch", "65": "bank_branch", "66": "bank_branch", "68": "real_estate", "69": "consulting", "70": "consulting",
    "71": "consulting", "72": "consulting", "73": "consulting", "74": "consulting", "75": "clinic", "77": "car_rental",
    "78": "security_cleaning", "79": "consulting", "80": "security_cleaning", "81": "security_cleaning", "82": "consulting",
    "85": "training", "86": "clinic", "87": "clinic", "88": "training", "90": "entertainment", "91": "entertainment",
    "93": "entertainment", "94": "charity", "95": "car_workshop", "96": "salon",
}

# Nitaqat activity (1-41, HRSD Annex 1) per class
def nitaqat(code):
    d, c = int(code[:2]), code
    if d <= 3: return 1
    if c in ("0610", "0620", "0910", "0990") or d == 6: return 2
    if d == 7: return 3
    if c == "0810": return 5
    if d in (5, 8): return 4
    if 10 <= d <= 33: return 7
    if d in (35, 36, 37): return 6
    if d in (38, 39): return 9
    if 41 <= d <= 43: return 8
    if c == "4730": return 39
    if c in ("4741", "9512"): return 14
    if c == "4773": return 12
    if c in ("4742", "4761", "4762", "4763", "4764", "4771", "4782", "4789"): return 13
    if c == "4772": return 37
    if d in (45, 46, 47): return 11
    if d in (49, 52): return 22
    if d in (50, 51): return 23
    if d == 53: return 16
    if d == 55: return 38
    if c == "5610": return 24
    if c in ("5621", "5629"): return 27
    if c == "5630": return 26
    if d in (58, 59, 60): return 30
    if d == 61: return 15
    if c == "6311": return 17
    if d in (62, 63): return 21
    if d in (64, 65, 66): return 29
    if d in (78, 80) and c != "8020": return 28
    if c == "8020": return 30
    if c in ("8121", "8129", "9601"): return 10
    if c in ("8110", "8130"): return 9
    if d == 79: return 38
    if d in (68, 69, 70, 71, 72, 73, 74, 77, 82): return 30
    if c == "7500": return 37
    if c == "8510": return 35
    if c in ("8521", "8522"): return 40
    if c == "8530": return 33
    if d == 85: return 30
    if d == 86: return 37
    if d in (87, 88): return 31
    if d in (90, 91, 93): return 38
    if d == 94: return 31
    if d in (95, 96): return 32
    return 41

def main():
    acts = {r["id"]: r for r in csv.DictReader(open(RAW / "activity_catalog.csv", encoding="utf-8"))}
    out = []
    for line in CLASSES.strip().splitlines():
        code, en, ar = line.split("|")
        prof = PROFILE_BY_CLASS.get(code) or PROFILE_BY_DIV[code[:2]]
        assert prof in acts, (code, prof)
        sec = section(code)
        out.append({"code": code, "section": sec, "section_ar": SECTIONS[sec][0], "section_en": SECTIONS[sec][1],
                    "name_ar": ar, "name_en": en, "profile": prof, "group": acts[prof]["group"],
                    "tariff": acts[prof]["tariff"], "nitaqat_id": nitaqat(code)})
    with open(RAW / "isic4_classes.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(len(out), "classes")

if __name__ == "__main__":
    main()
