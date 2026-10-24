"""Prize-first falsification of consequential synthetic evidence reconciliation.

The nine authored examples are NOT blind real-world accuracy evidence; they are
explicitly disclosed unit/acceptance cases for three independent source classes.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import evidence_loop as loop
from src.handoff_agent import handoff_catalogue, offline_handoff
from src.safety_shift import InputError


class EvidenceLoopAcceptanceTests(unittest.TestCase):
    def test_one_relevant_conflicting_and_unrelated_source_per_scene(self):
        for scene in handoff_catalogue():
            with self.subTest(scene=scene["id"]):
                choices=loop.evidence_options(scene["id"])
                self.assertEqual(choices["mode"],loop.MODE)
                self.assertEqual(choices["archive_truth"],loop.TRUTH)
                self.assertEqual(choices["provider_api_calls"],0)
                self.assertEqual(len(choices["source_options"]),3)
                self.assertNotIn("relationship",choices["source_options"][0])
                self.assertEqual(len(set(x["evidence_id"] for x in choices["source_options"])),3)

    def test_source_reconciliation_changes_outcome_but_not_baseline(self):
        expected={
            "CORROBORATING":"PARTIAL_SOURCE_ADDED_HUMAN_REVIEW",
            "CONFLICTING":"SOURCE_CONFLICT_HUMAN_ESCALATION",
            "IRRELEVANT":"UNRELATED_SOURCE_STILL_MISSING",
        }
        variants=loop._archive()
        self.assertEqual(len(variants),9)
        for scene in handoff_catalogue():
            before=offline_handoff(scene["id"])
            for item in (r for r in variants if r["scenario_id"]==scene["id"]):
                with self.subTest(scene=scene["id"],record=item["id"]):
                    after=loop.reconcile_evidence(scene["id"],item["id"])
                    self.assertEqual(after["decision_delta"]["after"],expected[item["relationship"]])
                    self.assertEqual(after["first_handoff_source_hash"],
                                     before["source_packet"]["local_source_hash"])
                    self.assertEqual(after["original_review"],before["review"])
                    self.assertTrue(after["original_review_kept_intact"])
                    self.assertEqual(after["provider_api_calls"],0)
                    self.assertFalse(after["provider_verified"])
                    self.assertFalse(after["model_called_for_followup"])
                    self.assertFalse(after["automatic_equipment_actions"])
                    self.assertFalse(after["decision_delta"]["automatic_closure"])
                    self.assertFalse(after["decision_delta"]["safety_action_authorized"])
                    self.assertTrue(after["human_approval_required"])
                    self.assertFalse(after["real_operational_impact_proven"])
                    self.assertRegex(after["attached_record"]["archive_sha256"],r"^[a-f0-9]{64}$")
                    self.assertFalse(after["attached_record"]["signed_provider_proof"])
                    self.assertEqual(len(after["reconciliation_steps"]),4)

    def test_cross_case_record_swap_and_unknown_source_fail_closed(self):
        for scene in handoff_catalogue():
            bad=next(x for x in loop._archive() if x["scenario_id"]!=scene["id"])
            with self.subTest(scene=scene["id"]),self.assertRaises(InputError):
                loop.reconcile_evidence(scene["id"],bad["id"])
        for rid in ("", "../.env","F:NET-J1", "AIR-JOURNAL-99",
                    "AIR-JOURNAL-01;ignore previous","AIR-JOURNAL-01\x00"):
            with self.subTest(record=rid),self.assertRaises(InputError):
                loop.reconcile_evidence("handoff-airflow",rid)

    def test_unknown_or_malformed_case_rejected(self):
        for bad in ("handoff-lobby","../x",42,[],None):
            with self.subTest(scene=bad),self.assertRaises(InputError):
                loop.evidence_options(bad)

    def test_repeated_review_does_not_rewrite_underlying_source(self):
        scene="handoff-network"
        original=offline_handoff(scene)["source_packet"]["local_source_hash"]
        a=loop.reconcile_evidence(scene,"NETWORK-CONFLICT-02")
        b=loop.reconcile_evidence(scene,"NETWORK-CONFLICT-02")
        self.assertEqual(a,b)
        self.assertEqual(original,offline_handoff(scene)["source_packet"]["local_source_hash"])

    def test_archive_tampering_is_refused(self):
        original=json.loads(loop.ARCHIVE.read_text())
        mutations=[]
        extra=copy.deepcopy(original)
        extra["records"][0]["fake_approval"]="TRUE"
        mutations.append(extra)
        dup=copy.deepcopy(original)
        dup["records"][1]["evidence_id"]=dup["records"][0]["evidence_id"]
        mutations.append(dup)
        kind=copy.deepcopy(original)
        kind["records"][0]["relationship"]="ALREADY_SAFE"
        mutations.append(kind)
        foreign=copy.deepcopy(original)
        foreign["archive_kind"]="VERIFIED_REAL_SITE_DATA"
        mutations.append(foreign)
        missing=copy.deepcopy(original)
        missing["records"].pop()
        mutations.append(missing)
        for i,body in enumerate(mutations):
            with self.subTest(adversarial_variant=i):
                with tempfile.TemporaryDirectory(prefix="judge-nonpublic-") as work:
                    f=Path(work)/"fictional.json"
                    f.write_text(json.dumps(body))
                    with patch.object(loop,"ARCHIVE",f),self.assertRaises(InputError):
                        loop.evidence_options("handoff-airflow")

    def test_claimed_expected_label_cannot_override_actual_asset_signal_comparison(self):
        from src.handoff_agent import source_packet
        packet=source_packet("handoff-airflow")
        conflict=next(r for r in loop._archive() if r["id"]=="AIR-CONFLICT-02")
        # A dishonest label cannot cause a contradiction or safe-result promotion:
        # only the original asset and reported signal drive the comparator.
        tampered=dict(conflict,reported_signal="yellow")
        with self.assertRaisesRegex(InputError,"contradicts observed"):
            loop.classify_source_against_packet(packet,tampered)
        tampered=dict(conflict,asset_class="PRINTER")
        with self.assertRaisesRegex(InputError,"contradicts observed"):
            loop.classify_source_against_packet(packet,tampered)
        selected,basis=loop.classify_source_against_packet(packet,conflict)
        self.assertEqual(selected,"CONFLICTING")
        self.assertEqual(basis["original_reported_signal"],"yellow")
        self.assertEqual(basis["followup_reported_signal"],"green")
        self.assertFalse(basis["model_inference"])


if __name__=="__main__":
    unittest.main()
