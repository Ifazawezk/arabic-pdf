"""Source text for the synthetic corpus.

Every PDF in ``corpus/`` is rendered from the blocks below, so the ground
truth is exact. All text here was written for this project and is released
under the same MIT license as the code.

Block kinds:
    ("h1", text) / ("h2", text)  heading
    ("p", text)                  paragraph
    ("table", rows)              table, rows[0] is the header row, cells in logical order
    ("page",)                    page break (only used by multi-page documents)
"""

PARAGRAPHS = {
    "weather": (
        "تشهد مدينة الدوحة في فصل الصيف ارتفاعا كبيرا في درجات الحرارة، إذ تتجاوز في بعض الأيام "
        "خمسا وأربعين درجة مئوية. ويحرص السكان على تجنب الخروج في ساعات الظهيرة، فيما تنتقل "
        "الأنشطة الرياضية والاجتماعية إلى المساء حين تصبح الأجواء ألطف قليلا."
    ),
    "libraries": (
        "تعد المكتبات العامة من أهم المؤسسات الثقافية في أي مجتمع، فهي لا تقدم الكتب فقط، بل توفر "
        "مساحات هادئة للدراسة والبحث، وتنظم ورشا للأطفال والشباب. وقد أصبحت كثير من المكتبات اليوم "
        "تتيح الكتب الإلكترونية والدوريات العلمية عبر الإنترنت لكل من يحمل بطاقة عضوية."
    ),
    "programming": (
        "لا يحتاج تعلم البرمجة إلى شهادة جامعية في البداية، ولكنه يحتاج إلى صبر وممارسة يومية. ينصح "
        "كثير من المدربين بالبدء بمشروع صغير يحل مشكلة حقيقية، ثم التوسع فيه تدريجيا، لأن التعلم من "
        "الأخطاء العملية أسرع بكثير من قراءة الكتب وحدها."
    ),
    "pearls": (
        "اعتمد أهل الخليج قديما على الغوص بحثا عن اللؤلؤ، وكانت رحلات الغوص تستمر عدة أشهر في عرض "
        "البحر. وكان الغواصون يعملون في ظروف قاسية، ولا يملكون من الأدوات إلا الحبال والأوزان ومشبكا "
        "صغيرا يغلق به الأنف. ومع ظهور اللؤلؤ الصناعي تراجعت هذه المهنة حتى كادت تختفي."
    ),
    "calligraphy": (
        "يتميز الخط العربي بتنوع أشكاله، فمنها النسخ والثلث والديواني والكوفي والرقعة. ولكل خط قواعده "
        "الخاصة في أطوال الحروف واتصالها، ولذلك يقضي الخطاط سنوات طويلة في التدريب قبل أن يحصل على "
        "إجازة من أستاذه تسمح له بتعليم غيره."
    ),
    "desert": (
        "رغم قسوة البيئة الصحراوية، تعيش فيها كائنات كثيرة تكيفت مع قلة الماء وشدة الحرارة. فبعض "
        "النباتات تمد جذورها عميقا في الرمال، وبعض الحيوانات لا تخرج من جحورها إلا ليلا، بينما تحصل "
        "حيوانات أخرى على حاجتها من الماء من الغذاء الذي تأكله."
    ),
    "metro": (
        "ساهم مترو الدوحة في تخفيف الازدحام على الطرق الرئيسية، خصوصا في أوقات الذروة. ويربط المترو "
        "بين المطار ووسط المدينة والمناطق السكنية والملاعب، كما ترتبط محطاته بحافلات صغيرة تنقل الركاب "
        "إلى الأحياء القريبة دون الحاجة إلى سيارة خاصة."
    ),
    "coffee": (
        "للقهوة العربية مكانة خاصة في الضيافة، فهي أول ما يقدم للضيف عند وصوله. وتحمص حبوب البن "
        "تحميصا خفيفا، ثم تطحن وتغلى مع الهيل وأحيانا مع الزعفران. ومن العادات المعروفة أن يهز الضيف "
        "الفنجان إذا اكتفى، فيفهم المضيف أنه لا يريد المزيد."
    ),
    "health": (
        "أصبح بإمكان المرضى اليوم حجز المواعيد الطبية وتجديد الوصفات عبر تطبيقات الهاتف، دون الحاجة "
        "إلى الانتظار في المراكز الصحية. ويرى الأطباء أن هذه الخدمات تختصر الوقت، لكنها لا تغني عن "
        "الزيارة المباشرة في الحالات التي تحتاج إلى فحص دقيق."
    ),
    "reading": (
        "تشير دراسات كثيرة إلى أن القراءة المنتظمة تحسن التركيز وتوسع المفردات، وتساعد على النوم إذا "
        "كانت قبل الخلود إلى الفراش بعيدا عن الشاشات. ولا يشترط أن يقرأ المرء كتابا كاملا كل أسبوع، "
        "فبضع صفحات في اليوم تكفي لبناء عادة تدوم سنوات."
    ),
    "solar": (
        "تتجه دول المنطقة إلى الاستثمار في الطاقة الشمسية بسبب وفرة الشمس طوال العام. وقد انخفضت "
        "تكلفة الألواح الشمسية خلال العقد الأخير انخفاضا كبيرا، مما جعل محطات الطاقة النظيفة منافسا "
        "حقيقيا لمحطات الغاز في إنتاج الكهرباء."
    ),
    "museum": (
        "يروي المتحف الوطني تاريخ البلاد منذ العصور القديمة حتى اليوم، عبر قاعات متصلة تعرض الأدوات "
        "والملابس والصور والوثائق. ويستوحي تصميم المبنى شكله من وردة الصحراء، وهي تكوينات بلورية "
        "طبيعية تتشكل في الرمال المالحة."
    ),
    "security": (
        "ينصح خبراء الأمن الرقمي باستخدام كلمات مرور طويلة ومختلفة لكل حساب، وتفعيل التحقق بخطوتين "
        "كلما أمكن ذلك. كما يحذرون من فتح الروابط التي تصل في رسائل مجهولة، لأن كثيرا من عمليات "
        "الاحتيال تبدأ برسالة تبدو عادية تماما."
    ),
    "data": (
        "يزداد الطلب على محللي البيانات في القطاعين العام والخاص، لأن المؤسسات تريد اتخاذ قراراتها "
        "بناء على أرقام واضحة لا على التخمين. ويحتاج المحلل إلى فهم الإحصاء ومهارة في عرض النتائج، "
        "إضافة إلى معرفة جيدة بالأدوات المستخدمة في تنظيف البيانات وتحليلها."
    ),
    "falcons": (
        "تحظى الصقور باهتمام كبير في ثقافة المنطقة، إذ ارتبطت قديما بالصيد في البر. ويقضي الصقار وقتا "
        "طويلا في تدريب الطائر وتعويده على صوته، ولا يزال سوق الصقور في الدوحة يستقبل الهواة والمربين "
        "من مختلف الأعمار."
    ),
    "dates": (
        "النخلة شجرة مباركة عند أهل الجزيرة العربية، فقد كان التمر غذاء أساسيا في الحل والترحال. ومن "
        "سعف النخيل صنعت السلال والحصر، ومن جذوعها سقفت البيوت القديمة، ولذلك لا يكاد يخلو بيت تقليدي "
        "من نخلة في فنائه."
    ),
}

# Arabic text with English words, numbers, dates, units, percentages,
# brackets, an email address and a URL. These are the lines that most
# extractors scramble.
MIXED = [
    "يعمل البرنامج على Windows 11 ويحتاج إلى 8 GB من الذاكرة على الأقل.",
    "أطلق الفريق الإصدار الجديد من Python 3.12 في 2 أكتوبر 2023 مع تحسينات في رسائل الخطأ.",
    "بلغت قيمة الفاتورة 1,250.75 QAR شاملة الضريبة، وتم الدفع بتاريخ 30/10/2026 الساعة 14:30.",
    "ارتفعت نسبة النجاح إلى 87.5% في عام 2025 بعد أن كانت 72% فقط (انظر الجدول 2).",
    "للتواصل يرجى مراسلة info@qatar-data.org أو الاتصال على الرقم +974 4412 3456 خلال أوقات الدوام.",
    "يمكن تحميل التقرير الكامل من الرابط https://data.example.qa/reports/2026 بصيغة PDF.",
    "تستخدم المكتبة PyMuPDF مع Tesseract 5 لقراءة الصفحات الممسوحة ضوئيا.",
    "ارتفع سعر الوجبة من 20 إلى 35 ريالا خلال سنتين، أي بزيادة تقارب 75%.",
    "قال المدير في كلمته: \"The future is data driven\" ثم أعلن عن برنامج تدريبي جديد.",
    "تبلغ مسافة الرحلة 450 km تقريبا، وتستغرق نحو 5 ساعات بالسيارة.",
]

ARABIC_INDIC = [
    "في عام ٢٠٢٤ بلغ عدد زوار المعرض ١٢٥ ألف زائر، بزيادة ١٨٪ عن العام السابق.",
    "يبدأ الدوام الساعة ٧:٣٠ صباحا وينتهي الساعة ٢:٣٠ ظهرا من الأحد إلى الخميس.",
    "سجلت المحطة ٤٦٫٥ درجة مئوية يوم ١٥ يوليو، وهي أعلى قراءة منذ ٢٠١٠.",
]

ENGLISH_WITH_ARABIC = [
    "The Arabic word كتاب means book, and its plural كتب is used in many library catalogues.",
    "In Doha, the National Library of Qatar holds more than 1,000,000 items. Its Arabic name is مكتبة قطر الوطنية.",
    "Search engines often fail when a PDF stores مرحبا as separate letter shapes instead of normal Unicode letters.",
    "A typical invoice line reads الإجمالي 7,350 QAR, which mixes two scripts and a number in one line.",
]

DIACRITICS = [
    "العِلْمُ نُورٌ وَالجَهْلُ ظَلَامٌ.",
    "قَرَأَ الطَّالِبُ الكِتَابَ فِي المَكْتَبَةِ ثُمَّ كَتَبَ مُلَخَّصًا قَصِيرًا.",
    "مَنْ جَدَّ وَجَدَ، وَمَنْ زَرَعَ حَصَدَ.",
]

TABLE_INVOICE = [
    ["المنتج", "الكمية", "سعر الوحدة", "الإجمالي"],
    ["حاسوب محمول", "3", "2,450 QAR", "7,350 QAR"],
    ["شاشة عرض", "5", "980 QAR", "4,900 QAR"],
    ["لوحة مفاتيح", "10", "120 QAR", "1,200 QAR"],
    ["فأرة لاسلكية", "12", "85 QAR", "1,020 QAR"],
]

TABLE_WEATHER = [
    ["الشهر", "أعلى حرارة", "أدنى حرارة", "الأمطار (مم)"],
    ["يناير", "22", "14", "13"],
    ["أبريل", "32", "21", "5"],
    ["يوليو", "42", "31", "0"],
    ["أكتوبر", "35", "25", "1"],
]

TABLE_STAFF = [
    ["الاسم", "القسم", "سنة التعيين", "البريد"],
    ["سارة أحمد", "البيانات", "2021", "sara@example.qa"],
    ["خالد علي", "الشبكات", "2019", "khaled@example.qa"],
    ["مريم يوسف", "الموارد البشرية", "2023", "maryam@example.qa"],
]

P = PARAGRAPHS

DOCUMENTS = {
    # Documents drawn with reportlab from text shaped by arabic-reshaper and
    # reordered by python-bidi. This is how many older generators (and a lot
    # of PHP and Java reporting tools) still write Arabic: presentation forms,
    # stored in visual order.
    "legacy_simple_arial": {
        "engine": "legacy", "font": "arial", "category": "simple",
        "blocks": [("h1", "المكتبات والقراءة"), ("p", P["libraries"]), ("p", P["reading"]), ("p", P["programming"])],
    },
    "legacy_simple_times": {
        "engine": "legacy", "font": "times", "category": "simple",
        "blocks": [("h1", "من تاريخ الخليج"), ("p", P["pearls"]), ("p", P["dates"]), ("p", P["falcons"])],
    },
    "legacy_simple_tahoma": {
        "engine": "legacy", "font": "tahoma", "category": "simple",
        "blocks": [("p", P["weather"]), ("p", P["desert"]), ("p", P["solar"])],
    },
    "legacy_simple_trado": {
        "engine": "legacy", "font": "trado", "category": "simple",
        "blocks": [("h1", "الخط والقهوة"), ("p", P["calligraphy"]), ("p", P["coffee"])],
    },
    "legacy_mixed_arial": {
        "engine": "legacy", "font": "arial", "category": "mixed",
        "blocks": [("h1", "ملاحظات تقنية")] + [("p", t) for t in MIXED],
    },
    "legacy_two_column_arial": {
        "engine": "legacy", "font": "arial", "category": "two-column", "columns": 2,
        "blocks": [("h1", "نشرة المدينة"), ("p", P["metro"]), ("p", P["museum"]), ("p", P["health"]),
                   ("p", P["security"]), ("p", P["data"]), ("p", P["weather"])],
    },
    "legacy_headers_tahoma": {
        "engine": "legacy", "font": "tahoma", "category": "headers",
        "header": "التقرير السنوي للخدمات العامة", "footer": "صفحة {page} من {pages}",
        "blocks": [("h1", "الخدمات العامة"), ("p", P["metro"]), ("p", P["health"]), ("page",),
                   ("p", P["libraries"]), ("p", P["museum"]), ("page",),
                   ("p", P["security"]), ("p", P["data"])],
    },
    "legacy_table_arial": {
        "engine": "legacy", "font": "arial", "category": "table",
        "blocks": [("h1", "فاتورة مشتريات"), ("p", "تفاصيل الطلب رقم 2041 كما وردت من المورد."),
                   ("table", TABLE_INVOICE), ("p", "جميع الأسعار شاملة الضريبة.")],
    },

    # Documents printed to PDF by a browser (headless Edge). The browser shapes
    # the text with a real layout engine, so these look like PDFs saved from
    # Word, Chrome or Google Docs.
    "browser_simple_arial": {
        "engine": "browser", "font": "Arial", "category": "simple",
        "blocks": [("h1", "البيئة والطاقة"), ("p", P["desert"]), ("h2", "الطاقة الشمسية"), ("p", P["solar"]),
                   ("h2", "الطقس"), ("p", P["weather"])],
    },
    "browser_simple_segoe": {
        "engine": "browser", "font": "Segoe UI", "category": "simple",
        "blocks": [("h1", "الحياة الرقمية"), ("p", P["security"]), ("p", P["health"]), ("p", P["data"])],
    },
    "browser_simple_majalla": {
        "engine": "browser", "font": "Sakkal Majalla", "category": "simple", "size": 16,
        "blocks": [("h1", "من التراث"), ("p", P["falcons"]), ("p", P["dates"]), ("p", P["pearls"])],
    },
    "browser_simple_simplified": {
        "engine": "browser", "font": "Simplified Arabic", "category": "simple",
        "blocks": [("p", P["museum"]), ("p", P["metro"]), ("p", P["libraries"])],
    },
    "browser_simple_typesetting": {
        "engine": "browser", "font": "Arabic Typesetting", "category": "simple", "size": 20,
        "blocks": [("h1", "الخط العربي"), ("p", P["calligraphy"]), ("p", P["coffee"])],
    },
    "browser_mixed_tahoma": {
        "engine": "browser", "font": "Tahoma", "category": "mixed",
        "blocks": [("h1", "ملاحظات تقنية")] + [("p", t) for t in MIXED],
    },
    "browser_mixed_indic_times": {
        "engine": "browser", "font": "Times New Roman", "category": "mixed", "size": 15,
        "blocks": [("h2", "أرقام وإحصاءات")] + [("p", t) for t in ARABIC_INDIC] + [("p", MIXED[3]), ("p", MIXED[7])],
    },
    "browser_english_arabic": {
        "engine": "browser", "font": "Segoe UI", "category": "mixed", "dir": "ltr",
        "blocks": [("h1", "Arabic inside English text")] + [("p", t) for t in ENGLISH_WITH_ARABIC],
    },
    "browser_two_column_times": {
        "engine": "browser", "font": "Times New Roman", "category": "two-column", "columns": 2, "size": 13,
        "blocks": [("h1", "مجلة المعرفة"), ("p", P["reading"]), ("p", P["programming"]), ("p", P["calligraphy"]),
                   ("p", P["museum"]), ("p", P["coffee"]), ("p", P["falcons"])],
    },
    "browser_three_column_arial": {
        "engine": "browser", "font": "Arial", "category": "two-column", "columns": 3, "size": 11,
        "blocks": [("h1", "أخبار قصيرة"), ("p", P["metro"]), ("p", P["solar"]), ("p", P["health"]),
                   ("p", P["desert"]), ("p", P["security"]), ("p", P["dates"])],
    },
    "browser_headers_arial": {
        "engine": "browser", "font": "Arial", "category": "headers",
        "header": "دليل الطالب 2026", "footer": "صفحة {page} من {pages}",
        "blocks": [("h1", "نصائح للدراسة"), ("p", P["reading"]), ("p", P["programming"]), ("page",),
                   ("p", P["libraries"]), ("p", P["data"]), ("page",),
                   ("p", P["security"]), ("p", P["health"])],
    },
    "browser_table_arial": {
        "engine": "browser", "font": "Arial", "category": "table",
        "blocks": [("h1", "فاتورة مشتريات"), ("p", "تفاصيل الطلب رقم 2041 كما وردت من المورد."),
                   ("table", TABLE_INVOICE), ("p", "جميع الأسعار شاملة الضريبة.")],
    },
    "browser_table_tahoma": {
        "engine": "browser", "font": "Tahoma", "category": "table",
        "blocks": [("h2", "الطقس في الدوحة"), ("table", TABLE_WEATHER), ("p", P["weather"]),
                   ("h2", "فريق العمل"), ("table", TABLE_STAFF)],
    },
    "browser_diacritics_arial": {
        "engine": "browser", "font": "Arial", "category": "diacritics", "size": 16,
        "blocks": [("h2", "حكم وأمثال")] + [("p", t) for t in DIACRITICS],
    },

    # Image-only PDFs: browser documents rasterised and wrapped back into a
    # PDF with no text layer, like a scanner or a phone camera app produces.
    "scanned_simple_arial": {
        "engine": "scanned", "source": "browser_simple_arial", "category": "scanned", "dpi": 200,
    },
    "scanned_mixed_tahoma": {
        "engine": "scanned", "source": "browser_mixed_tahoma", "category": "scanned", "dpi": 200,
    },
}
