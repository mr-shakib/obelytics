"""Bias check: the auditor's accuracy per group of questions."""
from app.modules.integrity.evaluation import question_style, strata_report


def test_question_style_detects_math_code_scenario_and_length():
    assert question_style("Evaluate $\\int_0^1 x^2 dx$.", None, None)["math"] == "yes"
    assert question_style("Write a program:\n```c\nint main() { return 0; }\n```", None, None)["code"] == "yes"
    style = question_style("Define normalization.", "A bank keeps customer records.", "ER diagram")
    assert style == {"math": "no", "code": "no", "scenario": "yes", "figure": "yes", "length": "short (<120 chars)"}
    assert question_style("x" * 200, None, None)["length"] == "long"


def test_strata_report_counts_agreement_abstentions_and_signed_gap():
    rows = [
        {"groups": {"exam": "MID"}, "ai": "C3", "gold": "C3"},
        {"groups": {"exam": "MID"}, "ai": "C4", "gold": "C2"},   # rated two levels higher
        {"groups": {"exam": "MID"}, "ai": None, "gold": "C1"},   # abstained
        {"groups": {"exam": "FINAL"}, "ai": "C2", "gold": "C3"},
        {"groups": {"exam": "FINAL"}, "ai": "C3", "gold": "bad"},  # no usable gold: ignored
    ]
    report = strata_report(rows, min_n=3)
    final, mid = report["exam"]
    assert mid == {
        "value": "MID", "n": 3, "judged": 2, "abstain_rate": 1 / 3, "bloom_exact": 0.5,
        "bloom_within_one": 0.5, "mean_level_gap": 1.0, "too_small": False,
    }
    assert final["n"] == 1 and final["mean_level_gap"] == -1.0 and final["too_small"] is True
