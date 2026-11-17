"""Evidence writer: splitting manuals into passages, search terms, checking drafted sentences."""
from app.modules.evidence.writer import (
    EVIDENCE_PROMPT_VERSION,
    build_prompt,
    check_sentences,
    evidence_schema,
    search_terms,
    split_passages,
)

MANUAL = """CRITERION 7 PROGRAM OUTCOMES

The program shall demonstrate that its graduates attain the program outcomes.
Attainment shall be measured directly through course assessment.

7.2 Continuous Improvement

The program shall use the results of outcome assessment to improve the curriculum.
Evidence of actions taken and their effect is required."""


def test_passages_keep_their_heading():
    passages = split_passages(MANUAL)
    assert [p.heading for p in passages] == ["CRITERION 7 PROGRAM OUTCOMES", "7.2 Continuous Improvement"]
    assert passages[0].text.startswith("The program shall demonstrate")
    assert "Evidence of actions taken" in passages[1].text


def test_long_paragraphs_are_cut_at_sentence_ends():
    text = " ".join(f"Sentence number {n} about assessment evidence." for n in range(80))
    passages = split_passages(text, max_chars=400)
    assert len(passages) > 3 and all(len(p.text) <= 400 for p in passages)
    assert all(p.text.endswith(".") for p in passages[:-1])


def test_search_terms_drop_short_and_common_words():
    assert search_terms("How the program shows continuous improvement", "CQI of outcomes") == [
        "continuous", "improvement", "cqi", "outcomes",
    ]


SOURCES = {
    "E1": {"kind": "co_attainment", "label": "CSE202 Databases: CO2",
           "text": "30 of 40 students reached the 50% threshold on CO2 (75%; attained). Counting only "
                   "questions the audit supports: 70% (attained)."},
    "E2": {"kind": "program_outcome", "label": "PO3", "text": "Design solutions. Mapped from 4 course outcomes."},
    "M1": {"kind": "manual", "label": "Manual — 7.2", "text": "Evidence of actions taken is required."},
}


def test_supported_sentences_cite_records_and_numbers_they_contain():
    checked = check_sentences([
        {"text": "In CSE202, 75% of students attained CO2; the exam evidence supports 70%.",
         "cites": ["E1"], "gap": False},
    ], SOURCES)
    assert checked == [{
        "text": "In CSE202, 75% of students attained CO2; the exam evidence supports 70%.",
        "cites": ["E1"], "gap": False, "status": "supported", "issues": [],
    }]


def test_invented_numbers_unknown_and_missing_citations_are_flagged():
    checked = check_sentences([
        {"text": "Attainment of CO2 rose to 92% after the changes.", "cites": ["E1"], "gap": False},
        {"text": "PO3 is mapped from 4 course outcomes.", "cites": ["E9", "E2"], "gap": False},
        {"text": "The program reviews its outcomes every year.", "cites": [], "gap": False},
        {"text": "Records of actions taken are not yet available.", "cites": ["M1"], "gap": True},
    ], SOURCES)
    assert checked[0]["status"] == "check" and "92" in checked[0]["issues"][0]
    assert checked[1]["cites"] == ["E2"] and checked[1]["issues"] == ["cites a source it was not given"]
    assert checked[2]["issues"] == ["states a fact without citing a program record"]
    assert checked[3]["status"] == "supported"  # an honest gap needs no program record


def test_course_and_outcome_codes_are_not_mistaken_for_numbers():
    checked = check_sentences([{"text": "CSE202 develops PO3 through CO2.", "cites": ["E2"], "gap": False}], SOURCES)
    assert checked[0]["status"] == "supported"


def test_prompt_lists_sources_and_schema_limits_citations_to_them():
    prompt = build_prompt("Program Outcomes", "Show direct measurement.", SOURCES)
    assert "[E1] CSE202 Databases: CO2:" in prompt and "[M1] Manual — 7.2:" in prompt
    assert "What it asks for: Show direct measurement." in prompt
    schema = evidence_schema(list(SOURCES))
    assert schema["properties"]["sentences"]["items"]["properties"]["cites"]["items"]["enum"] == ["E1", "E2", "M1"]
    assert EVIDENCE_PROMPT_VERSION == "evidence-v1"


def test_citations_repeated_inside_the_text_are_removed():
    checked = check_sentences([
        {"text": 'CO2 was attained at 75% ["E1"]. PO3 is mapped (E2) from 4 outcomes [E1, E2].',
         "cites": ["E1", "E2"], "gap": False},
    ], SOURCES)
    assert checked[0]["text"] == "CO2 was attained at 75%. PO3 is mapped from 4 outcomes."
    unclosed = check_sentences([{"text": "CO2 was attained at 75% [E1", "cites": ["E1"], "gap": False}], SOURCES)
    assert unclosed[0]["text"] == "CO2 was attained at 75%"
