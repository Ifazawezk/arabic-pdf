from arabic_pdf.metrics import cer, levenshtein, prepare, wer, word_order


def test_levenshtein_basic():
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein(["a", "b"], ["a", "b"]) == 0


def test_prepare_collapses_space_and_drops_bidi_marks():
    assert prepare("  مرحبا\u200f\n\n  بكم ") == "مرحبا بكم"


def test_cer_perfect_and_empty():
    assert cer("مرحبا بكم", "مرحبا  بكم") == 0.0
    assert cer("مرحبا بكم", "") == 1.0


def test_presentation_forms_count_as_errors():
    # same word, shaped glyph codes instead of letters
    assert cer("مرحبا", "\ufee3\ufeae\ufea3\ufe92\ufe8e") == 1.0


def test_word_order_reversed_scores_zero():
    ref = "ذهب الولد إلى المدرسة صباحا"
    hyp = " ".join(reversed(ref.split()))
    assert word_order(ref, ref) == 1.0
    assert word_order(ref, hyp) == 0.0
    assert wer(ref, ref) == 0.0
