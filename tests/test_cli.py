import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from chatgpt_codex.cli import main
from chatgpt_codex.config import AppConfig, load_config, load_permissions


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
            self.assertEqual(status["active_workspace"], "demo")
            self.assertEqual(status["openapi_url"], "https://actions.example.com/openapi.json")
            self.assertNotIn(token, stdout.getvalue())

    def test_ai_commands_prints_machine_readable_command_catalog(self):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["ai-commands"])

        catalog = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertIn("setup", catalog)
        self.assertIn("workspace", catalog)
        self.assertIn("chatgpt-codex status", catalog["inspect"])
        self.assertIn("chatgpt-codex token", catalog["chatgpt_builder"])

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
                self.assertIn("Chrome human login to ChatGPT", output)
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
