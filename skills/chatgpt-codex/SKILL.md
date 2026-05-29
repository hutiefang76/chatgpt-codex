---
name: chatgpt-codex
description: Set up and verify this repository as a ChatGPT local coding bridge. Use when the user asks Codex, Claude, or another AI agent to install ChatGPT Codex, ask for required setup inputs, configure a workspace, start the local server, set up or use a public HTTPS route, verify ChatGPT Actions endpoints, or produce the final ChatGPT Builder fields.
---

# ChatGPT Codex

Use this skill to turn this repository into a working local coding bridge for ChatGPT web.

使用本 skill，将本仓库配置成 ChatGPT 网页版可调用的本地编程桥。

## Workflow / 流程

1. Ask the user for required inputs before changing local state.
2. Install the local launcher.
3. Save setup permissions in `.chatgpt-codex/permissions.json`.
4. Create config for the target workspace.
5. Start the local server and set up or use a public HTTPS route when ChatGPT web access is needed.
6. Open ChatGPT Builder in Chrome only after browser automation is approved and the user has logged in manually.
7. Verify health, schema, and one authenticated read-only action.
8. Print or apply the final ChatGPT Builder fields.

中文：

1. 修改本地状态前，先向用户询问必要信息。
2. 安装本地启动器。
3. 将配置授权保存到 `.chatgpt-codex/permissions.json`。
4. 为目标 workspace 创建配置。
5. 启动本地服务；当需要 ChatGPT 网页端访问时，配置或使用公网 HTTPS 入口。
6. 只有在用户授权浏览器自动化并手动登录后，才在 Chrome 中打开 ChatGPT Builder。
7. 验证健康检查、schema，以及一个带鉴权的只读 Action。
8. 打印或填写最终可用于 ChatGPT Builder 的字段。

For a copyable user prompt and detailed checklist, read `references/agent-handoff.md`.

如需可复制提示词和详细检查清单，读取 `references/agent-handoff.md`。

## Required Inputs / 必要信息

Ask for:

询问：

- workspace path / workspace 路径
- operating system: macOS or Windows / 操作系统：macOS 或 Windows
- access plan: local-only test, built-in quick tunnel, custom domain, or existing HTTPS route / 访问方案：仅本地测试、内置临时隧道、自定义域名，或已有 HTTPS 入口
- local port, default `8766` / 本地端口，默认 `8766`
- confirmation that the ChatGPT account can create Custom GPTs with Actions / 确认 ChatGPT 账号能创建带 Actions 的 Custom GPT
- permission to open Chrome and automate ChatGPT Builder after manual login / 是否允许打开 Chrome，并在用户手动登录后自动配置 ChatGPT Builder
- permission to start local background services / 是否允许启动本地后台服务
- permission to install helper tools when the chosen access plan requires them / 当所选入口方案需要辅助工具时，是否允许自动安装
- custom hostname or HTTPS routing details if needed / 如需要，询问自定义域名或 HTTPS 路由信息

Never ask for ChatGPT passwords, browser cookies, OpenAI API keys, or unrelated secrets.

不要索要 ChatGPT 密码、浏览器 cookie、OpenAI API key 或无关密钥。

## Commands / 命令

Permissions template:

授权模板：

- `permissions.example.json` lives in the repository root and is safe to commit.
- `permissions.example.json` 位于仓库根目录，可以安全提交。
- The real local authorization file is `.chatgpt-codex/permissions.json` and is ignored by Git.
- 真实本机授权文件是 `.chatgpt-codex/permissions.json`，会被 Git 忽略。
- For manual editing, copy the template with `./scripts/prepare-permissions.sh` on macOS or `.\scripts\prepare-permissions.ps1` on Windows PowerShell.
- 如需手工编辑，macOS 用 `./scripts/prepare-permissions.sh` 复制模板，Windows PowerShell 用 `.\scripts\prepare-permissions.ps1`。
- If the user already provided answers, prefer `chatgpt-codex authorize` because it writes validated values.
- 如果用户已提供答案，优先使用 `chatgpt-codex authorize`，因为它会写入校验后的值。

Install on macOS:

macOS 安装：

```bash
./scripts/install.sh
. .venv/bin/activate
```

Install on Windows PowerShell:

Windows PowerShell 安装：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
. .\.venv\Scripts\Activate.ps1
```

Configure:

配置：

```bash
chatgpt-codex route-options
chatgpt-codex authorize \
  --workspace "$WORKSPACE" \
  --operating-system "$OPERATING_SYSTEM" \
  --access-plan "$ACCESS_PLAN" \
  --public-base-url "$PUBLIC_BASE_URL" \
  --allow-browser-automation \
  --allow-start-services \
  --allow-install-helpers \
  --allow-workspace-write \
  --allow-command-execution
```

```bash
chatgpt-codex init --workspace "$WORKSPACE" --public-base-url "$PUBLIC_BASE_URL"
chatgpt-codex doctor
```

Windows PowerShell:

Windows PowerShell：

```powershell
$Workspace = "C:\absolute\path\to\project"
$PublicBaseUrl = "https://actions.example.com"
chatgpt-codex init --workspace "$Workspace" --public-base-url "$PublicBaseUrl"
chatgpt-codex doctor
```

Access plan rules:

入口方案规则：

- `local-only`: no public HTTPS, no `cloudflared`, no domain; do not configure ChatGPT Actions.
- `local-only`：不需要公网 HTTPS、不需要 `cloudflared`、不需要域名；不要配置 ChatGPT Actions。
- `built-in-quick-tunnel`: public HTTPS required, `cloudflared` required, domain not required.
- `built-in-quick-tunnel`：需要公网 HTTPS，需要 `cloudflared`，不需要域名。
- `custom-domain`: public HTTPS required, domain required, `cloudflared` only if the user's routing choice uses it.
- `custom-domain`：需要公网 HTTPS，需要域名；只有用户选择的路由方式需要时才需要 `cloudflared`。
- `existing-https-route`: public HTTPS required, no `cloudflared` or new domain required.
- `existing-https-route`：需要公网 HTTPS；不需要 `cloudflared` 或新域名。

Start the local server:

启动本地服务：

```bash
chatgpt-codex serve
```

If the user chooses the built-in quick tunnel:

如果用户选择内置临时隧道：

```bash
chatgpt-codex tunnel
```

If the user approved browser automation and is logged into ChatGPT in Chrome:

如果用户已授权浏览器自动化，并且已在 Chrome 登录 ChatGPT：

```bash
chatgpt-codex open-chatgpt
```

Use Chrome automation to create or edit the GPT, paste `chatgpt-codex gpt-instructions`, import the schema URL, set Bearer auth with `chatgpt-codex token`, and save as private. Do not request or store ChatGPT credentials, cookies, or API keys.

使用 Chrome 自动化创建或编辑 GPT，粘贴 `chatgpt-codex gpt-instructions`，导入 schema URL，用 `chatgpt-codex token` 设置 Bearer 鉴权，并保存为私有。不要索要或保存 ChatGPT 凭据、cookie 或 API key。

## Verification / 验证

Before saying setup is complete, verify. For local-only testing, use the local server URL. For ChatGPT web use, use the public HTTPS URL.

确认完成前，必须验证。仅本地测试时使用本地服务地址；ChatGPT 网页端真实使用时使用公网 HTTPS 地址。

```bash
curl --noproxy '*' "$PUBLIC_BASE_URL/health"
curl --noproxy '*' "$PUBLIC_BASE_URL/openapi.json"
```

Windows PowerShell:

Windows PowerShell：

```powershell
curl.exe --noproxy "*" "$PublicBaseUrl/health"
curl.exe --noproxy "*" "$PublicBaseUrl/openapi.json"
```

Then test one authenticated read-only action:

然后测试一个带鉴权的只读 Action：

```bash
TOKEN="$(chatgpt-codex token)"
curl --noproxy '*' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path":".","recursive":false,"max_results":20}' \
  "$PUBLIC_BASE_URL/list_files"
```

Windows PowerShell:

Windows PowerShell：

```powershell
$Token = chatgpt-codex token
curl.exe --noproxy "*" `
  -H "Authorization: Bearer $Token" `
  -H "Content-Type: application/json" `
  -d '{"path":".","recursive":false,"max_results":20}' `
  "$PublicBaseUrl/list_files"
```

## Final Handoff / 最终交付

Print:

打印：

```bash
chatgpt-codex gpt-instructions
chatgpt-codex token
```

Tell the user to paste the token only into the ChatGPT Builder Action authentication field.

告诉用户只把 token 粘贴到 ChatGPT Builder 的 Action 鉴权字段。
