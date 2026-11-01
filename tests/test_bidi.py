from arabic_pdf.bidi import bidi_class, bracket_errors, needs_mirroring, reorder


def logical(visual: str, rtl: bool = True) -> str:
    return "".join(reorder(list(visual), rtl))


def test_classes():
    assert bidi_class("ب") == "R"
    assert bidi_class("\ufefb") == "R"  # presentation forms are Arabic letters too
    assert bidi_class("a") == "L"
    assert bidi_class("5") == "EN"
    assert bidi_class("١") == "AN"
    assert bidi_class(" ") == "ON"
    assert bidi_class("\ue000") == "ON"  # unmapped private use glyph


def test_pure_arabic_line_is_reversed():
    # painted left to right, "سلام عليكم" is stored as "مكيلع مالس"
    assert logical("مكيلع مالس") == "سلام عليكم"


def test_latin_run_keeps_its_order():
    assert logical("مالس Hello World ابحرم") == "مرحبا Hello World سلام"


def test_ltr_line_is_untouched():
    assert logical("Hello world", rtl=False) == "Hello world"


def test_arabic_inside_ltr_line():
    assert logical("The word باتك means book", rtl=False) == "The word كتاب means book"


def test_ligature_glyph_moves_as_one_unit():
    # "ولا" painted as [lam-alef glyph][waw]; the ligature glyph maps to two letters
    assert "".join(reorder(["لا", "و"], True)) == "ولا"


def test_number_keeps_digit_order():
    assert logical("ماع 2026 يف") == "في 2026 عام"


def test_percent_stays_after_number_in_arabic_text():
    # "87.5%" after an Arabic word is painted as "%87.5"
    assert logical("ماع يف %87.5 ىلإ") == "إلى 87.5% في عام"


def test_dates_times_and_thousands():
    assert logical("14:30 ةعاسلا 30/10/2026 خيراتب") == "بتاريخ 30/10/2026 الساعة 14:30"
    assert logical("ةبيرضلا 1,250.75 غلبم") == "مبلغ 1,250.75 الضريبة"


def test_phone_number_groups():
    assert logical("3456 4412 974+ مقرلا") == "الرقم +974 4412 3456"


def test_number_after_latin_word_joins_it():
    assert logical("ديدجلا Windows 11 ماظن") == "نظام Windows 11 الجديد"
    assert logical("رادصإلا Python 3.12 مدختسا") == "استخدم Python 3.12 الإصدار"


def test_unit_after_number():
    # "8 GB" and "500 QAR" are painted "GB 8" and "QAR 500" inside Arabic text
    assert logical("ةركاذ GB 8 جاتحي") == "يحتاج 8 GB ذاكرة"
    assert logical("طقف QAR 500 رعسب") == "بسعر 500 QAR فقط"


def test_brackets_are_mirrored_back():
    # python-bidi and browsers paint "(انظر الجدول 2)" as "(2 لودجلا رظنا)"
    assert logical("(2 لودجلا رظنا) طقف") == "فقط (انظر الجدول 2)"


def test_arabic_indic_digits_and_percent():
    assert logical("ةدايزب ٪١٨ نع") == "عن ١٨٪ بزيادة"


def test_brackets_stay_when_the_producer_already_mapped_them():
    # Adobe tools map the glyph to the character it stands for, not its shape
    assert "".join(reorder(list(")2 لودجلا رظنا( طقف"), True, mirror=False)) == "فقط (انظر الجدول 2)"


def test_bracket_errors():
    assert bracket_errors("(a) [b]") == 0
    assert bracket_errors(")a(") == 2
    assert bracket_errors("(a") == 1
    assert bracket_errors("no brackets") == 0


def test_page_vote_finds_shape_mapped_brackets():
    lines = [(list("(2 لودجلا رظنا) طقف"), True)]
    assert needs_mirroring(lines)


def test_page_vote_finds_logically_mapped_brackets():
    lines = [(list(")2 لودجلا رظنا( طقف"), True), (list(")5.1.1( لكشلا"), True)]
    assert not needs_mirroring(lines)


def test_page_vote_defaults_to_mirroring():
    assert needs_mirroring([(list("مالس"), True)])
    assert needs_mirroring([])
