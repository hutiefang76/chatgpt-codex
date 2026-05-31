import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chatgpt_codex.builder import (
    builder_route_map_path,
    builder_state_path,
    make_builder_payload,
    playwright_profile_dir,
    redact_secret,
)
from chatgpt_codex.cli import main
from chatgpt_codex.config import AppConfig, load_config


def run_quietly(args):
    with contextlib.redirect_stdout(io.StringIO()):
        return main(args)


class BuilderAutomationTests(unittest.TestCase):
    def test_builder_payload_contains_action_fields_without_leaking_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            config = AppConfig(
                token="secret-token-that-must-not-leak",
                workspaces={"demo": workspace},
                active_workspace="demo",
                public_base_url="https://actions.example.com/",
            )

            payload = make_builder_payload(config)
            serialized = json.dumps(payload, ensure_ascii=False)

            self.assertEqual(payload["gpt"]["name"], "Local Coding Bridge")
            self.assertEqual(payload["action"]["schema_import_url"], "https://actions.example.com/openapi.json")
            self.assertEqual(payload["action"]["privacy_policy_url"], "https://actions.example.com/privacy")
            self.assertEqual(payload["action"]["authentication"], {"type": "api_key", "auth_type": "bearer"})
            self.assertEqual(payload["visibility"], "private")
            self.assertTrue(payload["token_configured"])
            self.assertNotIn("secret-token-that-must-not-leak", serialized)

    def test_builder_payload_can_include_token_only_when_explicitly_requested(self):
        config = AppConfig(
            token="secret-token-for-builder-field",
            workspaces={"demo": Path.cwd()},
            active_workspace="demo",
            public_base_url="https://actions.example.com",
        )

        payload = make_builder_payload(config, include_token=True)

        self.assertEqual(payload["action"]["api_key"], "secret-token-for-builder-field")

    def test_redact_secret_removes_sensitive_values_from_nested_route_logs(self):
        value = {
            "headers": {
                "authorization": "Bearer secret",
                "cookie": "session=secret",
                "content-type": "application/json",
            },
            "postData": "{\"api_key\":\"secret\",\"name\":\"Local Coding Bridge\"}",
            "url": "https://chatgpt.com/backend-api/gizmos",
        }

        redacted = redact_secret(value)
        serialized = json.dumps(redacted, ensure_ascii=False)

        self.assertIn("content-type", serialized)
        self.assertIn("Local Coding Bridge", serialized)
        self.assertNotIn("Bearer secret", serialized)
        self.assertNotIn("session=secret", serialized)
        self.assertNotIn("\"api_key\":\"secret\"", serialized)

    def test_builder_paths_are_local_private_project_files_or_user_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            self.assertEqual(builder_state_path(root), root / ".chatgpt-codex" / "builder.json")
            self.assertEqual(builder_route_map_path(root), root / ".chatgpt-codex" / "builder-routes.json")

        with mock.patch("chatgpt_codex.builder.platform.system", return_value="Darwin"):
            mac_path = playwright_profile_dir()
        with mock.patch.dict("os.environ", {"LOCALAPPDATA": r"C:\Users\me\AppData\Local"}, clear=False):
            with mock.patch("chatgpt_codex.builder.platform.system", return_value="Windows"):
                win_path = playwright_profile_dir()

        self.assertIn("Application Support", str(mac_path))
        self.assertIn("chatgpt-codex", str(mac_path))
        self.assertIn("playwright-profile", str(mac_path))
        self.assertIn("chatgpt-codex", str(win_path))
        self.assertIn("playwright-profile", str(win_path))

    def test_builder_payload_cli_outputs_json_without_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            run_quietly(
                [
                    "--config",
                    str(config_path),
                    "init",
                    "--workspace",
                    str(workspace),
                    "--workspace-name",
                    "demo",
                    "--public-base-url",
                    "https://actions.example.com",
                ]
            )
            token = load_config(config_path).token
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "builder", "payload", "--json"])

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["action"]["schema_import_url"], "https://actions.example.com/openapi.json")
            self.assertEqual(payload["automation"]["primary"], "playwright")
            self.assertIn("hybrid", payload["automation"]["submit_modes"])
            self.assertNotIn(token, stdout.getvalue())

    def test_builder_dry_run_commands_point_to_playwright_script_without_leaking_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            run_quietly(
                [
                    "--config",
                    str(config_path),
                    "init",
                    "--workspace",
                    str(workspace),
                    "--workspace-name",
                    "demo",
                    "--public-base-url",
                    "https://actions.example.com",
                ]
            )
            token = load_config(config_path).token

            for command in [
                ["builder", "sniff", "--dry-run"],
                ["builder", "configure", "--mode", "hybrid", "--dry-run"],
                ["builder", "setup", "--mode", "hybrid", "--wait-seconds", "7", "--dry-run"],
                ["builder", "smoke", "--dry-run"],
            ]:
                stdout = io.StringIO()
                with self.subTest(command=command):
                    with contextlib.redirect_stdout(stdout):
                        exit_code = main(["--config", str(config_path), *command])

                    payload = json.loads(stdout.getvalue())
                    self.assertEqual(exit_code, 0)
                    self.assertIn("scripts/chatgpt_builder_playwright.mjs", " ".join(payload["command"]))
                    self.assertIn("--config", payload["command"])
                    self.assertNotIn(token, stdout.getvalue())

                    if command[1] == "setup":
                        self.assertIn("setup", payload["command"])
                        self.assertIn("--mode", payload["command"])
                        self.assertEqual(payload["command"][payload["command"].index("--mode") + 1], "hybrid")
                        self.assertIn("--wait-seconds", payload["command"])
                        self.assertEqual(payload["command"][payload["command"].index("--wait-seconds") + 1], "7")

    def test_builder_runtime_commands_install_playwright_browser_before_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            run_quietly(["--config", str(config_path), "init", "--workspace", str(workspace)])

            with mock.patch("chatgpt_codex.cli._playwright_browser_cache_exists", return_value=False):
                with mock.patch("chatgpt_codex.cli.subprocess.call", side_effect=[0, 0]) as calls:
                    exit_code = main(["--config", str(config_path), "builder", "doctor"])

            self.assertEqual(exit_code, 0)
            install_command = calls.call_args_list[0].args[0]
            runtime_command = calls.call_args_list[1].args[0]
            self.assertEqual(install_command[-3:], ["playwright", "install", "chromium"])
            self.assertIn("chatgpt_builder_playwright.mjs", " ".join(runtime_command))

    def test_builder_runtime_skips_browser_install_when_cache_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            run_quietly(["--config", str(config_path), "init", "--workspace", str(workspace)])

            with mock.patch("chatgpt_codex.cli._playwright_browser_cache_exists", return_value=True):
                with mock.patch("chatgpt_codex.cli.subprocess.call", return_value=0) as call:
                    exit_code = main(["--config", str(config_path), "builder", "doctor"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(len(call.call_args_list), 1)
            self.assertIn("chatgpt_builder_playwright.mjs", " ".join(call.call_args.args[0]))


if __name__ == "__main__":
    unittest.main()
