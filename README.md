# ChatGPT Codex

[Chinese](README.zh-CN.md) | [English](README.md)

ChatGPT Codex turns ChatGPT web into a ChatGPT local coding bridge through Custom GPT Actions. The production path is one command: the user logs in to ChatGPT in the opened browser, then waits while the local bridge, public route, Builder setup, and smoke test run.

The local server runs with only the Python standard library. ChatGPT web cannot reach `localhost` directly, so real ChatGPT Actions use needs a public HTTPS route. The built-in `tunnel` command uses `cloudflared`; you can also provide your own HTTPS route.

## What It Does

- Exposes a bearer-protected HTTP API for one registered local workspace.
- Lets a private GPT list, read, search, write, patch, and run commands in that workspace.
- Generates an OpenAPI document that ChatGPT Actions can import.
- Keeps file paths sandboxed under registered workspace roots.
- Supports workspace switching by registered workspace name, never arbitrary paths.
- Blocks common destructive shell commands by default.
- Gives Codex or Claude an AI-native command catalog for setup, inspection, and recovery.

## Requirements

- Supported OS: macOS and Windows.
- Python 3.9 or newer.
- Node.js/npm with `npx` for Playwright Builder automation. The local server itself does not require Node.
- A ChatGPT account or plan that can create Custom GPTs with Actions. Do not assume Free tier can create or edit GPTs; run `chatgpt-codex chatgpt-preflight` and check the Builder page after login.
- Local OS permission to read and write the workspace you configure.
- Optional: `cloudflared`, only for the built-in `chatgpt-codex tunnel` command or the default quick-tunnel route used by `setup`.
- Optional: a Cloudflare-managed domain if you want a stable hostname such as `chatgpt-codex.example.com`.

## Minimal Human Inputs

The intended user experience is deliberately small:

1. Human login to ChatGPT in the Playwright persistent profile: required. The agent must not ask for ChatGPT passwords, cookies, sessions, or API keys.
2. Workspace path: required, for example `/Users/me/project/demo`.
3. Browser human login to Cloudflare: optional, only for a stable Cloudflare-managed custom hostname.
4. Cloudflare-managed domain: optional. If provided, the fixed hostname is `chatgpt-codex.<domain>`.
5. Local authorization: required. Allow the agent to detect the OS, choose the route, install needed helpers, start services, open the Playwright browser, configure Builder after human login, write the workspace, and execute commands inside the workspace.

Defaults: if no Cloudflare login and domain are provided, use a temporary HTTPS tunnel for ChatGPT web. If both are available, use `chatgpt-codex.<domain>`. Local-only mode is for tests or explicit user requests.

## Local Authorization File

For AI-native setup, save the user's local permission choices in `.chatgpt-codex/permissions.json`. The root `permissions.example.json` file is a safe template. A user can copy it with `./scripts/prepare-permissions.sh` on macOS or `.\scripts\prepare-permissions.ps1` on Windows PowerShell, or an agent can write validated values directly:

```bash
chatgpt-codex authorize \
  --workspace /absolute/path/to/your/project \
  --operating-system auto \
  --access-plan built-in-quick-tunnel \
  --public-base-url https://temporary-or-stable-url.example.com \
  --allow-browser-automation \
  --allow-start-services \
  --allow-install-helpers \
  --allow-workspace-write \
  --allow-command-execution
```

## Quick Start

macOS:

```bash
git clone git@github.com:hutiefang76/chatgpt-codex.git
cd chatgpt-codex
./scripts/install.sh
. .venv/bin/activate
chatgpt-codex setup --workspace /absolute/path/to/your/project
```

Windows PowerShell:

```powershell
git clone git@github.com:hutiefang76/chatgpt-codex.git
cd chatgpt-codex
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
. .\.venv\Scripts\Activate.ps1
chatgpt-codex setup --workspace "C:\absolute\path\to\your\project"
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass -Force` in that terminal and retry activation.

The `setup` command prepares the local bridge, starts or uses a public HTTPS route, verifies the Action API, opens ChatGPT Builder, waits for the human ChatGPT login, captures the saved GPT URL, and runs `builder smoke` when possible. Temporary quick-tunnel URLs are retried automatically when the first URL is not reachable. The bridge then stays running until `Ctrl-C`.

For a dry run that prints the plan without touching browsers or starting tunnels:

```bash
chatgpt-codex setup --workspace /absolute/path/to/your/project --dry-run
```

## AI-Native Setup

Give this repository to Codex or Claude and ask it to use the bundled skill:

- [skills/chatgpt-codex/SKILL.md](skills/chatgpt-codex/SKILL.md)

Useful agent entry files:

- [AGENTS.md](AGENTS.md)
- [CLAUDE.md](CLAUDE.md)
- [docs/AI_NATIVE.md](docs/AI_NATIVE.md)

The same handoff can be printed from the CLI:

```bash
chatgpt-codex skill
chatgpt-codex ai-native
chatgpt-codex agent-brief
```

Agents should prefer machine-readable commands:

```bash
chatgpt-codex --lang en status
chatgpt-codex ai-commands
chatgpt-codex chatgpt-preflight
chatgpt-codex setup --workspace /absolute/path/to/project --dry-run
chatgpt-codex setup --workspace /absolute/path/to/project --builder-fallback auto --builder-challenge-grace-seconds 45
chatgpt-codex setup-smoke
chatgpt-codex api-smoke
chatgpt-codex channel status
chatgpt-codex access status
chatgpt-codex set-public-url https://your-current-public-url
chatgpt-codex channel renew --public-base-url https://your-current-public-url
chatgpt-codex verify
```

`status` reports config paths, active workspace, registered workspaces, local/public URLs, helper availability, language, and whether a token is configured. It never prints the bearer token itself.

`ai-commands` prints the local command catalog for language selection, setup, inspection, workspace switching, Builder fields, runtime, and access lifecycle.

`chatgpt-preflight` prints the ChatGPT-side prerequisites, the login URL, the Builder automation boundary, and Builder fields derived from the current local config without printing the bearer token.

`api-smoke` starts a temporary local server and tests the Action interfaces directly: auth, health, schema, workspace status, workspace listing, file list/read/write/search/patch, command execution, workspace switching, and safety blocks. It does not touch your real workspace.

`setup-smoke` is the deterministic local acceptance test for the setup path. It uses temporary workspaces to verify the local server, `api-smoke`, bootstrap workspace rebinding, Builder dry-run commands, and the Node Builder bridge self-test without requiring ChatGPT login.

## Builder Automation

The default Builder path is Playwright with a dedicated persistent profile. It does not reuse the user's daily Chrome profile, and the Chrome plugin is not a default dependency. The user logs in once inside the Playwright browser, then the saved GPT belongs to the user's ChatGPT account and is visible from normal browsers too.

Useful commands:

```bash
chatgpt-codex builder profile-path
chatgpt-codex builder payload --json
chatgpt-codex builder open-login
chatgpt-codex builder doctor
chatgpt-codex builder setup
chatgpt-codex builder configure --mode ui
chatgpt-codex builder configure --mode hybrid
chatgpt-codex builder sniff
chatgpt-codex builder smoke
```

`builder payload --json` produces the GPT name, description, instructions, schema URL, privacy URL, visibility, and automation metadata without printing the bearer token.

`builder setup` opens ChatGPT Builder in the persistent Playwright profile, waits while the user completes login or a browser challenge, fills stable Builder fields, attempts Action/auth/save automation, waits for a saved `https://chatgpt.com/g/...` URL, and stores it in `.chatgpt-codex/builder.json`.

If `builder setup` stays on a ChatGPT or Cloudflare challenge page past the challenge grace window, it returns `stage: "builder_fallback_required"` with a machine-readable Chrome/Computer Use handoff. In top-level `setup`, the local bridge and public route stay running so an AI agent can continue in the user's normal browser without losing the saved URL or token. Disable this with `--fallback none` only when you want the command to wait until its normal timeout.

`builder smoke` opens the saved GPT, submits a `workspace_status` smoke prompt, and exits non-zero unless a workspace-status result appears on the page. `builder configure --mode hybrid` also captures redacted Builder network traffic. `builder sniff` is the explicit internal API discovery flow: perform one Builder save/configure action in the opened browser, press `Ctrl-C`, and the redacted route map is saved to `.chatgpt-codex/builder-routes.json`.

Internal API replay must stay inside the same Playwright browser context. Do not export cookies, sessions, or ChatGPT credentials. Treat internal routes as unstable acceleration data; if they do not validate, fall back to UI automation.

## Channel Lifecycle

First registration binds this local tool install to the exact workspace path you pass. The high-level command does this automatically:

```bash
chatgpt-codex setup --workspace /absolute/path/to/your/project
```

By default, setup tries up to 6 temporary public tunnel URLs when no Cloudflare account/domain is provided. This avoids failing a fresh install just because one generated quick-tunnel route is slow or unreachable.

Low-level registration is still available when you already know the HTTPS URL:

```bash
chatgpt-codex channel register \
  --workspace /absolute/path/to/your/project \
  --public-base-url https://chatgpt-codex.example.com
```

Local secrets are stored in `.chatgpt-codex/config.json` under this repository root. This file contains the public URL, registered workspace paths, active workspace name, and bearer token. `.chatgpt-codex/` is ignored by Git, and config files are written as private files on macOS/Linux. Do not commit or publish it.

Lifecycle commands:

```bash
chatgpt-codex channel status
chatgpt-codex channel revoke
chatgpt-codex channel renew
chatgpt-codex channel renew --public-base-url https://new-public-url.example.com
chatgpt-codex channel renew --ttl-minutes 120
```

`channel status` never prints the token. `channel revoke` disables the channel immediately and rotates the token silently. `channel renew` reactivates access and prints the current token once for ChatGPT Builder.

Low-level access commands are also available:

```bash
chatgpt-codex rotate-token
chatgpt-codex access revoke
chatgpt-codex access status
```

Default personal-use access does not expire while the server is running. If you intentionally want a short-lived session, start with `chatgpt-codex serve --ttl-minutes 120` or renew with `--ttl-minutes`.

## Workspace Switching

Add another authorized project:

```bash
chatgpt-codex workspace add --name api --path /absolute/path/to/api
chatgpt-codex workspace add --name web --path /absolute/path/to/web --activate
chatgpt-codex workspace list
chatgpt-codex workspace switch api
```

Inside GPT chat, ask the GPT to call `workspace_status`, `list_workspaces`, and `switch_workspace`. The current local directory should be shown before file or command work.

## Closed-loop product flow

1. Collect minimal human inputs and local authorization.
2. Install the launcher on macOS or Windows PowerShell.
3. Run `chatgpt-codex setup --workspace <path>`.
4. Complete ChatGPT login in the opened Playwright browser.
5. Let setup verify the bridge, configure Builder, capture the saved GPT URL, and run `builder smoke`.
6. If Playwright returns `builder_fallback_required`, let the agent use Chrome/Computer Use with the printed handoff while setup keeps the bridge alive.
7. In GPT chat, use `workspace_status`, `list_workspaces`, and `switch_workspace` before file or command work.

## Lower-Level Commands

`chatgpt-codex bootstrap` remains available for deterministic local-side setup only. It registers a channel, starts the server, starts the quick tunnel and auto-captures its public URL, then verifies and prints Builder fields. It does not perform the top-level Builder setup flow.

```bash
chatgpt-codex bootstrap --workspace /absolute/path/to/your/project
chatgpt-codex bootstrap --workspace /absolute/path/to/your/project --public-base-url https://actions.example.com
chatgpt-codex bootstrap --workspace /absolute/path/to/your/project --no-tunnel
```

## Development Verification

```bash
python3 -m unittest discover -s tests
py -3 -m unittest discover -s tests
node --check scripts/chatgpt_builder_playwright.mjs
chatgpt-codex setup-smoke
```
