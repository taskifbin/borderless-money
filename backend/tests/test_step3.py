"""Step 3 tests — bounded LLM, number-grounded explanations, sourced RAG.

Runs with the stdlib interpreter (no network, no API key): the LLM is exercised
through injected stubs, never live.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.agent import orchestrator  # noqa: E402
from app.services import explainer, llm, regulatory_rag  # noqa: E402

VALID_INTENT = {"corridor": "AED_TO_BDT", "amount": 500, "currency": "AED",
                "recipient": "Mother", "urgency": "normal"}


class TestSchemaValidation(unittest.TestCase):
    def test_valid_intent_passes(self):
        self.assertIsNone(llm.validate_schema(dict(VALID_INTENT), llm.INTENT_SCHEMA))

    def test_missing_key_rejected(self):
        bad = {k: v for k, v in VALID_INTENT.items() if k != "amount"}
        self.assertEqual(llm.validate_schema(bad, llm.INTENT_SCHEMA), "missing:amount")

    def test_wrong_type_rejected(self):
        bad = dict(VALID_INTENT, amount="500")
        self.assertEqual(llm.validate_schema(bad, llm.INTENT_SCHEMA), "bad-type:amount")

    def test_bool_as_amount_rejected(self):
        bad = dict(VALID_INTENT, amount=True)
        # bool is rejected at the type gate (bool is not a valid amount type)
        self.assertEqual(llm.validate_schema(bad, llm.INTENT_SCHEMA), "bad-type:amount")

    def test_bad_urgency_rejected(self):
        bad = dict(VALID_INTENT, urgency="yesterday")
        self.assertEqual(llm.validate_schema(bad, llm.INTENT_SCHEMA), "bad-urgency")

    def test_non_json_rejected(self):
        data, err = llm.complete_json("not json at all", llm.INTENT_SCHEMA,
                                      llm_fn=lambda p: "I am a chatty model")
        self.assertIsNone(data)
        self.assertEqual(err, "invalid-json")

    def test_markdown_fenced_json_extracted(self):
        import json as _json

        data, err = llm.complete_json(
            "x", llm.INTENT_SCHEMA,
            llm_fn=lambda p: f"Here you go:\n```json\n{_json.dumps(VALID_INTENT)}\n```")
        self.assertIsNone(err)
        self.assertEqual(data["amount"], 500)

    def test_disabled_without_key(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(llm.is_enabled())
            data, err = llm.complete_json("x", llm.INTENT_SCHEMA)
            self.assertIsNone(data)
            self.assertEqual(err, "llm-disabled")


class TestGroundedExplainer(unittest.TestCase):
    def setUp(self):
        self.state = orchestrator.run("quote", text="Send 1,000 dirhams to my mother's bKash in Dhaka")

    def test_both_languages_present_and_grounded(self):
        result = explainer.build_explanations(self.state)
        self.assertTrue(result["grounded"])
        self.assertFalse(result["llm_paraphrased"])
        self.assertIn("33,488.80", result["en"])
        # Bangla template: Bangla copy with the same grounded Latin-digit numbers
        self.assertIn("33,488.80", result["bn"])
        self.assertIn("প্রণোদনা", result["bn"])

    def test_number_guard_rejects_injected_numbers(self):
        allowed = explainer.allowed_numbers(self.state)
        violations = explainer.numbers_violation(
            "They receive 33,488.80 BDT with a service fee of 999 BDT.", allowed)
        self.assertIn("999", " ".join(violations))

    def test_number_guard_accepts_clean_paraphrase(self):
        allowed = explainer.allowed_numbers(self.state)
        clean = ("Your family receives 33,488.80 taka including the 820.00 taka "
                 "government incentive (2.5%), in about 2 hours.")
        self.assertEqual(explainer.numbers_violation(clean, allowed), [])

    def test_llm_paraphrase_with_invented_number_is_rejected(self):
        result = explainer.build_explanations(
            self.state, llm_fn=lambda p: "They receive 33,488.80 BDT for a flat 4.99 service charge.")
        self.assertFalse(result["llm_paraphrased"], "paraphrase with invented number must be rejected")
        self.assertIn("33,488.80", result["en"])  # template kept

    def test_state_carries_explanations(self):
        self.assertTrue(self.state["explanation_en"])
        self.assertTrue(self.state["explanation_bn"])
        self.assertTrue(self.state["explanation_meta"]["grounded"])
        self.assertFalse(self.state["llm_used"])


class TestLLMFallbackIntent(unittest.TestCase):
    """The demo utterance the deterministic parser cannot parse; a stubbed,
    schema-validated LLM resolves it."""

    UTTERANCE = "please send half of my salary to my mother this month"

    def test_deterministic_parser_finds_nothing(self):
        parsed = orchestrator.intent_parser.parse_intent(self.UTTERANCE)
        self.assertIsNone(parsed["amount"])
        self.assertIsNone(parsed["payout_method"])

    def test_llm_fallback_parses_and_labels(self):
        stub = type("StubLLM", (), {
            "is_enabled": staticmethod(lambda: True),
            "INTENT_SCHEMA": llm.INTENT_SCHEMA,
            "complete_json": staticmethod(lambda prompt, schema, **kw: (dict(VALID_INTENT), None)),
        })()
        with patch.object(orchestrator, "llm", stub):
            state = orchestrator.run("quote", text=self.UTTERANCE)
        self.assertTrue(state["llm_used"])
        self.assertEqual(state["amount"], 500)
        self.assertTrue(state["parsed_intent"]["llm_fallback"])

    def test_malformed_llm_reply_falls_back_gracefully(self):
        stub = type("StubLLM", (), {
            "is_enabled": staticmethod(lambda: True),
            "INTENT_SCHEMA": llm.INTENT_SCHEMA,
            "complete_json": staticmethod(lambda prompt, schema, **kw: (None, "invalid-json")),
        })()
        with patch.object(orchestrator, "llm", stub):
            state = orchestrator.run("quote", text=self.UTTERANCE)
        self.assertFalse(state["llm_used"])
        # graceful degradation: the corridor default is applied (labeled in the log)
        self.assertEqual(state["amount"], 1000.0)
        joined = " ".join(state["explanation_log"])
        self.assertIn("please rephrase", joined.lower())
        self.assertIn("default", joined.lower())


class TestSourcedRAG(unittest.TestCase):
    ALLOWED = {"bb.org.bd", "www.bb.org.bd", "ofac.treasury.gov", "www.iso20022.org", "iso20022.org"}

    def test_every_citation_has_an_allowed_domain(self):
        result = regulatory_rag.retrieve("2.5 percent government cash incentive formal remittance")
        self.assertTrue(result["passages"])
        self.assertIn(result["engine"], ("all-MiniLM-L6-v2", "lexical-ngram-tf"))
        for passage in result["passages"]:
            self.assertTrue(passage.get("domain"), f"chunk {passage['id']} has no source domain")
            self.assertIn(passage["domain"], self.ALLOWED)

    def test_ofac_query_cites_ofac_source(self):
        result = regulatory_rag.retrieve("fuzzy name matching over-blocking human review")
        self.assertTrue(any("OFAC" in p["title"] or p["domain"] == "ofac.treasury.gov"
                            for p in result["passages"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
