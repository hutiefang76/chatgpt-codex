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

    # These patterns are a best-effort guardrail, NOT a security boundary. With
    # shell=True a determined caller can always bypass a deny-list (other tools,
    # encodings, scripts). The real boundary is per-Action approval in ChatGPT
    # plus running against one scoped workspace, never your home directory.
    # 这些规则只是尽力而为的防护栏，不是安全边界。shell=True 下黑名单总能被绕过；
    # 真正的边界是 ChatGPT 内逐次人工批准 Action + 只对单个受限 workspace 运行。
    DEFAULT_DENY_PATTERNS = (
        # rm with recursive AND force, in any flag order or long form
        # (catches -rf, -fr, -r -f, --recursive --force, ...).
        r"\brm\b(?=[^;&|]*(?:--recursive|-\w*[rR]))(?=[^;&|]*(?:--force|-\w*f))",
        r"\bdd\b[^;&|]*\bof=",
        r"\bfind\b[^;&|]*\s-delete\b",
        r">\s*/dev/(?:sd|hd|vd|xvd|nvme|disk|mapper)",
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
