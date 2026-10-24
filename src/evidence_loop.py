"""Original synthetic evidence-delta loop: new record -> independent review -> human.

This module NEVER calls Nebius, sends email, executes machine actions or promotes
fictional archive records to real-world attested evidence. It demonstrates the
difference between text summarization and inspectable evidence reconciliation.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .handoff_agent import handoff_catalogue, offline_handoff
from .safety_shift import InputError

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "fixtures" / "followup_records.json"
TRUTH = "ORIGINAL_SYNTHETIC_UNATTESTED"
MODE = "SYNTHETIC_EVIDENCE_RECONCILIATION_NO_NEBIUS"
KINDS = {"CORROBORATING", "CONFLICTING", "IRRELEVANT"}
ASSET_SIGNAL_BASELINE = {
    "handoff-airflow": ("AIR_HANDLER", "yellow"),
    "handoff-access": ("ACCESS_READER", "amber"),
    "handoff-network": ("NETWORK_MONITOR", "missing"),
}
OTHER_ASSETS = {"LOBBY_HVAC", "PARKING_INVENTORY", "PRINTER"}
ALLOWED_OBSERVATIONS = {"yellow", "amber", "green", "missing", "complete", "unknown"}
STATES = {
    "CORROBORATING": "PARTIAL_SOURCE_ADDED_HUMAN_REVIEW",
    "CONFLICTING": "SOURCE_CONFLICT_HUMAN_ESCALATION",
    "IRRELEVANT": "UNRELATED_SOURCE_STILL_MISSING",
}
ACTIONS = {
    "CORROBORATING": "check_manual",
    "CONFLICTING": "notify_supervisor",
    "IRRELEVANT": "request_relevant_record",
}
EXPLANATIONS = {
    "CORROBORATING": (
        "A relevant but unauthenticated fictional excerpt was retrieved; "
        "the original missing source has NOT been independently verified."
    ),
    "CONFLICTING": (
        "Two invented source records contradict one another. A human must "
        "reconcile the underlying records before changing the handoff."
    ),
    "IRRELEVANT": (
        "This fictional excerpt concerns an unrelated system. The original "
        "evidence gap remains open and no determination is made."
    ),
}
_ALLOWED_FIELDS = {
    "id", "scenario_id", "title", "evidence_id", "relationship",
    "excerpt", "uncertainty", "question_for_human",
    "asset_class", "reported_signal",
}


def _digest(obj: dict) -> str:
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")).hexdigest()


def _archive() -> list[dict]:
    try:
        data = json.loads(ARCHIVE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError("original fictional archive unavailable") from exc
    if (not isinstance(data, dict) or set(data) !=
            {"revision", "archive_kind", "records"} or
            data.get("archive_kind") != TRUTH or
            data.get("revision") != "independent-evidence-delta-v1-20261024"):
        raise InputError("unverified archive provenance")
    records = data["records"]
    if not isinstance(records, list) or len(records) != 9:
        raise InputError("fictional archive size changed")
    allowed = {row["id"] for row in handoff_catalogue()}
    if len(allowed) != 3:
        raise InputError("scenario catalogue has changed")
    seen_ids: set[str] = set()
    seen_evidence: set[str] = set()
    counts = {sid: set() for sid in allowed}
    for item in records:
        if not isinstance(item, dict) or set(item) != _ALLOWED_FIELDS:
            raise InputError("fictional archive record structure changed")
        if any(not isinstance(v, str) for v in item.values()):
            raise InputError("fictional archive record is not text")
        if (not re.fullmatch(r"[A-Z]+-[A-Z]+-[0-9]{2}", item["id"]) or
            not re.fullmatch(r"F:[A-Z]{3}-[A-Z][1-9]", item["evidence_id"]) or
            item["id"] in seen_ids or item["evidence_id"] in seen_evidence or
            item["scenario_id"] not in allowed or item["relationship"] not in KINDS or
            item["asset_class"] not in (
                {v[0] for v in ASSET_SIGNAL_BASELINE.values()} | OTHER_ASSETS
            ) or item["reported_signal"] not in ALLOWED_OBSERVATIONS or
            not 12 <= len(item["title"]) <= 95 or
            not 60 <= len(item["excerpt"]) <= 260 or
            not 45 <= len(item["uncertainty"]) <= 250 or
            not 40 <= len(item["question_for_human"]) <= 240 or
            not item["question_for_human"].startswith(("Which ", "What ", "Where ")) or
            not item["question_for_human"].endswith("?")):
            raise InputError("untrusted fictional followup record")
        seen_ids.add(item["id"])
        seen_evidence.add(item["evidence_id"])
        if item["relationship"] in counts[item["scenario_id"]]:
            raise InputError("duplicate evidence class for scenario")
        counts[item["scenario_id"]].add(item["relationship"])
    if any(kinds != KINDS for kinds in counts.values()):
        raise InputError("scenario has missing counterfactual variant")
    return records


def classify_source_against_packet(packet: dict, record: dict) -> tuple[str, dict]:
    """Infer a source delta from structured evidence, never from fixture's label.

    This deliberately small counterfactual evaluator is a deterministic
    comparison of fictional fields, not a generative model or expert diagnosis.
    """
    scene=packet.get("scene_id")
    if scene not in ASSET_SIGNAL_BASELINE:
        raise InputError("no original asset signature")
    asset, expected=ASSET_SIGNAL_BASELINE[scene]
    original=[str(x.get("text","")).lower() for x in packet.get("synthetic_signals",[])]
    if not any(expected in sentence for sentence in original):
        raise InputError("source claim not anchored to original signals")
    if record["asset_class"]!=asset:
        derived="IRRELEVANT"
    elif record["reported_signal"] in ("unknown",expected):
        derived="CORROBORATING"
    else:
        derived="CONFLICTING"
    # The human-authored expected label is only a consistency oracle. It does
    # not choose the decision; inconsistent original fixtures fail closed.
    if record["relationship"]!=derived:
        raise InputError("record metadata contradicts observed asset/signal")
    return derived,{
        "original_asset":asset,
        "original_reported_signal":expected,
        "followup_asset":record["asset_class"],
        "followup_reported_signal":record["reported_signal"],
        "method":"DETERMINISTIC_SYNTHETIC_ASSET_AND_SIGNAL_CONTRAST",
        "model_inference":False,
    }


def evidence_options(scenario_id: str) -> dict:
    if not isinstance(scenario_id, str) or scenario_id not in {
        row["id"] for row in handoff_catalogue()
    }:
        raise InputError("unapproved scenario")
    choices = [r for r in _archive() if r["scenario_id"] == scenario_id]
    return {
        "scenario_id": scenario_id,
        "mode": MODE,
        "archive_truth": TRUTH,
        "source_options": [
            {"id": r["id"], "title": r["title"],
             "excerpt": r["excerpt"], "evidence_id": r["evidence_id"]}
            for r in choices
        ],
        "provider_api_calls": 0,
        "notice": "Fictional archive excerpts; relevance is decided after selection.",
    }


def reconcile_evidence(scenario_id: str, record_id: str) -> dict:
    if not isinstance(record_id, str) or not re.fullmatch(
        r"[A-Z]+-[A-Z]+-[0-9]{2}", record_id
    ):
        raise InputError("invalid archive record selector")
    options = evidence_options(scenario_id)
    matches = [
        record for record in _archive()
        if record["id"] == record_id and record["scenario_id"] == scenario_id
    ]
    if len(matches) != 1 or not any(
        o["id"] == record_id for o in options["source_options"]
    ):
        raise InputError("unrelated or forged archive record")
    record = matches[0]
    first = offline_handoff(scenario_id)
    if (first["provider_verified"] or first["provider_api_calls"] != 0 or
        first["human_approval_required"] is not True):
        raise InputError("initial handoff provenance mismatch")
    relationship,comparison=classify_source_against_packet(
        first["source_packet"],record
    )
    selected_hash = _digest(record)
    return {
        "mode": MODE,
        "scenario_id": scenario_id,
        "archive_truth": TRUTH,
        "provider_api_calls": 0,
        "provider_verified": False,
        "model_called_for_followup": False,
        "first_handoff_source_hash": first["source_packet"]["local_source_hash"],
        "original_review_kept_intact": True,
        "original_review": first["review"],
        "attached_record": {
            "id": record_id,
            "evidence_id": record["evidence_id"],
            "title": record["title"],
            "excerpt": record["excerpt"],
            "archive_sha256": selected_hash,
            "signed_provider_proof": False,
        },
        "decision_delta": {
            "before": "MISSING_OR_UNVERIFIED_RECORD",
            "after": STATES[relationship],
            "relationship": relationship,
            "explanation": EXPLANATIONS[relationship],
            "comparison_basis":comparison,
            "unresolved": record["uncertainty"],
            "next_human_question": record["question_for_human"],
            "next_human_action": ACTIONS[relationship],
            "new_evidence_id": record["evidence_id"],
            "original_source_id_count": len(first["review"]["evidence_ids"]),
            "safety_action_authorized": False,
            "automatic_closure": False,
        },
        "reconciliation_steps": [
            {"phase": "RETRIEVE_FICTIONAL_ARCHIVE", "status": "PASS"},
            {"phase": "VERIFY_SCENARIO_SOURCE_LINK", "status": "PASS"},
            {"phase": "COMPARE_WITH_ORIGINAL_PACKET", "status": relationship},
            {"phase": "REQUEST_HUMAN_SOURCE_VERIFICATION", "status": "REQUIRED"},
        ],
        "human_approval_required": True,
        "automatic_equipment_actions": False,
        "external_equipment_connections": 0,
        "source_hash_is_not_a_provider_signature": True,
        "real_operational_impact_proven": False,
    }
