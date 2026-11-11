"""
Read a prepared question paper into questions, one model call per page or text chunk.

Shared by the background job and the gold-set script, so both read papers the same way.
"""
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.modules.ai.gateway import AIGateway
from app.modules.integrity.documents import PreparedPage, PreparedPaper, normalize_label
from app.modules.integrity.prompts import (
    CONTINUATION_HINT,
    EXTRACT_PROMPT,
    EXTRACT_PROMPT_VERSION,
    EXTRACT_SCHEMA,
    EXTRACT_TEXT_PROMPT,
    EXTRACT_TEXT_PROMPT_VERSION,
    TEXT_LAYER_HINT,
)

# Below this share of its word pairs found in the document, a question read from a
# text source is flagged: the model may have reworded or invented part of it.
MIN_WORDING_FOUND = 0.6
WORDING_WARNING = "Part of this wording is not in the document. Check it against the paper."


@dataclass
class ReadResult:
    questions: list[dict]
    model: str | None
    prompt_version: str


def _optional_text(value, max_length: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:max_length] or None


# Models often write LaTeX such as \frac or \times inside JSON with one backslash,
# which JSON decodes as a control character (form feed, tab, ...). Restore it.
_BROKEN_LATEX = re.compile(r"[\f\b\t\r](?=[A-Za-z])")
_LATEX_ESCAPES = {"\f": "\\f", "\b": "\\b", "\t": "\\t", "\r": "\\r"}


def repair_latex(text: str | None) -> str | None:
    return _BROKEN_LATEX.sub(lambda m: _LATEX_ESCAPES[m.group()], text) if text else text


_CO_CODE = re.compile(r"\s*(?:CO|CLO)\s*-?\s*\d{1,2}\s*", re.IGNORECASE)


def clean_extracted(data: dict) -> list[dict]:
    questions = data.get("questions") if isinstance(data, dict) else None
    cleaned = []
    for item in questions or []:
        if not isinstance(item, dict):
            continue
        label = _optional_text(item.get("label"), 50)
        text = repair_latex(_optional_text(item.get("text"), 5000))
        if not text or (not label and not item.get("continues")):
            continue
        marks = item.get("marks")
        cleaned.append({
            "label": label or "",
            "text": text,
            "context": repair_latex(_optional_text(item.get("context"), 5000)),
            "marks": float(marks) if isinstance(marks, (int, float)) and not isinstance(marks, bool) else None,
            # Only CO-shaped values: models sometimes put the marks ("[03]") here.
            "co": co if (co := _optional_text(item.get("co"), 20)) and _CO_CODE.fullmatch(co) else None,
            "figure": repair_latex(_optional_text(item.get("figure"), 1000)),
            "continues": item.get("continues") is True,
        })
    return cleaned


def merge_continuation(existing: list[dict], found: list[dict]) -> list[dict]:
    """
    Join a question split across a page break. The model marks the first entry of a
    page "continues" when it finishes the previous page's last question.
    """
    if found and existing and found[0]["continues"]:
        head, last = found[0], existing[-1]
        same = not head["label"] or normalize_label(head["label"]) == normalize_label(last["label"])
        if same:
            if head["text"] not in last["text"]:
                last["text"] = f"{last['text']}\n{head['text']}"
            for key in ("marks", "co", "figure", "context"):
                last[key] = last[key] if last[key] is not None else head[key]
            last["_checked"] = last.get("_checked", False) or head.get("_checked", False)
            found = found[1:]
    return existing + [item for item in found if item["label"]]


_BARE_PART = re.compile(r"\(?([a-z]{1,4})\)?\.?")
_ROMAN = re.compile(r"i{1,3}|iv|vi{0,3}|ix|x")
_NUMBER = re.compile(r"\s*(\d+)")
_NUMBER_LETTER = re.compile(r"\s*(\d+)\s*\(?([a-z])\)?")
_ENDS_ROMAN = re.compile(r"\((?:i{1,3}|iv|vi{0,3}|ix|x)\)\s*$")


def attach_bare_labels(questions: list[dict]) -> list[dict]:
    """
    A sub-part printed without its question number — "d)" at the top of a new page —
    belongs to the last numbered question: "3(d)". A roman part after "2(b)(i)"
    becomes "2(b)(ii)".
    """
    previous: str | None = None
    for question in questions:
        bare = _BARE_PART.fullmatch(question["label"].strip().lower())
        if bare and previous:
            token = bare.group(1)
            lettered = _NUMBER_LETTER.match(previous.lower())
            if _ROMAN.fullmatch(token) and lettered and _ENDS_ROMAN.search(previous.lower()):
                question["label"] = f"{lettered.group(1)}({lettered.group(2)})({token})"
            elif number := _NUMBER.match(previous):
                question["label"] = f"{number.group(1)}({token})"
        if _NUMBER.match(question["label"]):
            previous = question["label"]
    return questions


def fold_stems(questions: list[dict]) -> list[dict]:
    """
    Models often return a shared scenario as its own entry ("1") ahead of its
    parts ("1(a)", "1(b)"). Move it into each part's context instead.
    """
    keys = [normalize_label(q["label"]) for q in questions]
    folded = []
    for question, key in zip(questions, keys):
        parts = [
            other for other, other_key in zip(questions, keys)
            if other_key.startswith(key) and other_key[len(key):][:1].isalpha()
        ]
        if not key.isdigit() or not parts:
            folded.append(question)
            continue
        stem = "\n\n".join(p for p in (question["context"], question["text"]) if p)
        for part in parts:
            part["context"] = part["context"] or stem
            part["figure"] = part["figure"] or question["figure"]
    return folded


_LATEX_COMMAND = re.compile(r"\\[A-Za-z]+")


def _word_pairs(text: str) -> set[tuple[str, str]]:
    words = re.findall(r"[a-z0-9]+", _LATEX_COMMAND.sub(" ", text.lower()))
    return set(zip(words, words[1:]))


def wording_found(text: str, source_pairs: set[tuple[str, str]]) -> float:
    pairs = _word_pairs(text)
    if len(pairs) < 3:
        return 1.0
    return len(pairs & source_pairs) / len(pairs)


def _tail(text: str, length: int = 160) -> str:
    text = " ".join(text.split())
    return text[-length:]


def build_page_prompt(page: PreparedPage, previous: dict | None) -> tuple[str, str]:
    """The prompt for one page or chunk, and its prompt version."""
    continuation = ""
    if previous is not None:
        parent = re.match(r"\s*(\d+)", previous["label"])
        continuation = CONTINUATION_HINT.format(
            label=previous["label"],
            tail=_tail(previous["text"]).replace('"', "'"),
            parent=parent.group(1) if parent else previous["label"],
        )
    if page.image is not None:
        hint = TEXT_LAYER_HINT.format(text=page.text) if page.text else ""
        return EXTRACT_PROMPT + hint + continuation, EXTRACT_PROMPT_VERSION
    return (
        EXTRACT_TEXT_PROMPT + continuation + f"\n\n<document>\n{page.text}\n</document>",
        EXTRACT_TEXT_PROMPT_VERSION,
    )


async def read_paper(
    gateway: AIGateway,
    paper: PreparedPaper,
    on_progress: Callable[[int], Awaitable[None]] | None = None,
) -> ReadResult:
    items: list[dict] = []
    models: set[str] = set()
    versions: set[str] = set()
    for index, page in enumerate(paper.pages):
        prompt, version = build_page_prompt(page, items[-1] if items else None)
        result = await gateway.complete_json(
            purpose="read_page" if page.image is not None else "split_text",
            prompt=prompt,
            schema=EXTRACT_SCHEMA,
            prompt_version=version,
            images=[page.image] if page.image is not None else None,
        )
        models.add(result.model)
        versions.add(version)
        found = clean_extracted(result.data)
        for item in found:
            item["_checked"] = page.text is not None
        items = merge_continuation(items, found)
        if on_progress is not None:
            await on_progress(index + 1)

    items = fold_stems(attach_bare_labels(items))
    source_pairs = _word_pairs(paper.source_text) if paper.source_text else set()
    questions = []
    for item in items:
        checked = item.pop("_checked", False)
        item.pop("continues", None)
        item["warning"] = (
            WORDING_WARNING
            if checked and source_pairs and wording_found(item["text"], source_pairs) < MIN_WORDING_FOUND
            else None
        )
        questions.append(item)
    return ReadResult(
        questions=questions,
        model=", ".join(sorted(models)) or None,
        prompt_version="+".join(sorted(versions)) or EXTRACT_PROMPT_VERSION,
    )
