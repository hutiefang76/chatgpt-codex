import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "chatgpt_builder_playwright.mjs"


@unittest.skipUnless(shutil.which("node"), "node is required to run the Builder bridge self-test")
class PlaywrightScriptSelfTest(unittest.TestCase):
    """Guards the pure logic of the Playwright Builder bridge.

    The browser flow needs Node + Playwright + a real ChatGPT login and cannot be
    unit tested, but the decision logic can. In particular `saved_gpt_url_detected`
    guards the regression where `builder smoke` could never find a saved GPT URL.
    """

    def _run_self_test(self):
        result = subprocess.run(
            ["node", str(SCRIPT), "self-test"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        return json.loads(result.stdout)

    def test_self_test_passes(self):
        payload = self._run_self_test()
        self.assertTrue(payload["ok"], msg=json.dumps(payload, ensure_ascii=False))

    def test_saved_gpt_url_detection_is_wired(self):
        payload = self._run_self_test()
        checks = {item["name"]: item["ok"] for item in payload["checks"]}
        # smoke can only reach a saved GPT if this detection works both ways.
        self.assertTrue(checks["saved_gpt_url_detected"])
        self.assertTrue(checks["editor_url_not_saved"])
        self.assertTrue(checks["empty_url_not_saved"])

    def test_builder_fields_and_redaction(self):
        payload = self._run_self_test()
        checks = {item["name"]: item["ok"] for item in payload["checks"]}
        self.assertTrue(checks["schema_url"])
        self.assertTrue(checks["privacy_url"])
        self.assertTrue(checks["redacts_secrets"])


if __name__ == "__main__":
    unittest.main()
