import contextlib
import io
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from chatgpt_codex.cli import main
import chatgpt_codex.cli as cli
from chatgpt_codex.config import AppConfig, load_config, load_permissions
from chatgpt_codex.server import create_server


def run_quietly(args):
    with contextlib.redirect_stdout(io.StringIO()):
        return main(args)


class CliTests(unittest.TestCase):
    def test_init_writes_private_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--config",
                        str(config_path),
                        "init",
                        "--workspace",
                        str(workspace),
                        "--public-base-url",
                        "https://actions.example.com",
                    ]
                )

            config = load_config(config_path)
            raw_config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 0)
            self.assertEqual(config.workspace, workspace.resolve())
            self.assertEqual(config.active_workspace, "workspace")
            self.assertEqual(config.public_base_url, "https://actions.example.com")
            self.assertGreaterEqual(len(config.token), 32)
            self.assertNotIn("workspace", raw_config)
            self.assertIn("workspaces", raw_config)
            self.assertEqual(raw_config["active_workspace"], "workspace")
            self.assertEqual(raw_config["workspaces"]["workspace"], str(workspace.resolve()))

    def test_openapi_command_prints_importable_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            run_quietly(["--config", str(config_path), "init", "--workspace", str(workspace)])
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "openapi"])

            document = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertIn("/exec_command", document["paths"])

    def test_gpt_instructions_include_action_setup_fields(self):
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
                    "--public-base-url",
                    "https://actions.example.com",
                ]
            )
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "gpt-instructions"])

            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("https://actions.example.com/openapi.json", output)
            self.assertIn("Bearer", output)
            self.assertIn("Only me", output)
            self.assertIn("workspace_status", output)
            self.assertIn("switch_workspace", output)

    def test_workspace_cli_adds_lists_and_switches_authorized_workspaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            first = Path(tmp) / "first"
            second = Path(tmp) / "second"
            first.mkdir()
            second.mkdir()
            run_quietly(
                [
                    "--config",
                    str(config_path),
                    "init",
                    "--workspace",
                    str(first),
                    "--workspace-name",
                    "first",
                ]
            )

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--config",
                        str(config_path),
                        "workspace",
                        "add",
                        "--name",
                        "second",
                        "--path",
                        str(second),
                        "--activate",
                    ]
                )

            config = load_config(config_path)
            self.assertEqual(exit_code, 0)
            self.assertEqual(config.active_workspace, "second")
            self.assertEqual(config.workspace, second.resolve())
            self.assertIn("first", config.workspaces)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "workspace", "list"])

            listing = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(listing["active_workspace"], "second")
            self.assertEqual(len(listing["workspaces"]), 2)

    def test_app_config_requires_latest_workspace_registry_schema(self):
        with self.assertRaises(KeyError):
            AppConfig.from_dict({"workspace": "/tmp/legacy", "token": "secret-token"})

    def test_invalid_access_expiry_is_inactive_instead_of_crashing(self):
        config = AppConfig(
            token="secret-token",
            workspaces={"demo": Path.cwd()},
            active_workspace="demo",
            access_expires_at="not-a-date",
        )

        status = config.access_status()

        self.assertEqual(status["mode"], "invalid")
        self.assertFalse(status["active"])

    def test_status_prints_machine_readable_state_without_token(self):
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
                exit_code = main(["--config", str(config_path), "status"])

            status = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(status["configured"])
            self.assertTrue(status["token_configured"])
            self.assertTrue(status["access"]["active"])
            self.assertEqual(status["active_workspace"], "demo")
            self.assertEqual(status["openapi_url"], "https://actions.example.com/openapi.json")
            self.assertIn("builder_profile_path", status)
            self.assertIn("node_found", status)
            self.assertIn("npx_found", status)
            self.assertNotIn(token, stdout.getvalue())

    def test_cli_language_can_be_selected_for_machine_readable_status(self):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["--lang", "zh", "status"])

        status = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(status["language"], "zh")
        self.assertIn("chatgpt-codex --lang en status", status["language_examples"])
        self.assertIn("chatgpt-codex --lang zh status", status["language_examples"])

    def test_ai_commands_prints_machine_readable_command_catalog(self):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["ai-commands"])

        catalog = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertIn("setup", catalog)
        self.assertIn("workspace", catalog)
        self.assertIn("language", catalog)
        self.assertIn("chatgpt-codex --lang zh <command>", catalog["language"])
        self.assertIn("chatgpt-codex setup --workspace <path>", catalog["setup"])
        self.assertIn("chatgpt-codex status", catalog["inspect"])
        self.assertIn("chatgpt-codex access status", catalog["inspect"])
        self.assertIn("chatgpt-codex set-public-url <url>", catalog["routing"])
        self.assertIn("chatgpt-codex channel register --workspace <path> --public-base-url <url>", catalog["setup"])
        self.assertIn("chatgpt-codex channel status", catalog["inspect"])
        self.assertIn("chatgpt-codex channel renew", catalog["access"])
        self.assertIn("chatgpt-codex channel revoke", catalog["access"])
        self.assertIn("chatgpt-codex verify", catalog["inspect"])
        self.assertIn("chatgpt-codex api-smoke", catalog["inspect"])
        self.assertIn("chatgpt-codex access revoke", catalog["access"])
        self.assertIn("chatgpt-codex token", catalog["chatgpt_builder"])
        self.assertIn("chatgpt-codex chatgpt-preflight", catalog["chatgpt_builder"])
        self.assertIn("chatgpt-codex open-chatgpt-login", catalog["chatgpt_builder"])
        self.assertIn("chatgpt-codex setup-smoke", catalog["inspect"])

    def test_setup_dry_run_prints_single_command_product_plan_without_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--config",
                        str(config_path),
                        "setup",
                        "--workspace",
                        str(workspace),
                        "--builder-wait-seconds",
                        "12",
                        "--builder-challenge-grace-seconds",
                        "3",
                        "--dry-run",
                    ]
                )

            plan = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(plan["command"], "setup")
            self.assertEqual(plan["workspace"], str(workspace.resolve()))
            self.assertEqual(plan["builder_command"], "chatgpt-codex builder setup")
            self.assertEqual(plan["builder_fallback"], "auto")
            self.assertEqual(plan["builder_challenge_grace_seconds"], 3)
            self.assertIn("prepare_local_bridge", plan["steps"])
            self.assertIn("open_chatgpt_builder", plan["steps"])
            self.assertIn("smoke_test_saved_gpt", plan["steps"])
            self.assertFalse(plan["token_printed"])

    def test_setup_waits_for_public_route_before_verifying_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            args = type(
                "Args",
                (),
                {
                    "dry_run": False,
                    "run_setup_smoke": False,
                    "workspace": str(workspace),
                    "workspace_name": "demo",
                    "host": "127.0.0.1",
                    "port": 0,
                    "public_base_url": "",
                    "no_tunnel": False,
                    "cloudflared": "cloudflared",
                    "timeout": 10,
                    "route_attempts": 1,
                    "skip_builder": False,
                    "builder_mode": "ui",
                    "visibility": "private",
                    "builder_wait_seconds": 1,
                    "builder_fallback": "auto",
                    "builder_challenge_grace_seconds": 2,
                    "skip_smoke": False,
                    "smoke_wait_seconds": 1,
                    "force": False,
                },
            )()
            calls = []

            class FakeServer:
                server_port = 8767

                def serve_forever(self):
                    return None

                def shutdown(self):
                    calls.append("shutdown")

                def server_close(self):
                    calls.append("server_close")

            def fake_wait_health(*_):
                calls.append("wait_health")
                return False

            def fake_verify(*_):
                calls.append("verify_actions")
                return {"ok": False, "checks": []}

            with mock.patch("chatgpt_codex.cli.create_server", return_value=FakeServer()):
                with mock.patch("chatgpt_codex.cli._setup_public_route", return_value=("https://actions.example.com", None, None)):
                    with mock.patch("chatgpt_codex.cli._wait_health", side_effect=fake_wait_health):
                        with mock.patch("chatgpt_codex.cli._verify_actions", side_effect=fake_verify):
                            exit_code = cli._setup(args, config_path)

            self.assertEqual(exit_code, 1)
            self.assertIn("wait_health", calls)
            self.assertNotIn("verify_actions", calls)

    def test_setup_retries_quick_tunnel_when_first_public_route_is_unreachable(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            args = type(
                "Args",
                (),
                {
                    "dry_run": False,
                    "run_setup_smoke": False,
                    "workspace": str(workspace),
                    "workspace_name": "demo",
                    "host": "127.0.0.1",
                    "port": 0,
                    "public_base_url": "",
                    "no_tunnel": False,
                    "cloudflared": "cloudflared",
                    "timeout": 10,
                    "route_attempts": 2,
                    "skip_builder": True,
                    "builder_mode": "ui",
                    "visibility": "private",
                    "builder_wait_seconds": 1,
                    "builder_fallback": "auto",
                    "builder_challenge_grace_seconds": 2,
                    "skip_smoke": True,
                    "smoke_wait_seconds": 1,
                    "force": False,
                },
            )()
            calls = []

            class FakeServer:
                server_port = 8767

                def serve_forever(self):
                    return None

                def shutdown(self):
                    calls.append("shutdown")

                def server_close(self):
                    calls.append("server_close")

            class FakeThread:
                def join(self, timeout=None):
                    calls.append(f"join:{timeout}")

            class FakeProc:
                pass

            def fake_setup_public_route(*_):
                attempt = len([item for item in calls if item == "setup_public_route"]) + 1
                calls.append("setup_public_route")
                return f"https://actions-{attempt}.example.com", FakeProc(), FakeThread()

            def fake_wait_health(url, *_):
                calls.append(f"wait_health:{url}")
                return url == "https://actions-2.example.com"

            def fake_verify(*_):
                calls.append("verify_actions")
                return {"ok": True, "checks": []}

            with mock.patch("chatgpt_codex.cli.create_server", return_value=FakeServer()):
                with mock.patch("chatgpt_codex.cli._setup_public_route", side_effect=fake_setup_public_route):
                    with mock.patch("chatgpt_codex.cli._wait_health", side_effect=fake_wait_health):
                        with mock.patch("chatgpt_codex.cli._verify_actions", side_effect=fake_verify):
                            with mock.patch("chatgpt_codex.cli._terminate", side_effect=lambda _proc: calls.append("terminate")):
                                exit_code = cli._setup(args, config_path)

            self.assertEqual(exit_code, 0)
            self.assertEqual(calls.count("setup_public_route"), 2)
            self.assertIn("wait_health:https://actions-1.example.com", calls)
            self.assertIn("wait_health:https://actions-2.example.com", calls)
            self.assertIn("terminate", calls)
            self.assertIn("verify_actions", calls)

    def test_setup_keeps_bridge_running_when_builder_returns_agent_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            args = type(
                "Args",
                (),
                {
                    "dry_run": False,
                    "run_setup_smoke": False,
                    "workspace": str(workspace),
                    "workspace_name": "demo",
                    "host": "127.0.0.1",
                    "port": 0,
                    "public_base_url": "https://actions.example.com",
                    "no_tunnel": False,
                    "cloudflared": "cloudflared",
                    "timeout": 10,
                    "route_attempts": 1,
                    "skip_builder": False,
                    "builder_mode": "ui",
                    "visibility": "private",
                    "builder_wait_seconds": 1,
                    "builder_fallback": "auto",
                    "builder_challenge_grace_seconds": 2,
                    "skip_smoke": False,
                    "smoke_wait_seconds": 1,
                    "force": False,
                },
            )()
            calls = []

            class FakeServer:
                server_port = 8767

                def serve_forever(self):
                    calls.append("serve_forever")

                def shutdown(self):
                    calls.append("shutdown")

                def server_close(self):
                    calls.append("server_close")

            class FakeThread:
                def __init__(self, *_, **__):
                    pass

                def start(self):
                    calls.append("thread_start")

                def join(self, timeout=None):
                    calls.append(f"thread_join:{timeout}")

            fallback_payload = {
                "fallback_required": True,
                "fallback": {"kind": "chrome_or_computer_use"},
            }

            with mock.patch("chatgpt_codex.cli.create_server", return_value=FakeServer()):
                with mock.patch("chatgpt_codex.cli.threading.Thread", FakeThread):
                    with mock.patch("chatgpt_codex.cli._wait_health", return_value=True):
                        with mock.patch("chatgpt_codex.cli._verify_actions", return_value={"ok": True, "checks": []}):
                            with mock.patch("chatgpt_codex.cli._run_builder_runtime_result", return_value={"exit_code": 1, "payload": fallback_payload}):
                                with mock.patch("chatgpt_codex.cli._run_builder_runtime", side_effect=AssertionError("smoke must not run before fallback finishes")):
                                    exit_code = cli._setup(args, config_path)

            self.assertEqual(exit_code, 1)
            self.assertIn("thread_join:None", calls)
            self.assertIn("shutdown", calls)

    def test_setup_smoke_runs_deterministic_local_acceptance(self):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["setup-smoke"])

        result = json.loads(stdout.getvalue())
        check_names = [check["name"] for check in result["checks"]]
        self.assertEqual(exit_code, 0)
        self.assertTrue(result["ok"], msg=json.dumps(result, ensure_ascii=False))
        self.assertIn("local_server_verify", check_names)
        self.assertIn("api_smoke", check_names)
        self.assertIn("bootstrap_rebinds_workspace", check_names)
        self.assertIn("builder_configure_dry_run", check_names)
        self.assertIn("builder_setup_dry_run", check_names)
        self.assertIn("builder_smoke_dry_run", check_names)

    def test_chatgpt_preflight_reports_plan_and_builder_boundaries_without_token(self):
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
                exit_code = main(["--config", str(config_path), "chatgpt-preflight"])

            preflight = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(preflight["chatgpt_login"]["required"])
            self.assertIn("ChatGPT Plus", preflight["account_requirements"]["can_create_and_edit_gpts"])
            self.assertFalse(preflight["builder_automation"]["fully_configurable_by_local_api"])
            self.assertEqual(preflight["builder_fields"]["authentication"], "API key / Bearer")
            self.assertEqual(preflight["builder_fields"]["schema_import_url"], "https://actions.example.com/openapi.json")
            self.assertNotIn(token, stdout.getvalue())

    def test_builder_configure_dry_run_passes_wait_seconds(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            run_quietly(["--config", str(config_path), "init", "--workspace", str(workspace)])
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--config",
                        str(config_path),
                        "builder",
                        "configure",
                        "--mode",
                        "ui",
                        "--wait-seconds",
                        "7",
                        "--dry-run",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            command = payload["command"]
            self.assertEqual(exit_code, 0)
            self.assertIn("--wait-seconds", command)
            self.assertEqual(command[command.index("--wait-seconds") + 1], "7")

    def test_builder_setup_dry_run_passes_fallback_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            run_quietly(["--config", str(config_path), "init", "--workspace", str(workspace)])
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--config",
                        str(config_path),
                        "builder",
                        "setup",
                        "--fallback",
                        "auto",
                        "--challenge-grace-seconds",
                        "4",
                        "--dry-run",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            command = payload["command"]
            self.assertEqual(exit_code, 0)
            self.assertIn("--fallback", command)
            self.assertEqual(command[command.index("--fallback") + 1], "auto")
            self.assertIn("--challenge-grace-seconds", command)
            self.assertEqual(command[command.index("--challenge-grace-seconds") + 1], "4")

    def test_doctor_without_config_prints_next_step_instead_of_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "missing.json"
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "doctor"])

            output = stdout.getvalue()
            self.assertEqual(exit_code, 1)
            self.assertIn("config is missing", output)
            self.assertIn("chatgpt-codex channel register", output)

    def test_channel_register_status_revoke_and_renew(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--config",
                        str(config_path),
                        "channel",
                        "register",
                        "--workspace",
                        str(workspace),
                        "--workspace-name",
                        "demo",
                        "--public-base-url",
                        "https://actions.example.com/",
                    ]
                )
            registered = json.loads(stdout.getvalue())
            config = load_config(config_path)
            first_token = config.token
            self.assertEqual(exit_code, 0)
            self.assertTrue(registered["registered"])
            self.assertTrue(registered["active"])
            self.assertEqual(registered["token"], first_token)
            self.assertEqual(registered["public_base_url"], "https://actions.example.com")
            self.assertEqual(config.workspace, workspace.resolve())
            self.assertEqual(config.active_workspace, "demo")
            self.assertEqual(config.access_status()["mode"], "no_expiry")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "channel", "status"])
            status = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(status["registered"])
            self.assertTrue(status["token_configured"])
            self.assertNotIn(first_token, stdout.getvalue())

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "channel", "revoke"])
            revoked = json.loads(stdout.getvalue())
            revoked_config = load_config(config_path)
            self.assertEqual(exit_code, 0)
            self.assertFalse(revoked["active"])
            self.assertTrue(revoked["token_rotated"])
            self.assertNotEqual(revoked_config.token, first_token)
            self.assertNotIn(revoked_config.token, stdout.getvalue())

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "channel", "renew", "--public-base-url", "https://fresh.example.com"])
            renewed = json.loads(stdout.getvalue())
            renewed_config = load_config(config_path)
            self.assertEqual(exit_code, 0)
            self.assertTrue(renewed["active"])
            self.assertEqual(renewed["token"], renewed_config.token)
            self.assertEqual(renewed["public_base_url"], "https://fresh.example.com")
            self.assertEqual(renewed_config.access_status()["mode"], "no_expiry")

    def test_api_smoke_exercises_action_interfaces_without_existing_config(self):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["api-smoke"])

        result = json.loads(stdout.getvalue())
        check_names = [check["name"] for check in result["checks"]]
        self.assertEqual(exit_code, 0)
        self.assertTrue(result["ok"])
        self.assertIn("workspace_status", check_names)
        self.assertIn("write_file", check_names)
        self.assertIn("apply_patch", check_names)
        self.assertIn("exec_command", check_names)
        self.assertIn("switch_workspace", check_names)
        self.assertIn("path_escape_blocked", check_names)
        self.assertIn("dangerous_command_blocked", check_names)
        self.assertIn("expired_access_blocked", check_names)
        self.assertNotIn("api-smoke-token", stdout.getvalue())

    def test_access_commands_grant_revoke_and_rotate_without_leaking_status_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            run_quietly(["--config", str(config_path), "init", "--workspace", str(workspace), "--workspace-name", "demo"])
            original = load_config(config_path).token

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "access", "grant", "--ttl-minutes", "30"])
            granted = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(granted["access"]["active"])
            self.assertFalse(granted["token_rotated"])
            self.assertEqual(load_config(config_path).token, original)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "access", "status"])
            self.assertEqual(exit_code, 0)
            self.assertNotIn(original, stdout.getvalue())

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "access", "revoke"])
            revoked = json.loads(stdout.getvalue())
            after_revoke = load_config(config_path)
            self.assertEqual(exit_code, 0)
            self.assertFalse(revoked["access"]["active"])
            self.assertTrue(revoked["token_rotated"])
            self.assertNotEqual(after_revoke.token, original)
            self.assertNotIn(after_revoke.token, stdout.getvalue())

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "rotate-token", "--ttl-minutes", "15"])
            rotated = json.loads(stdout.getvalue())
            after_rotate = load_config(config_path)
            self.assertEqual(exit_code, 0)
            self.assertEqual(rotated["token"], after_rotate.token)
            self.assertTrue(rotated["access"]["active"])

    def test_set_public_url_preserves_token_and_workspaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            run_quietly(["--config", str(config_path), "init", "--workspace", str(workspace), "--workspace-name", "demo"])
            before = load_config(config_path)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "set-public-url", "https://new.example.com/"])

            after = load_config(config_path)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["public_base_url"], "https://new.example.com")
            self.assertEqual(after.token, before.token)
            self.assertEqual(after.workspaces, before.workspaces)

    def test_verify_checks_health_schema_and_read_only_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "hello.txt").write_text("hello", encoding="utf-8")
            run_quietly(["--config", str(config_path), "init", "--workspace", str(workspace), "--workspace-name", "demo"])
            config = load_config(config_path)
            config.port = 0
            server = create_server(config, config_path)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base_url = f"http://127.0.0.1:{server.server_port}"
                run_quietly(["--config", str(config_path), "set-public-url", base_url])
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    exit_code = main(["--config", str(config_path), "verify", "--base-url", base_url])

                result = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(result["ok"])
                self.assertEqual(len(result["checks"]), 3)
                self.assertTrue(all(check["ok"] for check in result["checks"]))
                self.assertEqual(result["checks"][1]["server_url"], base_url)
                self.assertNotIn("_content", stdout.getvalue())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_ai_native_alias_prints_agent_handoff(self):
        for command in ["agent-brief", "ai-native", "skills", "skill"]:
            with self.subTest(command=command):
                stdout = io.StringIO()

                with contextlib.redirect_stdout(stdout):
                    exit_code = main([command])

                output = stdout.getvalue()
                self.assertEqual(exit_code, 0)
                self.assertIn("Codex or Claude", output)
                self.assertIn("skills/chatgpt-codex/SKILL.md", output)
                self.assertIn("workspace path", output)
                self.assertIn("Playwright-profile human login to ChatGPT", output)
                self.assertIn("chatgpt-codex.<domain>", output)
                self.assertIn("public HTTPS", output)
                self.assertIn("ChatGPT Builder", output)

    def test_route_options_explain_cloudflared_and_domain_requirements(self):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["route-options"])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("built-in-quick-tunnel", output)
        self.assertIn("cloudflared required: yes", output)
        self.assertIn("custom-domain", output)
        self.assertIn("domain required: yes", output)

    def test_authorize_writes_permissions_without_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            workspace = Path(tmp) / "workspace"
            root.mkdir()
            workspace.mkdir()
            stdout = io.StringIO()
            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                with contextlib.redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "authorize",
                            "--workspace",
                            str(workspace),
                            "--operating-system",
                            "macos",
                            "--access-plan",
                            "built-in-quick-tunnel",
                            "--public-base-url",
                            "https://actions.example.com",
                            "--allow-browser-automation",
                            "--allow-start-services",
                            "--allow-install-helpers",
                            "--allow-workspace-write",
                            "--allow-command-execution",
                        ]
                    )
                permissions_path = root / ".chatgpt-codex" / "permissions.json"
                permissions = load_permissions(permissions_path)
            finally:
                os.chdir(previous_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(permissions.workspace, workspace.resolve())
            self.assertEqual(permissions.access_plan, "built-in-quick-tunnel")
            self.assertTrue(permissions.allow_browser_automation)
            self.assertTrue(permissions.allow_install_helpers)
            self.assertNotIn("password", permissions_path.read_text(encoding="utf-8").lower())

    def test_permissions_template_prints_and_writes_valid_json(self):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["permissions-template"])

        template = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(template["access_plan"], "built-in-quick-tunnel")
        self.assertIn("workspace", template)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "permissions.json"
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = main(["permissions-template", "--output", str(output)])

            written = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 0)
            self.assertEqual(written["public_base_url"], "https://actions.example.com")


if __name__ == "__main__":
    unittest.main()
