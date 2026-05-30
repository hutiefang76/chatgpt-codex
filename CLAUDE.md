# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Two modes of work / 两种工作模式

This repo has two distinct audiences — know which one you are in.

本仓库面向两类不同的使用者，先分清你在哪一类。

- **Operating the bridge as a product** (the common case): follow [skills/chatgpt-codex/SKILL.md](./skills/chatgpt-codex/SKILL.md), then [AGENTS.md](./AGENTS.md). That path collects the minimal human inputs — human login to ChatGPT in the Playwright persistent profile, a workspace path, optional Cloudflare browser login, optional Cloudflare-managed domain, and one local authorization — then detects the OS, picks a route (a temporary HTTPS tunnel by default, or `chatgpt-codex.<domain>` when a Cloudflare login and domain exist), starts the server, verifies it, and fills the ChatGPT Builder. Prefer the CLI (`chatgpt-codex channel register|status|serve|api-smoke`, `chatgpt-codex builder ...`) over ad-hoc steps.
- **作为产品来运行这座桥**（常见情况）：先看 SKILL.md，再看 AGENTS.md。
- **Developing this codebase** (everything below): build, test, and architecture guidance.
- **开发这套代码**（以下全部内容）：构建、测试与架构说明。

## Development commands

```bash
# Full test suite — stdlib unittest, 51 tests, ~4s
python3 -m unittest discover -s tests            # Windows: py -3 -m unittest discover -s tests

# A single module / class / method
python3 -m unittest tests.test_server
python3 -m unittest tests.test_server.ServerTests.test_server_requires_bearer_token_for_actions

# Run the CLI without installing (entry point: chatgpt_codex.cli:main)
python3 -m chatgpt_codex --help

# Interface-level smoke test: spins a server on a throwaway workspace and exercises
# every Action plus the safety blocks (auth, path escape, dangerous command, expiry)
python3 scripts/api-smoke.py                      # or: chatgpt-codex api-smoke

# Install: creates .venv + a `chatgpt-codex` wrapper. There are NO third-party deps to install.
./scripts/install.sh && . .venv/bin/activate      # Windows: scripts/install.ps1
```

Tests are plain `unittest.TestCase`s, so pytest discovers them too if you prefer. There is no configured linter or formatter — match the surrounding style.

## Architecture

A zero-dependency, standard-library HTTP server exposes bearer-protected, sandboxed file/search/patch/exec actions over one local workspace. A ChatGPT Custom GPT calls those actions through an imported OpenAPI document over a public HTTPS route; a Python→Node Playwright bridge configures the ChatGPT Builder web UI.

Request path for one Action: `ChatGPT → public HTTPS route (cloudflared tunnel or your own) → server.py Handler → bearer + access-TTL check → WorkspaceTools / CommandExecutor (path-sandboxed) → JSON`.

Modules (`chatgpt_codex/`):

- [cli.py](chatgpt_codex/cli.py) — argparse entry point and orchestration for every subcommand; also holds `verify`, `api-smoke`, and all human/agent handoff text. Large but flat: each command is a branch in `main()`.
- [config.py](chatgpt_codex/config.py) — `AppConfig` (token, `workspaces` name→path map, `active_workspace`, host/port, `public_base_url`, access TTL) and `SetupPermissions`; load/save under `.chatgpt-codex/`; the `ACCESS_PLANS` table.
- [server.py](chatgpt_codex/server.py) — `create_server()` → `ThreadingHTTPServer`. GET `/health`, `/openapi.json`, `/privacy` are open; every POST action requires `Authorization: Bearer <token>` and active access.
- [workspace.py](chatgpt_codex/workspace.py) — `WorkspaceTools`: list/read/write/search plus a small, deterministic `apply_patch` parser (exact-context hunks, no fuzzy matching); skips `IGNORED_NAMES`.
- [executor.py](chatgpt_codex/executor.py) — `CommandExecutor.run()`: shell exec with deny-list validation, sandboxed cwd, and output truncation.
- [security.py](chatgpt_codex/security.py) — `generate_token()`, `PathSandbox` (paths cannot escape the workspace), `CommandPolicy` (regex deny-list of destructive commands).
- [openapi.py](chatgpt_codex/openapi.py) — `make_openapi_document()`: the OpenAPI 3.1 spec served at `/openapi.json` and imported by ChatGPT Actions.
- [builder.py](chatgpt_codex/builder.py) — Builder field payloads, per-OS Playwright profile dir, secret redaction for sniffed routes.

Cross-cutting facts that aren't obvious from any single file:

1. **The config file is the live source of truth.** `server.py` re-reads `.chatgpt-codex/config.json` under a lock before every action (`reload_config_locked`). So `rotate-token`, `channel revoke/renew`, and `workspace switch` all take effect on an already-running `serve` process with no restart.
2. **Adding or changing an Action touches three places in lockstep:** the route + dispatch in `server.py`, the path + schemas in `openapi.py` (its operationIds are what ChatGPT calls), and the implementing method in `workspace.py` / `executor.py` / `config.py`. `_api_smoke` in `cli.py` exercises the whole set end to end — run `chatgpt-codex api-smoke` after any Action change.
3. **All local state and secrets live in `.chatgpt-codex/`** (gitignored, chmod 600 on macOS/Linux): `config.json` holds the bearer token, alongside `permissions.json`, `builder-routes.json`, and `builder.json`. Never print the bearer token or commit this directory; `status` / `channel status` deliberately report `token_configured` but never the token itself.
4. **Security is centralized in `security.py`** and enforced at every entry: bearer auth (server), path sandbox (every file/command op), command deny-list (executor), access TTL (config), and workspace switching restricted to pre-registered names — ChatGPT can never reach an arbitrary path.
5. **Builder automation is a Python→Node bridge.** `chatgpt-codex builder <cmd>` shells out via `npx --yes --package playwright node scripts/chatgpt_builder_playwright.mjs ...` using a dedicated persistent profile. Node/npx are required only for this; the server itself needs neither. Append `--dry-run` to any builder subcommand to print the command instead of running it.

## Conventions

- **Zero runtime dependencies.** `pyproject.toml` declares none, and the server path must keep using only the standard library (`http.server`, `urllib`, `secrets`, ...). Don't pull third-party packages into it.
- **User-facing strings are bilingual** (`English / 中文`) — help text, JSON notes, printed handoffs. Match that when editing them.
- **`tests/test_docs.py` gates documentation** and will fail the suite if broken: README.md must stay English-only while README.zh-CN.md is Chinese; this file and the other doc files must keep the minimal-input keywords (`Playwright`, `ChatGPT`, `workspace`, `Cloudflare`, `chatgpt-codex.<domain>`, `temporary HTTPS tunnel`) and avoid the comparison terms it forbids. Re-run `python3 -m unittest tests.test_docs` after editing any doc.
