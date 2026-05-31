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

    def test_setup_command_is_wired_for_product_flow(self):
        payload = self._run_self_test()
        checks = {item["name"]: item["ok"] for item in payload["checks"]}
        self.assertTrue(checks["parses_setup_wait_seconds"])
        self.assertTrue(checks["setup_timeout_step_detects_challenge"])
        self.assertTrue(checks["parses_setup_fallback"])
        self.assertTrue(checks["builder_challenge_fallback_after_grace"])
        self.assertTrue(checks["builder_fallback_handoff_is_machine_readable"])

    def test_smoke_is_not_just_url_open(self):
        script = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("SMOKE_PROMPT", script)
        self.assertIn("workspace_status", script)
        self.assertIn("isSmokeSuccessful", script)
        self.assertNotIn("ok: Boolean(targetUrl)", script)

    def test_setup_attempts_action_automation_before_manual_fallback(self):
        script = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("attemptActionSetup", script)
        self.assertIn("action_attempt", script)
        self.assertIn("schema_textarea", script)
        self.assertIn("auth_token", script)
        self.assertIn("configure_fields_challenge", script)

    @unittest.skipUnless(shutil.which("npx"), "npx is required to test the packaged Playwright load path")
    def test_self_test_passes_through_npx_package_playwright(self):
        result = subprocess.run(
            ["npx", "--yes", "--package", "playwright", "node", str(SCRIPT), "self-test"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"], msg=result.stdout)
        self.assertTrue(payload["playwright_loaded"], msg=result.stdout)
        checks = {item["name"]: item["ok"] for item in payload["checks"]}
        self.assertTrue(checks["playwright_has_chromium"], msg=result.stdout)


if __name__ == "__main__":
    unittest.main()
