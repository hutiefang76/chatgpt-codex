#!/usr/bin/env python3
"""Run deterministic local setup acceptance checks.

运行确定性的本地配置验收。
"""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from chatgpt_codex.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main(["setup-smoke", *sys.argv[1:]]))
