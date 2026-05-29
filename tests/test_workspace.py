import tempfile
import unittest
from pathlib import Path

from chatgpt_codex.workspace import WorkspaceTools


class WorkspaceToolsTests(unittest.TestCase):
    def test_lists_files_with_relative_paths(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            (root / "notes").mkdir()
            (root / "notes" / "a.txt").write_text("hello", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "ignored").write_text("secret", encoding="utf-8")

            result = WorkspaceTools(root).list_files(".", recursive=True, max_results=20)

            paths = [entry["path"] for entry in result["entries"]]
            self.assertIn("notes", paths)
            self.assertIn("notes/a.txt", paths)
            self.assertNotIn(".git/ignored", paths)
            self.assertFalse(result["truncated"])

    def test_reads_writes_and_searches_text(self):
        with tempfile.TemporaryDirectory() as workspace:
            tools = WorkspaceTools(Path(workspace))

            write_result = tools.write_file("src/app.py", "print('hello')\n")
            read_result = tools.read_file("src/app.py")
            search_result = tools.search_text("hello", path=".")

            self.assertEqual(write_result["bytes_written"], len("print('hello')\n".encode("utf-8")))
            self.assertEqual(read_result["content"], "print('hello')\n")
            self.assertEqual(search_result["matches"][0]["path"], "src/app.py")
            self.assertEqual(search_result["matches"][0]["line"], 1)

    def test_apply_patch_updates_file(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            (root / "README.md").write_text("old title\nbody\n", encoding="utf-8")
            tools = WorkspaceTools(root)

            result = tools.apply_patch(
                """*** Begin Patch
*** Update File: README.md
@@
-old title
+new title
 body
*** End Patch
"""
            )

            self.assertEqual(result["changed_files"], ["README.md"])
            self.assertEqual((root / "README.md").read_text(encoding="utf-8"), "new title\nbody\n")

    def test_apply_patch_rejects_escape(self):
        with tempfile.TemporaryDirectory() as workspace:
            tools = WorkspaceTools(Path(workspace))

            with self.assertRaises(ValueError):
                tools.apply_patch(
                    """*** Begin Patch
*** Update File: ../outside.txt
@@
-old
+new
*** End Patch
"""
                )


if __name__ == "__main__":
    unittest.main()

