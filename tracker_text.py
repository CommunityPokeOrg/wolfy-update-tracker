"""Shared trigger-phrase matching for the Wolfy Update Tracker.

keywords.json (repo root) is the single source of truth for the phrases that
count as an "update" sighting. Matching is case-insensitive, word-boundary,
with flexible internal whitespace for multi-word phrases. Both the Python
pipeline (tools/build_state.py, scripts/record_sighting.py,
scripts/dispatch_sighting.py) and the site (app.js, via keywords.json) use
these rules.
"""
import json
import os
import re

KEYWORDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keywords.json")


def load_keywords(path=KEYWORDS_FILE):
    try:
        with open(path) as f:
            kws = json.load(f)
        kws = [k.strip() for k in kws if isinstance(k, str) and k.strip()]
        return kws or ["update"]
    except (FileNotFoundError, json.JSONDecodeError):
        return ["update"]


def _kw_re(kw):
    return re.compile(r"\b" + r"\s+".join(re.escape(w) for w in kw.split()) + r"\b",
                      re.IGNORECASE)


def occurrences(text, keywords=None):
    """Number of tracked-phrase occurrences in text (summed over phrases,
    non-overlapping per phrase)."""
    kws = keywords if keywords is not None else load_keywords()
    return sum(len(_kw_re(k).findall(text or "")) for k in kws)


# Speaker attribution: a pasted chat log can contain other people's lines.
# Two transcript shapes are recognised — Discord copy blocks ("Name — HH.MM"
# on its own line) and inline "Name: message" prefixes. Text not attributed
# to anyone still counts (the sighting form asks for Wolfy's verbatim words);
# only text explicitly attributed to a non-Wolfy speaker is excluded.
_SPEAKER_HDR = re.compile(
    r"^[ \t]*([A-Za-z0-9_.\- ]{1,30}?)[ \t]*\u2014[ \t]*"
    r"\d{1,2}[:.]\d{2}(?::\d{2})?[ \t]*(?:[ap]m)?[ \t]*$", re.I | re.M)
_NAME_PREFIX = re.compile(r"^[ \t]*([A-Za-z][A-Za-z0-9_.\-]{0,29}):")


def _is_wolfy(name):
    return bool(re.search(r"wolfy", name or "", re.I))


def wolfy_text(quote):
    """Return the portions of a sighting quote attributable to Wolfy."""
    t = quote or ""
    keep, pos, cur = [], 0, True
    for m in _SPEAKER_HDR.finditer(t):
        keep.append((cur, t[pos:m.start()]))
        cur = _is_wolfy(m.group(1))
        pos = m.end()
    keep.append((cur, t[pos:]))
    text = "".join(s for c, s in keep if c)
    lines = []
    for ln in text.split("\n"):
        m = _NAME_PREFIX.match(ln)
        if m and not _is_wolfy(m.group(1)):
            continue
        lines.append(ln)
    return "\n".join(lines)
