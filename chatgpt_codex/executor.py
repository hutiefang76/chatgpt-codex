import subprocess
from pathlib import Path
from typing import Dict

from .security import CommandPolicy, PathSandbox


class CommandExecutor:
    """Run shell commands inside the workspace after safety checks.

    通过安全检查后，在 workspace 内执行 shell 命令。
    """

    def __init__(self, workspace: Path, policy=None):
        self.sandbox = PathSandbox(Path(workspace))
        self.policy = policy or CommandPolicy()

    def run(self, command: str, cwd: str = ".", timeout_seconds: int = 60, max_output: int = 20000) -> Dict[str, object]:
        safe_command = self.policy.validate(command)
        safe_cwd = self.sandbox.resolve(cwd)
        completed = subprocess.run(
            safe_command,
            cwd=str(safe_cwd),
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(1, int(timeout_seconds or 60)),
        )
        stdout, stdout_truncated = _truncate(completed.stdout, max_output)
        stderr, stderr_truncated = _truncate(completed.stderr, max_output)
        return {
            "command": safe_command,
            "cwd": self.sandbox.relative(safe_cwd),
            "exit_code": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
        }


def _truncate(value: str, max_output: int):
    limit = max(1, int(max_output or 20000))
    if len(value) <= limit:
        return value, False
    return value[:limit], True
