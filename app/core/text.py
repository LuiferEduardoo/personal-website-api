import math
import re
import unicodedata
from datetime import time

_SLUG_NON_WORD = re.compile(r"[^a-z0-9]+")
_HTML_TAG = re.compile(r"<[^>]+>")
_HTML_ENTITY = re.compile(r"&[^;\s]+;")
_WHITESPACE = re.compile(r"\s+")

DEFAULT_WORDS_PER_MINUTE = 200


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = _SLUG_NON_WORD.sub("-", ascii_text).strip("-")
    return slug or "post"


def estimate_reading_time(
    html_content: str, words_per_minute: int = DEFAULT_WORDS_PER_MINUTE
) -> time:
    stripped = _HTML_TAG.sub(" ", html_content)
    stripped = _HTML_ENTITY.sub(" ", stripped)
    stripped = _WHITESPACE.sub(" ", stripped).strip()
    word_count = len(stripped.split()) if stripped else 0
    minutes_total = max(1, math.ceil(word_count / words_per_minute))
    hours, minutes = divmod(minutes_total, 60)
    return time(hour=min(hours, 23), minute=minutes, second=0)
