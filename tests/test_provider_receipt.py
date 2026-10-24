"""Adversarial provider-envelope tests; no external requests or credentials."""
import json
import unittest
from src.safety_shift import (
    MODEL, MAX_RESPONSE_BYTES, InputError, parse_verified_nebius_completion,
)


def response(**changes):
    obj = {
        "id": "fictional-provider-response-only",
        "model": MODEL,
        "choices": [{
            "index": 0,
            "finish_reason": "stop",
            "message": {"role": "assistant", "content": '{"severity":"review"}'},
        }],
        "usage": {
            "prompt_tokens": 401,
            "completion_tokens": 109,
            "total_tokens": 510,
        },
    }
    obj.update(changes)
    return json.dumps(obj, separators=(",", ":")).encode()


class ProviderReceiptTests(unittest.TestCase):
    def test_accepts_bounded_completed_response_and_observed_counters(self):
        content, receipt = parse_verified_nebius_completion(response())
        self.assertEqual(json.loads(content), {"severity": "review"})
        self.assertEqual(receipt["model"], MODEL)
        self.assertEqual(receipt["http_status"], 200)
        self.assertEqual(receipt["finish_reason"], "stop")
        self.assertEqual(receipt["usage"]["total_tokens"], 510)

    def test_refuses_wrong_or_absent_model_even_if_answer_looks_safe(self):
        for model in ("nvidia/Nemotron-3-Nano-30B-A3B", None, "", "Qwen/Qwen3.5-397B-A17B"):
            with self.subTest(model=model), self.assertRaisesRegex(InputError, "model identity"):
                parse_verified_nebius_completion(response(model=model))

    def test_refuses_nonstop_or_multiple_final_choices(self):
        for finish in ("length", None, "content_filter", "tool_calls"):
            bad = [{"finish_reason": finish,
                    "message": {"content": '{"severity":"review"}'}}]
            with self.subTest(finish=finish), self.assertRaisesRegex(InputError, "truncated"):
                parse_verified_nebius_completion(response(choices=bad))
        with self.assertRaisesRegex(InputError, "completion count"):
            parse_verified_nebius_completion(response(choices=[]))
        with self.assertRaisesRegex(InputError, "completion count"):
            parse_verified_nebius_completion(response(choices=[{"message": {"content": "{}"}}] * 2))

    def test_refuses_reasoning_only_even_with_stop(self):
        with self.assertRaisesRegex(InputError, "final answer missing"):
            parse_verified_nebius_completion(response(choices=[{
                "finish_reason": "stop", "message": {
                    "content": None, "reasoning_content": "This cannot be the final answer."
                }
            }]))

    def test_refuses_missing_usage_even_with_correct_model(self):
        for usage in (None, {}, {"total_tokens": 100}):
            with self.subTest(usage=usage), self.assertRaisesRegex(InputError, "usage"):
                parse_verified_nebius_completion(response(usage=usage))

    def test_refuses_negative_boolean_and_inconsistent_usage(self):
        for usage in (
            {"prompt_tokens": 0, "completion_tokens": 2, "total_tokens": 2},
            {"prompt_tokens": True, "completion_tokens": 1, "total_tokens": 2},
            {"prompt_tokens": 5, "completion_tokens": -1, "total_tokens": 4},
            {"prompt_tokens": 5, "completion_tokens": 4, "total_tokens": 99},
            {"prompt_tokens": 5, "completion_tokens": 4097, "total_tokens": 4102},
            {"prompt_tokens": 20001, "completion_tokens": 1, "total_tokens": 20002},
        ):
            with self.subTest(usage=usage), self.assertRaisesRegex(InputError, "token usage"):
                parse_verified_nebius_completion(response(usage=usage))

    def test_refuses_truncated_json(self):
        with self.assertRaisesRegex(InputError, "not JSON"):
            parse_verified_nebius_completion(response()[:-5])

    def test_refuses_oversize_even_if_json_valid(self):
        huge = response(debug_padding="x" * MAX_RESPONSE_BYTES)
        with self.assertRaisesRegex(InputError, "bounded response size"):
            parse_verified_nebius_completion(huge)

    def test_refuses_unexpected_nonbyte_response(self):
        with self.assertRaisesRegex(InputError, "bounded response size"):
            parse_verified_nebius_completion("not bytes")

    def test_refuses_envelope_without_choice_object(self):
        with self.assertRaisesRegex(InputError, "truncated"):
            parse_verified_nebius_completion(response(choices=[None]))


if __name__ == "__main__":
    unittest.main()
