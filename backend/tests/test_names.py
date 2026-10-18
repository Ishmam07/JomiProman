import pytest

from app.services.names import DIFFERENT, SAME, SIMILAR, classify, normalize_name


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("করিম", "করিম", SAME),
        ("করিম", "করীম", SAME),  # ী / ি folded
        ("আব্দুল হক", "আবদুল হক", SAME),  # hasanta ignored
        ("মোঃ আব্দুল করিম", "আব্দুল করিম", SAME),  # honorific dropped
        ("Md. Karim", "karim", SAME),
        ("করিম", "কারিম", SIMILAR),  # spelling variant -> amber
        ("আব্দুল হক", "আব্দুল হাক", SIMILAR),
        ("করিম", "রফিক", DIFFERENT),
        ("করিম", "রহিম", DIFFERENT),  # different people must not match
        ("জামাল উদ্দিন", "নাসরিন আক্তার", DIFFERENT),
    ],
)
def test_classify(a, b, expected):
    label, score = classify(a, b)
    assert label == expected, (a, b, label, score)


def test_word_order_does_not_matter():
    assert classify("হক আব্দুল", "আব্দুল হক")[0] == SAME


def test_empty_names_are_different():
    assert classify("", "করিম")[0] == DIFFERENT
    assert classify("মোঃ", "মো.")[0] == DIFFERENT  # only honorifics -> nothing to compare


def test_normalize_is_idempotent():
    once = normalize_name("মোঃ আব্দুল করীম")
    assert normalize_name(once) == once
