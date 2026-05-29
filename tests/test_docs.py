from pathlib import Path
import json
import unittest


class DocumentationTests(unittest.TestCase):
    def test_docs_do_not_reference_external_project_comparisons(self):
        root = Path(__file__).resolve().parents[1]
        docs = [
            root / "README.md",
            root / "AGENTS.md",
            root / "CLAUDE.md",
            root / "docs" / "AI_NATIVE.md",
            root / "skills" / "chatgpt-codex" / "SKILL.md",
            root / "skills" / "chatgpt-codex" / "references" / "agent-handoff.md",
            root / "docs" / "superpowers" / "plans" / "2026-05-29-chatgpt-codex.md",
        ]
        forbidden = [
            "coding " + "tools",
            "coding" + "-tools",
            "m" + "cp",
            "similar " + "projects",
            "other " + "projects",
            "independent " + "from",
            "其他" + "开源",
            "开源" + "项目",
            "独" + "立于",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8").lower()
            for term in forbidden:
                with self.subTest(path=path.name, term=term):
                    self.assertNotIn(term, content)

    def test_skill_has_complete_metadata_and_no_template_todos(self):
        root = Path(__file__).resolve().parents[1]
        skill = root / "skills" / "chatgpt-codex" / "SKILL.md"
        metadata = root / "skills" / "chatgpt-codex" / "agents" / "openai.yaml"

        skill_content = skill.read_text(encoding="utf-8")
        metadata_content = metadata.read_text(encoding="utf-8")

        self.assertIn("name: chatgpt-codex", skill_content)
        self.assertIn("description:", skill_content)
        self.assertNotIn("TODO", skill_content)
        self.assertIn("Use $chatgpt-codex", metadata_content)

    def test_readme_clarifies_cloudflared_is_not_required_for_local_server(self):
        root = Path(__file__).resolve().parents[1]
        readme = (root / "README.md").read_text(encoding="utf-8")

        self.assertIn("The local server runs with only the Python standard library", readme)
        self.assertIn("ChatGPT web cannot reach `localhost` directly", readme)
        self.assertIn("only for the built-in `chatgpt-codex tunnel` command", readme)
        self.assertNotIn("only optional " + "external tool", readme.lower())
        self.assertNotIn("唯一" + "可选" + "的外部工具", readme)

    def test_docs_include_macos_and_windows_setup_paths(self):
        root = Path(__file__).resolve().parents[1]
        readme = (root / "README.md").read_text(encoding="utf-8")
        skill = (root / "skills" / "chatgpt-codex" / "SKILL.md").read_text(encoding="utf-8")

        self.assertTrue((root / "scripts" / "install.sh").exists())
        self.assertTrue((root / "scripts" / "install.ps1").exists())
        self.assertIn("macOS", readme)
        self.assertIn("Windows PowerShell", readme)
        self.assertIn(".\\.venv\\Scripts\\Activate.ps1", readme)
        self.assertIn("py -3 -m unittest discover -s tests", readme)
        self.assertIn("Chrome human login to ChatGPT", skill)
        self.assertIn("chatgpt-codex.<domain>", skill)
        self.assertIn("Do not ask the user to choose an operating system", skill)
        self.assertIn("chatgpt-codex authorize", readme)
        self.assertIn(".chatgpt-codex/permissions.json", readme)
        self.assertIn("chatgpt-codex open-chatgpt", readme)
        self.assertIn("chatgpt-codex workspace add", readme)
        self.assertIn("switch_workspace", readme)
        self.assertIn("built-in-quick-tunnel", skill)

    def test_docs_define_minimal_human_inputs_consistently(self):
        root = Path(__file__).resolve().parents[1]
        files = [
            root / "README.md",
            root / "AGENTS.md",
            root / "CLAUDE.md",
            root / "docs" / "AI_NATIVE.md",
            root / "skills" / "chatgpt-codex" / "SKILL.md",
            root / "skills" / "chatgpt-codex" / "references" / "agent-handoff.md",
        ]

        for path in files:
            content = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn("Chrome", content)
                self.assertIn("ChatGPT", content)
                self.assertIn("workspace", content)
                self.assertIn("Cloudflare", content)
                self.assertIn("chatgpt-codex.<domain>", content)
                self.assertIn("temporary HTTPS tunnel", content)

    def test_root_permissions_template_and_helpers_exist(self):
        root = Path(__file__).resolve().parents[1]
        template_path = root / "permissions.example.json"
        template = json.loads(template_path.read_text(encoding="utf-8"))
        readme = (root / "README.md").read_text(encoding="utf-8")

        self.assertTrue(template_path.exists())
        self.assertTrue((root / "scripts" / "prepare-permissions.sh").exists())
        self.assertTrue((root / "scripts" / "prepare-permissions.ps1").exists())
        self.assertEqual(template["access_plan"], "built-in-quick-tunnel")
        self.assertIn("permissions.example.json", readme)
        self.assertIn("prepare-permissions.ps1", readme)
        self.assertNotIn("password", template_path.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
