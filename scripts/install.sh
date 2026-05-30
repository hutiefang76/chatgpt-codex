#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

python3 -m venv .venv

cat > .venv/bin/chatgpt-codex <<MSG
#!/usr/bin/env bash
export PYTHONPATH="$ROOT\${PYTHONPATH:+:\$PYTHONPATH}"
exec "$ROOT/.venv/bin/python" -m chatgpt_codex "\$@"
MSG
chmod +x .venv/bin/chatgpt-codex

cat <<'MSG'
chatgpt-codex installed for macOS.
chatgpt-codex 已完成 macOS 安装。

Next:
下一步:
  . .venv/bin/activate
  chatgpt-codex channel register --workspace /absolute/path/to/project --public-base-url https://actions.example.com
  chatgpt-codex serve
MSG
