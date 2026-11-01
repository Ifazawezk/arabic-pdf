from arabic_pdf.normalize import fold, is_presentation_form, uses_non_arabic_letters


def test_presentation_forms_become_letters():
    # "مرحبا" written with initial, medial and final shapes
    assert fold("\ufee3\ufeae\ufea3\ufe92\ufe8e") == "مرحبا"


def test_lam_alef_ligature_keeps_logical_order():
    assert fold("\ufefb") == "لا"
    assert fold("\ufef5") == "لآ"
    assert fold("\ufeed\ufefc") == "ولا"


def test_allah_ligature():
    assert fold("\ufdf2") == "الله"


def test_isolated_harakat_lose_their_space():
    assert fold("\ufe76") == "َ"
    assert fold("م\ufe7c") == "مّ"
    # shadda with fatha ligature: no stray space, NFC order of marks
    assert fold("م\ufc60") == "مَّ"


def test_tatweel_removed_by_default():
    assert fold("مـــدرسة") == "مدرسة"
    assert fold("مـــدرسة", keep_tatweel=True) == "مـــدرسة"


def test_latin_ligatures():
    assert fold("ﬁnance") == "finance"


def test_persian_variant_shapes_map_to_arabic_letters():
    # Arial maps its medial yeh and heh glyphs to the Persian code points
    assert fold("\ufbfe") == "ي"
    assert fold("\ufbab") == "ه"
    assert fold("\ufbfd") == "ى"
    # unless the text is Persian
    assert fold("\ufbfe", arabic_variants=False) == "ی"


def test_detects_persian_letters():
    assert uses_non_arabic_letters("پدر")
    assert not uses_non_arabic_letters("مدرسة")


def test_plain_text_untouched():
    text = "النص العادي 2026 and English."
    assert fold(text) == text
    assert not any(is_presentation_form(c) for c in fold("\ufefb\ufdf2"))


def test_heh_doachashmee_letter_in_arabic_text():
    # Arial maps its initial heh glyph to U+06BE
    assert fold("\u062c\u0630\u0648\u0631\u06be\u0627") == "جذورها"


def test_farsi_yeh_letter_follows_its_shape():
    assert fold("\u0639\u06cc\u0646") == "عين"   # dotted inside a word
    assert fold("\u0639\u0644\u06cc") == "على"   # dotless at the end


def test_unmapped_alef_with_hamza_mark():
    # an alef variant without a Unicode mapping, with a hamza mark attached
    assert fold("\ufffd\u0654\u0646") == "أن"


def test_marks_after_attachment_compose():
    # alef + hamza below mark becomes the precomposed letter
    assert fold("\u0627\u0655") == "\u0625"
