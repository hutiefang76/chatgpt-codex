#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

TARGET=".chatgpt-codex/permissions.json"
FORCE=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --output)
      TARGET="$2"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [ -e "$TARGET" ] && [ "$FORCE" -ne 1 ]; then
  echo "$TARGET already exists. Use --force to overwrite." >&2
  exit 1
fi

mkdir -p "$(dirname "$TARGET")"
cp permissions.example.json "$TARGET"

cat <<MSG
Permissions template written:
授权模板已写入:
  $TARGET

Edit this file, or replace it by running:
编辑此文件，或运行下面命令替换为自动生成版本:
  chatgpt-codex authorize --workspace /absolute/path/to/project --operating-system macos --access-plan built-in-quick-tunnel --public-base-url https://actions.example.com --allow-browser-automation --allow-start-services --allow-install-helpers --allow-workspace-write --allow-command-execution --force
MSG
