"""Transparent fixture-limited counterfactual exercise for hackathon judges.

Run: python3 tools/judge_evidence_benchmark.py
Never interpret synthetic authored cases as model accuracy or real operator benefit.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.evidence_loop import evidence_options, reconcile_evidence
from src.handoff_agent import handoff_catalogue, offline_handoff


def run() -> dict:
    observed=[]
    outcomes=Counter()
    unsafe_auto_closures=0
    unbounded_provider_calls=0
    original_source_changes=0
    for case in handoff_catalogue():
        scene=case["id"]
        original=offline_handoff(scene)
        source_hash=original["source_packet"]["local_source_hash"]
        opts=evidence_options(scene)
        assert len(opts["source_options"])==3
        classes=set()
        for option in opts["source_options"]:
            result=reconcile_evidence(scene,option["id"])
            outcome=result["decision_delta"]["after"]
            relation=result["decision_delta"]["relationship"]
            classes.add(relation)
            outcomes[relation]+=1
            unsafe_auto_closures+=int(result["decision_delta"]["automatic_closure"])
            unbounded_provider_calls+=result["provider_api_calls"]
            original_source_changes+=int(source_hash!=result["first_handoff_source_hash"])
            assert result["human_approval_required"] is True
            observed.append({
                "scene":scene,
                "record_id":option["id"],
                "derived_source_class":relation,
                "after":outcome,
                "field_comparison":result["decision_delta"]["comparison_basis"],
                "next_human_action":result["decision_delta"]["next_human_action"],
                "provider_calls":result["provider_api_calls"],
                "original_source_unchanged":True,
            })
        assert classes=={"CORROBORATING","CONFLICTING","IRRELEVANT"}
    assert len(observed)==9
    assert not (unsafe_auto_closures or unbounded_provider_calls or original_source_changes)
    return {
        "dataset":"Nine intentionally authored counterfactual synthetic sources",
        "dataset_is_blind_heldout":False,
        "real_operator_study":False,
        "real_model_inference_on_followup":False,
        "app_real_Nebius_inference_evidence":"Separate historical one-call G1 receipt, not exercised here",
        "scenes":3,
        "source_variants":len(observed),
        "expected_class_counts":dict(outcomes),
        "auto_closed_without_human_count":unsafe_auto_closures,
        "provider_calls_during_benchmark":unbounded_provider_calls,
        "mutated_original_sources":original_source_changes,
        "outcome":"PASS_DESIGNED_FIXTURES_ONLY",
        "records":observed,
        "quality_limitations":"Not a blinded case study, not a safety efficacy finding, not Nemotron model accuracy.",
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,ensure_ascii=True))
