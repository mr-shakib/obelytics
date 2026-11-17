"""Code-side checks on course outcome statements (no model involved)."""
from app.modules.authoring.quality import (
    LevelInfo,
    canonical_level,
    check_statement,
    leading_verb,
    similarity,
)
from app.modules.authoring.service import clean_statement

APPLY = LevelInfo("C3", "Apply")
ANALYZE = LevelInfo("C4", "Analyze")
CREATE = LevelInfo("C6", "Create")
VALUING = LevelInfo("A3", "Valuing")


def test_a_good_statement_has_no_warnings():
    statement = "Analyze the time complexity of recursive algorithms using recurrence relations."
    assert check_statement(statement, levels=[ANALYZE]) == []


def test_leading_verb_skips_the_able_to_prefix():
    assert leading_verb("Students will be able to design a relational schema.") == "design"
    assert leading_verb("On completion, the student should be able to explain paging.") == "explain"
    assert leading_verb("Apply Kirchhoff's laws.") == "apply"
    assert leading_verb("Students will understand sorting and searching.") == "understand"
    assert leading_verb("Students learn hashing.") == "students"


def test_vague_verbs_are_flagged():
    warnings = check_statement("Understand the basic concepts of operating systems in depth.",
                               levels=[APPLY])
    assert any("understand" in w for w in warnings)


def test_statements_that_describe_the_course_are_flagged():
    warnings = check_statement("This course introduces students to computer networks and protocols.",
                               levels=[APPLY])
    assert any("action verb" in w for w in warnings)


def test_verb_that_does_not_fit_the_tagged_level():
    warnings = check_statement("Design a memory allocator for a given set of workload constraints.",
                               levels=[APPLY])
    assert any("Create" in w and "C3 Apply" in w for w in warnings)
    assert check_statement("Design a memory allocator for a given set of workload constraints.",
                           levels=[CREATE]) == []


def test_level_check_ignores_non_cognitive_levels():
    warnings = check_statement("Display a commitment to ethical practice in group projects at all times.",
                               levels=[VALUING])
    assert not any("usually signals" in w for w in warnings)


def test_two_outcomes_in_one_are_flagged_but_not_noun_phrases():
    two = check_statement("Analyze sorting algorithms and design efficient search procedures for data.",
                          levels=[ANALYZE])
    assert any("more than one outcome" in w for w in two)
    one = check_statement("Explain the structure and design of compilers for imperative languages.",
                          levels=[LevelInfo("C2", "Understand")])
    assert not any("more than one outcome" in w for w in one)


def test_length_untagged_and_duplicates():
    assert any("Too short" in w for w in check_statement("Apply Ohm's law.", levels=[APPLY]))
    assert any("No Bloom level" in w for w in check_statement(
        "Apply Ohm's law to solve series and parallel resistor circuits.", levels=[]))
    warnings = check_statement(
        "Explain how an operating system schedules processes on a single CPU.",
        levels=[LevelInfo("C2", "Understand")],
        others=[("CO1", "Explain how the operating system schedules processes on one CPU.")],
    )
    assert "Very similar to CO1." in warnings


def test_canonical_levels_and_similarity():
    assert canonical_level("Analysing") == "analyze"
    assert canonical_level("Remembering") == "remember"
    assert canonical_level("Imitation") is None
    assert similarity("Design a database", "Design a database") == 1.0
    assert similarity("Design a database", "Explain sorting") == 0.0


def test_clean_statement_tidies_model_output():
    assert clean_statement("  students will be able to analyze   page replacement\nalgorithms ") == (
        "Analyze page replacement algorithms."
    )
    assert clean_statement("Explain paging.") == "Explain paging."
    assert clean_statement(None) == ""
