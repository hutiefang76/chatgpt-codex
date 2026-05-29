import tempfile
import unittest
from pathlib import Path

from chatgpt_codex.security import CommandPolicy, PathSandbox, generate_token


class SecurityTests(unittest.TestCase):
    def test_path_sandbox_rejects_escape(self):
        with tempfile.TemporaryDirectory() as workspace:
            sandbox = PathSandbox(Path(workspace))

            with self.assertRaises(ValueError) as raised:
                sandbox.resolve("../outside.txt")

            self.assertIn("outside workspace", str(raised.exception))

    def test_path_sandbox_accepts_nested_workspace_path(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace).resolve()
            sandbox = PathSandbox(root)

            resolved = sandbox.resolve("notes/today.md")

            self.assertEqual(resolved, root / "notes" / "today.md")

    def test_command_policy_rejects_destructive_commands(self):
        policy = CommandPolicy()

        for command in [
            "rm -rf /tmp/example",
            "git reset --hard",
            "sudo reboot",
            "mkfs.ext4 /dev/disk0",
            "del /s /q C:\\temp\\example",
            "rmdir /s /q C:\\temp\\example",
            "Remove-Item -Recurse -Force C:\\temp\\example",
            "Format-Volume -DriveLetter D",
            "Restart-Computer",
        ]:
            with self.subTest(command=command):
                with self.assertRaises(ValueError):
                    policy.validate(command)

    def test_command_policy_accepts_read_only_commands(self):
        policy = CommandPolicy()

        self.assertEqual(policy.validate("pwd && ls -la"), "pwd && ls -la")

    def test_generated_token_is_urlsafe_and_long_enough(self):
        token = generate_token()

        self.assertGreaterEqual(len(token), 32)
        self.assertRegex(token, r"^[A-Za-z0-9_-]+$")


if __name__ == "__main__":
    unittest.main()
