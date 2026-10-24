"""Falsification probes for critic v2: generic but fluent output must not pass.

Test fixtures are original local synthetic observations, NOT real provider
responses or independent unseen generalization performance.
"""
from __future__ import annotations
import json
import unittest

from src.handoff_agent import (
    CRITIC_VERSION,_review_model_text,handoff_catalogue,
    offline_handoff,source_packet,
)
from src.safety_shift import InputError


class CriticV2AdversarialTests(unittest.TestCase):
    def test_legitimate_original_scenario_specific_summaries_pass(self):
        for scene in handoff_catalogue():
            with self.subTest(scene=scene["id"]):
                result=offline_handoff(scene["id"])
                self.assertEqual(result["critic_policy_version"],CRITIC_VERSION)
                self.assertEqual(_review_model_text(
                    source_packet(scene["id"]),json.dumps(result["review"])
                ),result["review"])

    def test_generic_record_request_rejected_even_if_it_mentions_a_log(self):
        for scene in handoff_catalogue():
            original=offline_handoff(scene["id"])["review"]
            generic=dict(original,question_for_human=(
                "Which original source log should a qualified reviewer inspect?"
            ))
            with self.subTest(scene=scene["id"]),self.assertRaisesRegex(
                InputError,"scenario-specific"
            ):
                _review_model_text(source_packet(scene["id"]),json.dumps(generic))

    def test_generic_uncertainty_rejected_even_with_valid_source_ids(self):
        for scene in handoff_catalogue():
            original=offline_handoff(scene["id"])["review"]
            generic=dict(original,missing_evidence=(
                "An original source record is missing and remains unverified."
            ))
            with self.subTest(scene=scene["id"]),self.assertRaisesRegex(
                InputError,"scenario-specific"
            ):
                _review_model_text(source_packet(scene["id"]),json.dumps(generic))

    def test_fluent_case_agnostic_rationale_rejected(self):
        for scene in handoff_catalogue():
            original=offline_handoff(scene["id"])["review"]
            generic=dict(original,reason=(
                "The reported records are incomplete and further human review is required."
            ))
            with self.subTest(scene=scene["id"]),self.assertRaisesRegex(
                InputError,"scenario-specific"
            ):
                _review_model_text(source_packet(scene["id"]),json.dumps(generic))

    def test_missing_source_id_must_be_in_actual_citation_list(self):
        for scene in handoff_catalogue():
            original=offline_handoff(scene["id"])["review"]
            generic=dict(original,evidence_ids=[original["evidence_ids"][0]])
            with self.subTest(scene=scene["id"]),self.assertRaisesRegex(
                InputError,"missing source"
            ):
                _review_model_text(source_packet(scene["id"]),json.dumps(generic))

    def test_qualitative_fact_fabrication_blocked_without_fake_numbers(self):
        badphrases=(
            "The technician inspected the equipment.",
            "The system healthy status is established.",
            "A repair completed successfully.",
            "Service restored and there is no further action.",
            "The operator confirmed the issue was resolved.",
            "Access granted after a reviewer checks the record.",
        )
        packet=source_packet("handoff-airflow")
        base=offline_handoff("handoff-airflow")["review"]
        for phrase in badphrases:
            note=dict(base,reason="The synthetic fan record is unverified. "+phrase)
            with self.subTest(unsupported=phrase),self.assertRaises(InputError):
                _review_model_text(packet,json.dumps(note))


if __name__=="__main__":
    unittest.main()
