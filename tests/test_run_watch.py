import importlib.util
import os
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_watch.py"
spec = importlib.util.spec_from_file_location("run_watch", MODULE_PATH)
run_watch = importlib.util.module_from_spec(spec)
sys.modules["run_watch"] = run_watch
spec.loader.exec_module(run_watch)


class RunWatchTests(unittest.TestCase):
    def test_extract_json_from_markdown_fence(self):
        text = '```json\n{"offers": [], "best_real_use": []}\n```'
        data = run_watch.extract_json(text)
        self.assertEqual(data["offers"], [])

    def test_extract_json_from_sentinel_markers(self):
        text = 'BEGIN_AI_DEALS_JSON\n{"offers": [], "best_real_use": []}\nEND_AI_DEALS_JSON'
        data = run_watch.extract_json(text)
        self.assertEqual(data["offers"], [])

    def test_call_gemini_does_not_force_json_mime_with_google_search(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn("google_search", source)
        call_section = source[source.index("def call_gemini"):source.index("def sample_payload")]
        config_section = call_section[call_section.index("config = types.GenerateContentConfig"):call_section.index("response = client.models.generate_content")]
        self.assertNotIn("response_mime_type", config_section)
        self.assertNotIn("response_schema", config_section)

    def test_extract_json_rejects_truncated_json(self):
        with self.assertRaises(Exception):
            run_watch.extract_json('{"offers":[{"offer":"abc}')

    def test_split_text_respects_limit(self):
        chunks = run_watch.split_text("a" * 5000, limit=1900)
        self.assertEqual(len(chunks), 3)
        self.assertTrue(all(len(chunk) <= 1900 for chunk in chunks))

    def test_diff_detects_new_and_modified(self):
        raw = {
            "generated_title": "test",
            "generated_summary": "test",
            "offers": [
                {
                    "rank": 1,
                    "offer": "Gemini API",
                    "provider": "Google",
                    "type": "API LLM",
                    "region": "Monde",
                    "gain": "Free tier",
                    "conditions_limits": "limites connues",
                    "problems_traps": "non précisé",
                    "usage_score": 4,
                    "validity": "non précisé",
                    "official_link": "https://ai.google.dev/",
                    "community_source": "non précisé",
                }
            ],
        }
        current = run_watch.normalize_payload(raw)
        previous = run_watch.normalize_payload(raw)
        self.assertFalse(run_watch.diff_payload(previous, current).changed)

        changed_raw = dict(raw)
        changed_raw["offers"] = [dict(raw["offers"][0], gain="Free tier mis à jour")]
        changed = run_watch.normalize_payload(changed_raw)
        diff = run_watch.diff_payload(previous, changed)
        self.assertTrue(diff.changed)
        self.assertEqual(len(diff.modified_offers), 1)

    def test_discord_messages_respect_limit(self):
        payload = run_watch.normalize_payload({
            "generated_title": "test",
            "generated_summary": "test",
            "offers": [
                {
                    "rank": 1,
                    "offer": "Very Long Offer",
                    "provider": "Provider",
                    "type": "API",
                    "region": "Monde",
                    "gain": "x" * 2500,
                    "conditions_limits": "y" * 2500,
                    "problems_traps": "z" * 2500,
                    "usage_score": 5,
                    "validity": "non précisé",
                    "official_link": "https://example.com",
                    "community_source": "non précisé",
                }
            ],
        })
        diff = run_watch.DiffResult(True, payload["offers"], [], [])
        messages = run_watch.build_discord_messages(diff, payload)
        self.assertTrue(messages)
        self.assertTrue(all(len(message) <= run_watch.DISCORD_CONTENT_LIMIT for message in messages))

    def test_sample_payload_normalizes(self):
        payload = run_watch.sample_payload()
        self.assertIn("offers", payload)
        self.assertEqual(len(payload["offers"]), 1)


if __name__ == "__main__":
    unittest.main()

class DiscordV4Tests(unittest.TestCase):
    def _payload_many(self, n=17):
        return run_watch.normalize_payload({
            "generated_title": "test",
            "generated_summary": "test",
            "offers": [
                {
                    "rank": i,
                    "offer": f"Offer {i}",
                    "provider": f"Provider {i}",
                    "type": "API LLM",
                    "region": "Monde",
                    "gain": "Free tier utile pour freelance solo",
                    "conditions_limits": "limites officielles à vérifier",
                    "problems_traps": "quota faible possible",
                    "usage_score": 5 if i <= 5 else 3,
                    "validity": "non précisé",
                    "official_link": f"https://example.com/{i}",
                    "community_source": "non précisé",
                }
                for i in range(1, n + 1)
            ],
            "best_real_use": ["a", "b", "c", "d", "e"],
            "riskiest_or_unstable": ["risk"],
            "watchlist": ["watch 1", "watch 2", "watch 3"],
            "critical_sources_used": ["source"],
        })

    def test_discord_v4_mentions_every_new_offer_name(self):
        payload = self._payload_many(17)
        diff = run_watch.DiffResult(True, payload["offers"], [], [])
        messages = run_watch.build_discord_messages(diff, payload)
        joined = "\n".join(messages)
        for i in range(1, 18):
            self.assertIn(f"Offer {i}", joined)
        self.assertTrue(all(len(message) <= run_watch.DISCORD_CONTENT_LIMIT for message in messages))

    def test_discord_report_filename_contains_counts(self):
        payload = self._payload_many(2)
        diff = run_watch.DiffResult(True, payload["offers"], [], [])
        filename = run_watch.discord_report_filename(diff, payload)
        self.assertIn("new2-mod0-out0", filename)
        self.assertTrue(filename.endswith(".md"))
