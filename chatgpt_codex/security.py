"""Security helpers for paths, tokens, and command filtering.

路径、token 和命令过滤相关的安全辅助函数。
"""

import re
import secrets
from pathlib import Path


def generate_token() -> str:
    """Create a URL-safe bearer token.

    生成 URL 安全的 bearer token。
    """

    return secrets.token_urlsafe(32)


class PathSandbox:
    """Resolve user-supplied paths without letting them escape the workspace.

    解析用户传入的路径，并确保它们不能逃逸出 workspace。
    """

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace).expanduser().resolve()

    def resolve(self, path: str) -> Path:
        requested = Path(path or ".").expanduser()
        if requested.is_absolute():
            candidate = requested.resolve()
        else:
            candidate = (self.workspace / requested).resolve()
        try:
            candidate.relative_to(self.workspace)
        except ValueError as exc:
            raise ValueError(f"path is outside workspace: {path}") from exc
        return candidate

    def relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.workspace).as_posix() or "."


class CommandPolicy:
    """Block common destructive commands before they reach the shell.

    在命令进入 shell 之前拦截常见危险命令。
    """

    # These patterns are intentionally conservative. They are a guardrail, not
    # a full shell sandbox.
    # 这些规则刻意保守：它们是防护栏，不是完整的 shell 沙箱。
    DEFAULT_DENY_PATTERNS = (
        r"\brm\s+-[^;&|]*r[^;&|]*f\b",
        r"\bgit\s+reset\s+--hard\b",
        r"\bgit\s+clean\s+-[^;&|]*f\b",
        r"\bsudo\b",
        r"\bsu\b",
        r"\bshutdown\b",
        r"\breboot\b",
        r"\bhalt\b",
        r"\b(?:del|erase)\b(?=[^;&|]*\s/[sq]\b)",
        r"\b(?:rmdir|rd)\b(?=[^;&|]*\s/[sq]\b)",
        r"\bremove-item\b(?=[^;&|]*-recurse\b)(?=[^;&|]*-force\b)",
        r"\bformat-volume\b",
        r"\bclear-disk\b",
        r"\brestart-computer\b",
        r"\bstop-computer\b",
        r"\bmkfs(?:\.[A-Za-z0-9_+-]+)?\b",
        r"\bdiskutil\s+erase",
        r"\bchmod\s+-R\s+777\b",
        r"\bchown\s+-R\b",
        r":\(\)\s*\{\s*:\|:",
    )

    def __init__(self, deny_patterns=None):
        self.deny_patterns = tuple(deny_patterns or self.DEFAULT_DENY_PATTERNS)

    def validate(self, command: str) -> str:
        normalized = (command or "").strip()
        if not normalized:
            raise ValueError("command is required")
        for pattern in self.deny_patterns:
            if re.search(pattern, normalized, flags=re.IGNORECASE):
                raise ValueError(f"command is blocked by safety policy: {pattern}")
        return normalized
