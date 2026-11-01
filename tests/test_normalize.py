from arabic_pdf.normalize import fold, is_presentation_form, uses_non_arabic_letters


def test_presentation_forms_become_letters():
    # "مرحبا" written with initial, medial and final shapes
    assert fold("ﻣﺮﺣﺒﺎ") == "مرحبا"


def test_lam_alef_ligature_keeps_logical_order():
    assert fold("ﻻ") == "لا"
    assert fold("ﻵ") == "لآ"
    assert fold("ﻭﻼ") == "ولا"


def test_allah_ligature():
    assert fold("ﷲ") == "الله"


def test_isolated_harakat_lose_their_space():
    assert fold("ﹶ") == "َ"
    assert fold("مﹼ") == "مّ"
    # shadda with fatha ligature: no stray space, NFC order of marks
    assert fold("مﱠ") == "مَّ"


def test_tatweel_removed_by_default():
    assert fold("مـــدرسة") == "مدرسة"
    assert fold("مـــدرسة", keep_tatweel=True) == "مـــدرسة"


def test_latin_ligatures():
    assert fold("ﬁnance") == "finance"


def test_persian_variant_shapes_map_to_arabic_letters():
    # Arial maps its medial yeh and heh glyphs to the Persian code points
    assert fold("ﯾ") == "ي"
    assert fold("ﮫ") == "ه"
    assert fold("ﯽ") == "ى"
    # unless the text is Persian
    assert fold("ﯾ", arabic_variants=False) == "ی"


def test_detects_persian_letters():
    assert uses_non_arabic_letters("پدر")
    assert not uses_non_arabic_letters("مدرسة")


def test_plain_text_untouched():
    text = "النص العادي 2026 and English."
    assert fold(text) == text
    assert not any(is_presentation_form(c) for c in fold("ﻻﷲ"))
