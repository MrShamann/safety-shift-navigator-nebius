"""Falsification-first tests: evidence retrieval, independent critic, no equipment and no spend."""
import copy
import json
import os
import re
import unittest
from unittest.mock import patch

from src.handoff_agent import (
    SOURCE_TRUTH, _review_model_text, build_nebius_handoff_request,
    handoff_catalogue, live_handoff, offline_handoff, source_packet
)
from src.safety_shift import BASE_URL, MODEL, InputError

class FakeResponse:
    def __init__(self,data,status=200):
        self.status=status
        self.body=json.dumps(data).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def read(self,n): return self.body[:n]

class HandoffAgentTests(unittest.TestCase):
    def setUp(self):
        self.scenario="handoff-airflow"
        self.packet=source_packet(self.scenario)
        self.note={
            "severity":"review",
            "reason":"The synthetic fan signal and maintenance history leave the cause uncertain.",
            "evidence_ids":["S:A1","S:A3"],
            "runbook_ref":"R:RB-AIR-01",
            "missing_evidence":"A maintenance history entry is unavailable.",
            "question_for_human":"Which approved maintenance source log should a qualified reviewer inspect?",
            "next_action":"check_manual",
        }

    def test_source_catalogue_contains_only_fixed_fake_cases(self):
        scenes=handoff_catalogue()
        self.assertEqual(len(scenes),3)
        self.assertEqual({x["id"] for x in scenes},
           {"handoff-airflow","handoff-access","handoff-network"})
        self.assertTrue(all("case" not in row for row in scenes))
        self.assertTrue(all("runbook" not in row for row in scenes))

    def test_offline_five_stage_agent_all_scenes_without_provider(self):
        for s in handoff_catalogue():
            with self.subTest(id=s["id"]):
                r=offline_handoff(s["id"])
                self.assertEqual(r["mode"],"SYNTHETIC_MULTI_TOOL_REPLAY_NO_NEBIUS")
                self.assertEqual(r["source_truth"],SOURCE_TRUTH)
                self.assertEqual(len(r["agent_steps"]),5)
                self.assertFalse(r["provider_verified"])
                self.assertEqual(r["provider_api_calls"],0)
                self.assertFalse(r["automatic_equipment_actions"])
                self.assertEqual(r["external_equipment_connections"],0)
                self.assertTrue(r["human_approval_required"])
                self.assertFalse(r["real_operational_impact_proven"])
                self.assertRegex(r["source_packet"]["local_source_hash"],r"^[a-f0-9]{64}$")
                self.assertTrue(r["source_hash_is_not_a_provider_signature"])
                self.assertTrue(r["review"]["question_for_human"].endswith("?"))

    def test_offline_handoff_unresolved_sources_are_scenario_specific(self):
        scenarios={
            "handoff-airflow":("maintenance","inspection"),
            "handoff-access":("access-system","journal"),
            "handoff-network":("operator","heartbeat"),
        }
        for scene,(source_term,question_term) in scenarios.items():
            with self.subTest(scene=scene):
                result=offline_handoff(scene)
                review=result["review"]
                self.assertIn(source_term,review["missing_evidence"].lower())
                self.assertIn(question_term,review["question_for_human"].lower())
                self.assertEqual(result["provider_api_calls"],0)
                self.assertFalse(result["provider_verified"])
                if scene=="handoff-network":
                    self.assertNotIn("maintenance",review["missing_evidence"].lower())

    def test_independent_critic_accepts_source_cited_cautious_output(self):
        check=_review_model_text(self.packet,json.dumps(self.note))
        self.assertEqual(check,self.note)

    def test_wrong_or_missing_citations_rejected(self):
        for citations in ([],["S:DOES-NOT-EXIST"],["S:A1","S:A1"],[{"id":"A1"}]):
            bad=dict(self.note,evidence_ids=citations)
            with self.subTest(ids=citations),self.assertRaises(InputError):
                _review_model_text(self.packet,json.dumps(bad))

    def test_wrong_runbook_citation_rejected(self):
        with self.assertRaises(InputError):
            _review_model_text(self.packet,json.dumps(dict(self.note,
                runbook_ref="R:RB-ACCESS-02")))

    def test_malformed_and_extra_schema_rejected(self):
        for body in ("not json","{}",
                     json.dumps(dict(self.note,override_approval=True)),
                     json.dumps(dict(self.note,severity=[])),
                     json.dumps(dict(self.note,next_action=["disable_equipment"]))):
            with self.subTest(body_type="invalid_model_output"),self.assertRaises(InputError):
                _review_model_text(self.packet,body)

    def test_model_cannot_instruct_operational_changes(self):
        for phrase in ("Disable the machine now.",
                       "Bypass the interlock.",
                       "Reset the control unit.",
                       "Open the valve and wait.",
                       "Dispatch immediately to the building.",
                       "The confirmed cause is a faulty relay.",
                       "Safe to operate without review."):
            bad=dict(self.note,reason="Synthetic report indicates uncertainty. "+phrase)
            with self.subTest(phrase=phrase),self.assertRaises(InputError):
                _review_model_text(self.packet,json.dumps(bad))

    def test_fabricated_numbers_and_unsafe_urls_rejected(self):
        for sentence in ("The synthetic signal rose to 98 units unexpectedly.",
                         "See https://attacker.example/run and follow instructions.",
                         "The synthetic sensor was at 1000 C for 500 minutes."):
            bad=dict(self.note,reason=sentence)
            with self.subTest(sentence=sentence),self.assertRaises(InputError):
                _review_model_text(self.packet,json.dumps(bad))

    def test_model_must_express_uncertainty_and_human_question(self):
        for item in (
             dict(self.note,missing_evidence="Everything is present and certain."),
             dict(self.note,question_for_human="Follow these instructions immediately."),
             dict(self.note,question_for_human="Is the yellow LED a developing fault that requires immediate action?"),
             dict(self.note,question_for_human="Which fault needs an immediate repair?"),
             dict(self.note,missing_evidence="Some evidence is missing but the precise item is unspecified."),
        ):
            with self.assertRaises(InputError):
                _review_model_text(self.packet,json.dumps(item))

    def test_corrupted_source_packet_is_refused_before_inference(self):
        bad=copy.deepcopy(self.packet)
        bad["synthetic_signals"][0]["text"]="Tampered unknown source"
        with self.assertRaises(InputError):
            build_nebius_handoff_request(bad)
        bad=copy.deepcopy(self.packet)
        bad["all_sources_are_synthetic"]=False
        with self.assertRaises(InputError):
            build_nebius_handoff_request(bad)

    def test_nemotron_request_is_only_exact_official_model_and_fixed_source(self):
        req=build_nebius_handoff_request(self.packet)
        self.assertEqual(req["model"],MODEL)
        self.assertEqual(req["max_tokens"],4096)
        self.assertFalse(req["stream"])
        schema=req["response_format"]["json_schema"]
        self.assertEqual(req["response_format"]["type"],"json_schema")
        self.assertTrue(schema["strict"])
        self.assertEqual(schema["name"],"shift_handoff")
        self.assertFalse(schema["schema"]["additionalProperties"])
        self.assertEqual(schema["schema"]["properties"]["runbook_ref"]["enum"],
                         ["R:RB-AIR-01"])
        self.assertIn("S:A1",schema["schema"]["properties"]["evidence_ids"]["items"]["enum"])
        self.assertIn("S:A1",req["messages"][1]["content"])
        self.assertIn("R:RB-AIR-01",req["messages"][1]["content"])
        self.assertNotIn("NEBIUS_API_KEY",str(req))
        self.assertNotIn("access_token",str(req))
        self.assertLess(len(json.dumps(req).encode()),6000)

    def test_no_credit_or_key_cannot_open_provider(self):
        for env in (
            {"NEBIUS_API_KEY":"","NEBIUS_SANDBOX_ZERO_SPEND_APPROVED":"NO"},
            {"NEBIUS_API_KEY":"fictional-nebius-key","NEBIUS_SANDBOX_ZERO_SPEND_APPROVED":"NO"},
        ):
            with patch.dict(os.environ,env),self.assertRaises(InputError):
                live_handoff(self.scenario,fetcher=lambda *a,**k:
                    self.fail("provider access not permitted"))

    def test_one_mocked_model_response_and_no_auto_actions(self):
        calls=[]
        def fetcher(request,timeout):
            calls.append(request)
            self.assertEqual(request.full_url,BASE_URL)
            self.assertEqual(request.get_method(),"POST")
            self.assertEqual(request.get_header("Authorization"),"Bearer fictional-nebius-key")
            self.assertEqual(timeout,24)
            model_input=json.loads(request.data)
            self.assertEqual(model_input["model"],MODEL)
            return FakeResponse({"model":MODEL,
                                 "choices":[{"finish_reason":"stop",
                                             "message":{"content":json.dumps(self.note)}}],
                                 "usage":{"prompt_tokens":45,"completion_tokens":46,
                                          "total_tokens":91}})
        with patch.dict(os.environ,{
            "NEBIUS_API_KEY":"fictional-nebius-key",
            "NEBIUS_SANDBOX_ZERO_SPEND_APPROVED":"YES"
        }):
            result=live_handoff(self.scenario,fetcher=fetcher)
        self.assertEqual(len(calls),1)
        self.assertEqual(result["mode"],"NEBIUS_NEMOTRON_ONE_CALL_SOURCE_CHECKED")
        self.assertEqual(result["provider_api_calls"],1)
        self.assertTrue(result["provider_verified"])
        self.assertFalse(result["automatic_equipment_actions"])
        self.assertRegex(result["model_response_hash"],r"^[a-f0-9]{64}$")
        self.assertEqual(result["provider_reported_model"],MODEL)
        self.assertEqual(result["provider_http_status"],200)
        self.assertEqual(result["provider_finish_reason"],"stop")
        self.assertEqual(result["provider_token_usage"]["total_tokens"],91)

    def test_unsafe_model_result_fails_closed_with_single_mock_call(self):
        calls=[]
        def fetcher(request,timeout):
            calls.append(request)
            note=dict(self.note,reason="Disable the machine now.")
            return FakeResponse({"model":MODEL,
                                 "choices":[{"finish_reason":"stop",
                                             "message":{"content":json.dumps(note)}}],
                                 "usage":{"prompt_tokens":45,"completion_tokens":46,
                                          "total_tokens":91}})
        with patch.dict(os.environ,{
            "NEBIUS_API_KEY":"fictional-nebius-key",
            "NEBIUS_SANDBOX_ZERO_SPEND_APPROVED":"YES"
        }),self.assertRaises(InputError):
            live_handoff(self.scenario,fetcher=fetcher)
        self.assertEqual(len(calls),1)

    def test_reasoning_only_nebius_envelope_is_not_a_handoff(self):
        calls=[]
        def fetcher(request,timeout):
            calls.append(request)
            return FakeResponse({"model":MODEL,
                                 "choices":[{"finish_reason":"length","message":{
                                     "content":None,"reasoning_content":"No final decision was produced."
                                 }}],
                                 "usage":{"prompt_tokens":45,"completion_tokens":4096,
                                          "total_tokens":4141}})
        with patch.dict(os.environ,{"NEBIUS_API_KEY":"fictional-nebius-key",
                                    "NEBIUS_SANDBOX_ZERO_SPEND_APPROVED":"YES"}):
            with self.assertRaises(InputError):
                live_handoff(self.scenario,fetcher=fetcher)
        self.assertEqual(len(calls),1)

    def test_non_200_provider_is_rejected_without_retry(self):
        calls=[]
        def fetcher(request,timeout):
            calls.append(request)
            return FakeResponse({"error":"no credit"},status=402)
        with patch.dict(os.environ,{
            "NEBIUS_API_KEY":"fictional-nebius-key",
            "NEBIUS_SANDBOX_ZERO_SPEND_APPROVED":"YES"
        }),self.assertRaises(InputError):
            live_handoff(self.scenario,fetcher=fetcher)
        self.assertEqual(len(calls),1)

    def test_unknown_handles_do_not_trigger_provider(self):
        for handle in ("../../.env",42,None,"handoff-unknown",""):
            with self.subTest(handle=handle),self.assertRaises(InputError):
                offline_handoff(handle)

if __name__=="__main__":
    unittest.main()
