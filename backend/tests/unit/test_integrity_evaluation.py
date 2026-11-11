"""Agreement metrics used to score the auditor against faculty labels."""
import pytest

from app.modules.integrity.evaluation import (
    exact_agreement,
    fleiss_kappa,
    majority,
    precision_recall,
    weighted_kappa,
    within_one_level,
)


def test_weighted_kappa_perfect_and_partial():
    a = ["C1", "C2", "C3", "C4", "C5", "C6"]
    assert weighted_kappa(a, a) == pytest.approx(1.0)
    near = ["C2", "C2", "C3", "C4", "C5", "C5"]
    far = ["C6", "C2", "C3", "C4", "C5", "C1"]
    assert weighted_kappa(a, near) > weighted_kappa(a, far)


def test_weighted_kappa_matches_a_known_value():
    # Hand-checked: 2x2 table [[1,1],[0,2]] on two categories → linear = quadratic → 0.5
    assert weighted_kappa(["C1", "C1", "C2", "C2"], ["C1", "C2", "C2", "C2"], categories=("C1", "C2")) == pytest.approx(0.5)


def test_fleiss_kappa_known_example():
    # Three raters, perfect agreement on varied items → 1.0
    assert fleiss_kappa([["a", "a", "a"], ["b", "b", "b"], ["c", "c", "c"]]) == pytest.approx(1.0)
    # Systematic disagreement → negative
    assert fleiss_kappa([["a", "b"], ["b", "a"], ["a", "b"]]) < 0


def test_simple_rates():
    assert exact_agreement(["C1", "C2", None], ["C1", "C3", "C3"]) == 0.5
    assert within_one_level(["C1", "C2", "C6"], ["C2", "C4", "C6"]) == pytest.approx(2 / 3)
    assert precision_recall([True, True, False, False], [True, False, True, False]) == (0.5, 0.5)


def test_majority_breaks_ordinal_ties_with_the_median():
    assert majority(["C3", "C3", "C4"], ordinal=True) == "C3"
    assert majority(["C2", "C4", "C5"], ordinal=True) == "C4"
    assert majority(["CO1", "CO2"]) is None
    assert majority([None, ""]) is None
