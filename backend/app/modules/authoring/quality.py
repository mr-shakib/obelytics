"""
Checks on a course outcome statement, done in code so they never depend on the model.

They return plain warnings for the teacher; none of them blocks saving a CO.
"""
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

# Verbs that name a state of mind rather than something an exam can observe.
VAGUE_VERBS = {
    "understand", "know", "learn", "appreciate", "comprehend", "realize", "realise",
    "grasp", "be", "become", "gain", "familiarize", "familiarise", "acquire", "master",
}

# Usual action verbs per cognitive level (revised Bloom's taxonomy). A verb may
# fit more than one level; a mismatch is only reported when it fits none of the
# levels the CO is tagged with.
COGNITIVE_VERBS: dict[str, set[str]] = {
    "remember": {"define", "list", "recall", "state", "name", "identify", "recognize",
                 "recognise", "label", "match", "memorize", "reproduce", "select"},
    "understand": {"explain", "describe", "summarize", "summarise", "interpret", "classify",
                   "discuss", "illustrate", "paraphrase", "express", "outline", "infer",
                   "exemplify", "compare", "contrast", "translate", "relate", "review"},
    "apply": {"apply", "solve", "use", "implement", "demonstrate", "compute", "calculate",
              "execute", "operate", "perform", "employ", "practice", "practise", "determine",
              "sketch", "construct", "conduct", "carry", "prepare", "simulate", "program",
              "measure", "estimate", "model"},
    "analyze": {"analyze", "analyse", "differentiate", "distinguish", "examine", "compare",
                "contrast", "investigate", "categorize", "categorise", "deconstruct",
                "attribute", "inspect", "diagnose", "debug", "decompose", "derive",
                "interpret", "model", "test"},
    "evaluate": {"evaluate", "assess", "justify", "critique", "criticize", "criticise", "judge",
                 "appraise", "argue", "defend", "recommend", "validate", "verify", "prioritize",
                 "prioritise", "select", "rate", "conclude", "measure", "test", "optimize",
                 "optimise", "compare"},
    "create": {"design", "develop", "create", "construct", "formulate", "propose", "devise",
               "compose", "plan", "build", "invent", "synthesize", "synthesise", "generate",
               "produce", "integrate", "author", "model", "prototype"},
}
_ALL_VERBS = set().union(*COGNITIVE_VERBS.values())

_LEVEL_PREFIXES = (
    ("remember", ("remem", "knowledge", "recall")),
    ("understand", ("underst", "compreh")),
    ("apply", ("appl",)),
    ("analyze", ("analy",)),
    ("evaluate", ("evalu",)),
    ("create", ("creat", "synth")),
)

# "Students will be able to …", "On completion of the course, students should be able to …",
# "Students will understand …"
_PREFIX = re.compile(
    r"^(?:.{0,120}?\b(?:will|should|shall|can)\s+be\s+able\s+to"
    r"|(?:be\s+)?able\s+to"
    r"|(?:the\s+)?(?:students?|learners?)\s+(?:will|should|shall|can|must))\s+",
    re.IGNORECASE,
)
_WORD = re.compile(r"[a-zA-Z][a-zA-Z'-]*")
_JOINED_VERB = re.compile(r"(?:\band\b|,)\s+([a-zA-Z]+)\s+([a-zA-Z]+)", re.IGNORECASE)
_NOT_AN_OBJECT = {"of", "for", "to", "in", "on", "with", "and", "or", "by", "as", "from"}
# Openings that describe the course or the teacher, not what students will do.
_NOT_A_VERB = {
    "this", "the", "a", "an", "to", "students", "student", "learners", "course", "introduce",
    "introduces", "introduction", "provide", "provides", "teach", "teaches", "cover", "covers",
    "knowledge", "ability", "familiarity", "awareness",
}
_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "with", "by", "as", "from",
    "at", "into", "using", "use", "their", "its", "such", "various", "different", "given",
    "basic", "simple", "students", "student", "able", "will", "be",
}

MIN_WORDS = 6
MAX_WORDS = 45
SIMILARITY = 0.6


@dataclass(frozen=True)
class LevelInfo:
    code: str
    name: str


def canonical_level(name: str) -> str | None:
    """Map an organization's level name (e.g. "Analysing") to a cognitive level, if it is one."""
    lowered = (name or "").strip().lower()
    for level, prefixes in _LEVEL_PREFIXES:
        if lowered.startswith(prefixes):
            return level
    return None


def strip_prefix(statement: str) -> str:
    return _PREFIX.sub("", statement.strip(), count=1)


def leading_verb(statement: str) -> str | None:
    match = _WORD.search(strip_prefix(statement))
    return match.group(0).lower() if match else None


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text) if w.lower() not in _STOPWORDS and len(w) > 2}


def similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def check_statement(
    statement: str,
    *,
    levels: Sequence[LevelInfo] = (),
    others: Iterable[tuple[str, str]] = (),
) -> list[str]:
    """
    Warnings for one CO statement.

    levels — the Bloom levels the CO is tagged with.
    others — (label, statement) pairs it should not repeat, e.g. the course's other COs.
    """
    warnings: list[str] = []
    text = statement.strip()
    words = _WORD.findall(strip_prefix(text))
    verb = leading_verb(text)

    if verb in VAGUE_VERBS:
        warnings.append(
            f"Starts with “{verb}”, which can't be observed or assessed. Use an action verb "
            "such as explain, apply, analyze or design."
        )
    elif verb in _NOT_A_VERB:
        warnings.append(
            "Should start with what students will be able to do, as one measurable action verb."
        )

    tagged = [(lvl, canonical_level(lvl.name)) for lvl in levels]
    cognitive = [(lvl, canon) for lvl, canon in tagged if canon]
    if verb in _ALL_VERBS and cognitive and not any(verb in COGNITIVE_VERBS[c] for _, c in cognitive):
        usual = [lvl for lvl, _ in _LEVEL_PREFIXES if verb in COGNITIVE_VERBS[lvl]]
        tagged_names = ", ".join(f"{lvl.code} {lvl.name}" for lvl, _ in cognitive)
        warnings.append(
            f"“{verb}” usually signals {' or '.join(u.capitalize() for u in usual)}, "
            f"but the CO is tagged {tagged_names}."
        )
    if not levels:
        warnings.append("No Bloom level is tagged.")

    for match in _JOINED_VERB.finditer(strip_prefix(text)):
        second, following = match.group(1).lower(), match.group(2).lower()
        if second in _ALL_VERBS and second != verb and following not in _NOT_AN_OBJECT:
            warnings.append(
                f"May combine more than one outcome (“{verb}” and “{second}”). "
                "One action per CO is easier to assess."
            )
            break

    if len(words) < MIN_WORDS:
        warnings.append("Too short to say what students will do and with what content.")
    elif len(words) > MAX_WORDS:
        warnings.append("Long for one outcome; consider trimming it or splitting it in two.")

    for label, other in others:
        if similarity(text, other) >= SIMILARITY:
            warnings.append(f"Very similar to {label}.")
            break
    return warnings
