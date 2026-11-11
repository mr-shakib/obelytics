"""
Remove personal data from text before it leaves for an external model.

Pattern-based: email addresses, phone numbers and student-ID-shaped numbers, plus
any names the caller knows are in the text (e.g. the signed-in user). It cannot
find arbitrary names typed into free text — features should not send student
records to the gateway in the first place; this is the safety net.
"""
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache

from app.core.config import settings

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
# Bangladeshi mobiles (01XXXXXXXXX, +8801XXXXXXXXX) and international "+<digits>" numbers.
_PHONE = re.compile(
    r"(?<![\w+])(?:\+?88[\s-]?)?01[3-9]\d{2}[\s-]?\d{6}(?!\d)"
    r"|(?<![\w+])\+\d{1,3}(?:[\s-]?\d{2,4}){2,4}(?!\d)"
)
# DIU-style student IDs: 221-15-4567, 0242310005101234 (16-digit registration numbers).
_STUDENT_ID = re.compile(r"(?<![\w-])\d{3}-\d{2,3}-\d{3,5}(?![\w-])|(?<!\d)\d{13,16}(?!\d)")


@dataclass
class Redaction:
    text: str
    count: int = 0
    kinds: dict[str, int] = field(default_factory=dict)


@lru_cache(maxsize=4)
def _extra_pattern(source: str) -> re.Pattern | None:
    return re.compile(source) if source else None


def redact(text: str, names: Iterable[str | None] = ()) -> Redaction:
    result = Redaction(text=text)

    def sub(pattern: re.Pattern, placeholder: str, kind: str) -> None:
        result.text, n = pattern.subn(placeholder, result.text)
        if n:
            result.count += n
            result.kinds[kind] = result.kinds.get(kind, 0) + n

    sub(_EMAIL, "[EMAIL]", "email")
    sub(_PHONE, "[PHONE]", "phone")
    sub(_STUDENT_ID, "[ID]", "id")
    extra = _extra_pattern(settings.AI_REDACT_EXTRA_PATTERN)
    if extra is not None:
        sub(extra, "[ID]", "id")
    # Longest names first, so "Md. Rahim Uddin" goes before "Rahim".
    for name in sorted({(n or "").strip() for n in names}, key=len, reverse=True):
        if len(name) >= 3:
            sub(re.compile(rf"(?<!\w){re.escape(name)}(?!\w)", re.IGNORECASE), "[PERSON]", "name")
    return result
