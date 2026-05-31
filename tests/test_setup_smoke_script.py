import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "setup-smoke.py"


class SetupSmokeScriptTests(unittest.TestCase):
    def test_script_runs_setup_smoke_command(self):
        result = subprocess.run(
            ["python3", str(SCRIPT)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"], msg=result.stdout)


if __name__ == "__main__":
    unittest.main()
