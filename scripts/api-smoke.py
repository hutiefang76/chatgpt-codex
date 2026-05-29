#!/usr/bin/env python3
"""Run the interface-level smoke test.

运行接口级冒烟测试。
"""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from chatgpt_codex.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main(["api-smoke", *sys.argv[1:]]))
