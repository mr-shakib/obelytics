"""
Agreement metrics for the gold set (docs/ai-congress/07_Evidence_and_Validation.md §1).

Bloom levels are ordinal (C1 < … < C6), so agreement uses quadratic-weighted
Cohen's kappa: a C3-vs-C4 disagreement costs less than C1-vs-C6. Fleiss' kappa
measures agreement among several raters on nominal labels (e.g. which CO).
"""
from collections import Counter
from collections.abc import Hashable, Sequence

BLOOM_ORDER = ("C1", "C2", "C3", "C4", "C5", "C6")


def weighted_kappa(a: Sequence[str], b: Sequence[str], categories: Sequence[str] = BLOOM_ORDER) -> float | None:
    """Quadratic-weighted Cohen's kappa between two raters. None if undefined."""
    pairs = [(x, y) for x, y in zip(a, b) if x in categories and y in categories]
    if not pairs:
        return None
    k = len(categories)
    index = {c: i for i, c in enumerate(categories)}
    n = len(pairs)
    observed = [[0.0] * k for _ in range(k)]
    for x, y in pairs:
        observed[index[x]][index[y]] += 1
    row = [sum(observed[i]) for i in range(k)]
    col = [sum(observed[i][j] for i in range(k)) for j in range(k)]
    weight = [[((i - j) ** 2) / ((k - 1) ** 2) for j in range(k)] for i in range(k)]
    disagreement_observed = sum(weight[i][j] * observed[i][j] for i in range(k) for j in range(k)) / n
    disagreement_expected = sum(weight[i][j] * row[i] * col[j] for i in range(k) for j in range(k)) / (n * n)
    if disagreement_expected == 0:
        return 1.0 if disagreement_observed == 0 else None
    return 1 - disagreement_observed / disagreement_expected


def fleiss_kappa(items: Sequence[Sequence[Hashable]]) -> float | None:
    """Fleiss' kappa. Each item is the list of labels its raters gave (same count per item)."""
    items = [list(item) for item in items if len(item) >= 2]
    if not items:
        return None
    raters = len(items[0])
    items = [item for item in items if len(item) == raters]
    n = len(items)
    totals: Counter = Counter()
    agreement = 0.0
    for item in items:
        counts = Counter(item)
        totals.update(counts)
        agreement += (sum(c * c for c in counts.values()) - raters) / (raters * (raters - 1))
    p_bar = agreement / n
    p_e = sum((count / (n * raters)) ** 2 for count in totals.values())
    if p_e == 1:
        return 1.0 if p_bar == 1 else None
    return (p_bar - p_e) / (1 - p_e)


def exact_agreement(a: Sequence, b: Sequence) -> float | None:
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    return sum(x == y for x, y in pairs) / len(pairs) if pairs else None


def within_one_level(a: Sequence[str], b: Sequence[str]) -> float | None:
    index = {c: i for i, c in enumerate(BLOOM_ORDER)}
    pairs = [(index[x], index[y]) for x, y in zip(a, b) if x in index and y in index]
    return sum(abs(x - y) <= 1 for x, y in pairs) / len(pairs) if pairs else None


def majority(labels: Sequence, ordinal: bool = False):
    """Most common label; for ordinal Bloom labels a tie goes to the median."""
    labels = [label for label in labels if label]
    if not labels:
        return None
    counts = Counter(labels)
    best = max(counts.values())
    leaders = [label for label, count in counts.items() if count == best]
    if len(leaders) == 1:
        return leaders[0]
    if ordinal:
        ordered = sorted(labels, key=BLOOM_ORDER.index)
        return ordered[(len(ordered) - 1) // 2]
    return None  # no majority


def precision_recall(predicted: Sequence[bool], actual: Sequence[bool]) -> tuple[float | None, float | None]:
    tp = sum(p and a for p, a in zip(predicted, actual))
    fp = sum(p and not a for p, a in zip(predicted, actual))
    fn = sum(a and not p for p, a in zip(predicted, actual))
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return precision, recall
