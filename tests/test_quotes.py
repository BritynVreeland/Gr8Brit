from bbos.evidence.quotes import locate_quote, normalize_body, verify_span

SRC = normalize_body(
    "We land at IST at 11pm.  Is it safe to take a taxi to Sultanahmet\nthat late? I’ve read about scams…"
)


def test_exact_match_returns_offsets():
    m = locate_quote(SRC, "Is it safe to take a taxi")
    assert m and SRC[m.start : m.end] == "Is it safe to take a taxi"


def test_tolerates_whitespace_case_and_typography_but_returns_source_text():
    m = locate_quote(SRC, "is it safe to take a taxi to sultanahmet that late? I've read about scams...")
    assert m is not None
    assert m.text == SRC[m.start : m.end]
    assert m.text.startswith("Is it safe") and m.text.endswith("scams…")
    assert verify_span(SRC, m.text, m.start, m.end)


def test_rejects_paraphrase():
    assert locate_quote(SRC, "Is a taxi to Sultanahmet safe at night?") is None


def test_rejects_empty():
    assert locate_quote(SRC, "   ") is None


def test_verify_span_detects_mismatch():
    assert not verify_span(SRC, "We land", 1, 8)
