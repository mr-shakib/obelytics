"""The CO-PO mapping rules (K, CEP, CEA) shared by the validator and AI suggestions."""
from uuid import uuid4

from app.modules.obe.mapping_rules import MappingFacts, check_link, needs_cea, needs_cep, po_number

K3, K4, K5 = uuid4(), uuid4(), uuid4()


def test_po_numbers_and_which_pos_need_cep_or_cea():
    assert po_number("PO7") == 7
    assert po_number("PO 7") is None and po_number("PSO1") is None
    assert [needs_cep(f"PO{n}") for n in (1, 7, 8, 10)] == [True, True, False, False]
    assert needs_cea("PO10") and not needs_cea("PO1") and not needs_cea("PO100")


def test_k_rule_needs_at_least_one_of_the_pos_knowledge_profiles():
    def missing_kp(co_kps):
        return check_link(
            "PO8", po_kp_ids={K3, K4}, co_kp_ids=co_kps, co_has_cep=False, co_has_cea=False
        ).missing_kp

    assert missing_kp(set()) is True
    assert missing_kp({K5}) is True
    assert missing_kp({K4}) is False
    assert missing_kp({K3, K4, K5}) is False


def test_k_rule_is_skipped_when_the_po_lists_no_knowledge_profiles():
    check = check_link("PO9", po_kp_ids=set(), co_kp_ids=set(), co_has_cep=False, co_has_cea=False)
    assert check.ok


def test_cep_and_cea_rules():
    check = check_link("PO3", po_kp_ids=set(), co_kp_ids=set(), co_has_cep=False, co_has_cea=False)
    assert check.missing_cep and not check.missing_cea and not check.ok
    check = check_link("PO10", po_kp_ids=set(), co_kp_ids=set(), co_has_cep=False, co_has_cea=False)
    assert check.missing_cea and not check.missing_cep
    assert check_link("PO10", po_kp_ids=set(), co_kp_ids=set(), co_has_cep=False,
                      co_has_cea=True).ok


def test_facts_check_counts_mappings_about_to_be_added():
    co, po = uuid4(), uuid4()
    facts = MappingFacts(po_codes={po: "PO3"}, po_kp_ids={po: {K5}}, kp_codes={K5: "K5"})

    before = facts.check(co, po)
    assert before.missing_kp and before.missing_cep
    after = facts.check(co, po, added_kp_ids=[K5], adds_cep=True)
    assert after.ok
    assert facts.required_kp_codes(po) == ["K5"]
