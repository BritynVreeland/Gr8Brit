"""Verbatim-quote guarantees.

Every quote stored as evidence must be an exact substring of the raw document it came from.
The model proposes a quote; this module locates it in the source and returns the true offsets,
or rejects it. Quotes are never "repaired" into existence.
"""

import unicodedata
from dataclasses import dataclass

# Typographic variants LLMs commonly normalize when copying text.
_CHAR_FOLDS = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "‛": "'",
        "′": "'",
        "“": '"',
        "”": '"',
        "‟": '"',
        "″": '"',
        "–": "-",
        "—": "-",
        "−": "-",
        " ": " ",
        " ": " ",
        " ": " ",
        "…": "\x00",  # placeholder, expanded below so "…" matches "..."
    }
)


@dataclass(frozen=True)
class QuoteMatch:
    start: int
    end: int
    text: str  # exact source text between start and end


def _fold(text: str) -> tuple[str, list[int]]:
    """Fold text for matching; return folded string and a map folded-index -> source-index.

    Folding: NFC, typographic quotes/dashes/spaces -> ASCII, ellipsis -> '...', runs of
    whitespace -> one space, case-insensitive.
    """
    out_chars: list[str] = []
    index_map: list[int] = []
    prev_space = False
    for i, ch in enumerate(unicodedata.normalize("NFC", text)):
        ch = ch.translate(_CHAR_FOLDS)
        if ch == "\x00":
            for _ in range(3):
                out_chars.append(".")
                index_map.append(i)
            prev_space = False
            continue
        if ch.isspace():
            if prev_space:
                continue
            ch = " "
            prev_space = True
        else:
            prev_space = False
        out_chars.append(ch.lower())
        index_map.append(i)
    return "".join(out_chars), index_map


def locate_quote(source: str, quote: str) -> QuoteMatch | None:
    """Find `quote` inside `source`, tolerant only of whitespace/typography/case differences.

    Returns the exact source span, or None if the quote does not occur in the source.
    The source must already be NFC-normalized (collectors store NFC text).
    """
    quote = quote.strip()
    if not quote:
        return None
    exact = source.find(quote)
    if exact != -1:
        return QuoteMatch(exact, exact + len(quote), quote)

    folded_src, index_map = _fold(source)
    folded_q, _ = _fold(quote)
    folded_q = folded_q.strip()
    pos = folded_src.find(folded_q)
    if pos == -1:
        return None
    start = index_map[pos]
    end = index_map[pos + len(folded_q) - 1] + 1
    return QuoteMatch(start, end, source[start:end])


def verify_span(source: str, quote: str, start: int, end: int) -> bool:
    """True when source[start:end] is exactly the stored quote (used by audits)."""
    return 0 <= start < end <= len(source) and source[start:end] == quote


def normalize_body(text: str) -> str:
    """Canonical form for raw document bodies: NFC, trimmed, normalized line endings."""
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()
