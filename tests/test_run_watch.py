import importlib.util
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


if __name__ == "__main__":
    unittest.main()
