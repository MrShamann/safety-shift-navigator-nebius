"""No-network security tests for Nebius/NVIDIA contest adapter."""
import json
import os
import unittest
from unittest.mock import patch

from src.safety_shift import (
    BASE_URL, MODEL, DenyRedirect, InputError, fixture,
    guarded_nebius_fetcher, live_triage, validate_model_response
)

class NebiusSecureTransportTest(unittest.TestCase):
    def test_official_nemotron_model_and_api_host(self):
        self.assertEqual(MODEL,"nvidia/Nemotron-3_5-Lightning")
        self.assertEqual(BASE_URL,
                         "https://api.tokenfactory.nebius.com/v1/chat/completions")

    def test_verified_https_no_proxy_fetcher_can_initialize(self):
        self.assertTrue(callable(guarded_nebius_fetcher()))

    def test_any_redirect_refused_before_token_forward(self):
        guard=DenyRedirect()
        for host in ("https://attacker.example/collect",
                     "https://api.tokenfactory.nebius.com/other-path"):
            with self.subTest(host=host),self.assertRaises(InputError):
                guard.redirect_request(None,None,302,"Moved",{},host)

    def test_missing_zero_spend_gate_blocks_even_with_a_key(self):
        with patch.dict(os.environ,{"NEBIUS_API_KEY":"fake-test-key-only",
             "NEBIUS_SANDBOX_ZERO_SPEND_APPROVED":"NO"}),self.assertRaises(InputError):
            live_triage(fixture(),fetcher=lambda *a,**k:self.fail("No network"))

    def test_malformed_api_keys_rejected_without_remote_call(self):
        for bad in ("short","fake fake token","fake-token\nextra",
                    "bad\tkey\tvalue","漢字"*6,"t"*301):
            with self.subTest(key_type="malformed"),patch.dict(os.environ,{
                "NEBIUS_API_KEY":bad,
                "NEBIUS_SANDBOX_ZERO_SPEND_APPROVED":"YES"
            }),self.assertRaises(InputError):
                live_triage(fixture(),fetcher=lambda *a,**k:self.fail("No network"))

    def test_offline_credentials_absent_do_not_build_http_transport(self):
        with patch.dict(os.environ,{"NEBIUS_API_KEY":"",
             "NEBIUS_SANDBOX_ZERO_SPEND_APPROVED":"NO"}),patch(
             "src.safety_shift.guarded_nebius_fetcher",
             side_effect=AssertionError("no client should be created")):
            with self.assertRaises(InputError):
                live_triage(fixture())

    def test_model_instructions_cannot_operate_hardware(self):
        for phrase in ("Disable the safety override now.",
                       "Turn off the interlock.",
                       "Open the valve manually.",
                       "Reset the alarm to clear it.",
                       "Bypass the isolation lock."):
            note={"severity":"review",
                  "reason":phrase,
                  "evidence_ids":[fixture()["signals"][0]["id"]],
                  "next_action":"check_manual"}
            with self.subTest(phrase=phrase),self.assertRaises(InputError):
                validate_model_response(fixture(),json.dumps(note))

if __name__=="__main__":
    unittest.main()
