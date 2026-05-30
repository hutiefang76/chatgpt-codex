---
name: chatgpt-codex
description: Set up and verify this repository as a ChatGPT local coding bridge. Use when the user asks Codex, Claude, or another AI agent to install ChatGPT Codex, collect minimal human inputs, configure a workspace, start the local server, set up or use a public HTTPS route, verify ChatGPT Actions endpoints, or produce the final ChatGPT Builder fields.
---

# ChatGPT Codex

Use this skill to turn this repository into a working local coding bridge for ChatGPT web.

使用本 skill，将本仓库配置成 ChatGPT 网页版可调用的本地编程桥。

## Workflow / 流程

1. Ask only for the minimal human inputs before changing local state.
2. Install the local launcher.
3. Save setup permissions in `.chatgpt-codex/permissions.json`.
4. Create config for the target workspace.
5. Start the local server and set up or use a public HTTPS route when ChatGPT web access is needed.
6. Open ChatGPT Builder in Chrome only after browser automation is approved and the user has logged in manually.
7. Verify health, schema, and one authenticated read-only action.
8. Print or apply the final ChatGPT Builder fields.

中文：

1. 修改本地状态前，只向用户询问真人必须提供的最小信息。
2. 安装本地启动器。
3. 将配置授权保存到 `.chatgpt-codex/permissions.json`。
4. 为目标 workspace 创建配置。
5. 启动本地服务；当需要 ChatGPT 网页端访问时，配置或使用公网 HTTPS 入口。
6. 只有在用户授权浏览器自动化并手动登录后，才在 Chrome 中打开 ChatGPT Builder。
7. 验证健康检查、schema，以及一个带鉴权的只读 Action。
8. 打印或填写最终可用于 ChatGPT Builder 的字段。

For a copyable user prompt and detailed checklist, read `references/agent-handoff.md`.

如需可复制提示词和详细检查清单，读取 `references/agent-handoff.md`。

## Closed Loop / 功能闭环

The setup is complete only when all of these are true:

只有全部满足时才算完成：

- minimal human inputs and local authorization are recorded;
- 已记录真人最小输入和本地授权；
- `.chatgpt-codex/config.json` exists with `workspaces` and `active_workspace`;
- `.chatgpt-codex/config.json` 已存在，并包含 `workspaces` 和 `active_workspace`；
- `chatgpt-codex status` is readable by the agent;
- agent 可以读取 `chatgpt-codex status`；
- local server is running;
- 本地服务已运行；
- final public URL is saved with `chatgpt-codex set-public-url`;
- 最终公网 URL 已用 `chatgpt-codex set-public-url` 保存；
- `chatgpt-codex verify` passes;
- `chatgpt-codex verify` 通过；
- ChatGPT Builder has the current schema URL and bearer token;
- ChatGPT Builder 已配置当前 schema URL 和 bearer token；
- GPT chat can show and switch the active workspace using Actions.
- GPT 对话可以通过 Actions 显示并切换当前工作区。

## Required Inputs / 必要信息

Ask for:

询问：

- Chrome human login to ChatGPT: required. The user logs in manually; the agent only operates after login.
- Chrome 真人登录 ChatGPT：必须。用户手动登录；agent 只在登录后操作。
- Workspace path: required, for example `/Users/me/project/demo`.
- Workspace 路径：必须，例如 `/Users/me/project/demo`。
- Chrome human login to Cloudflare: optional, only for a stable Cloudflare-managed hostname.
- Chrome 真人登录 Cloudflare：可选，仅在需要稳定的 Cloudflare 托管域名时使用。
- Cloudflare-managed domain: optional. When provided, always use the fixed hostname `chatgpt-codex.<domain>`, for example `chatgpt-codex.hutiefang.net`.
- Cloudflare 管理的域名：可选。提供时固定使用 `chatgpt-codex.<domain>`，例如 `chatgpt-codex.hutiefang.net`。
- Local authorization: required. Confirm the agent may detect the OS, choose the route, install needed helpers, start local services, open Chrome, configure ChatGPT Builder after human login, write the workspace, and execute commands inside the workspace.
- 本地授权：必须。确认 agent 可以自动识别系统、选择入口方案、安装必要辅助工具、启动本地服务、打开 Chrome、在真人登录后配置 ChatGPT Builder、写入 workspace，并在 workspace 内执行命令。

Do not ask the user to choose an operating system, access plan, local port, or subdomain unless they explicitly want to override defaults. Detect the OS, use port `8766`, and choose the route automatically.

不要要求用户选择操作系统、访问方案、本地端口或子域名，除非用户明确要覆盖默认值。自动识别系统，默认使用端口 `8766`，并自动选择入口方案。

Route defaults:

入口默认规则：

- If no Cloudflare login and domain are available, use a temporary HTTPS tunnel for ChatGPT web.
- 如果没有 Cloudflare 登录和域名，使用临时 HTTPS 隧道供 ChatGPT 网页端访问。
- If Cloudflare login and a managed domain are available, configure the stable hostname `chatgpt-codex.<domain>`.
- 如果已登录 Cloudflare 且有托管域名，配置稳定域名 `chatgpt-codex.<domain>`。
- Use local-only only for tests or explicit user requests.
- 仅在测试或用户明确要求时使用仅本地模式。
- The ChatGPT account must support GPT Actions to create or configure the GPT. Save it private unless the user intentionally shares access.
- ChatGPT 账号必须支持 GPT Actions 才能创建或配置 GPT。除非用户明确要共享访问，否则保存为私有。

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

AI-native management:

AI-native 管理：

- Start with `chatgpt-codex status` to read machine-readable local state.
- 先运行 `chatgpt-codex status` 读取机器可读的本地状态。
- Use `chatgpt-codex ai-commands` to discover the local command catalog.
- 用 `chatgpt-codex ai-commands` 获取本地命令目录。
- Use `chatgpt-codex set-public-url <url>` after a tunnel or custom route gives the final public URL.
- 隧道或自定义入口给出最终公网 URL 后，用 `chatgpt-codex set-public-url <url>` 保存。
- Use `chatgpt-codex api-smoke` before browser work to test Action interfaces directly in temporary workspaces.
- 浏览器操作前用 `chatgpt-codex api-smoke` 在临时工作区直接测试 Action 接口。
- Use `chatgpt-codex access grant --ttl-minutes <minutes>` or `chatgpt-codex serve --ttl-minutes <minutes>` so exposed Actions have a clear expiry.
- 用 `chatgpt-codex access grant --ttl-minutes <minutes>` 或 `chatgpt-codex serve --ttl-minutes <minutes>` 给暴露的 Actions 设置明确有效期。
- Use `chatgpt-codex rotate-token` when the ChatGPT Builder auth field must be refreshed, and `chatgpt-codex access revoke` when exposure should stop immediately.
- 需要刷新 ChatGPT Builder 鉴权字段时用 `chatgpt-codex rotate-token`，需要立即停止暴露时用 `chatgpt-codex access revoke`。
- Use `chatgpt-codex verify` for the final health/schema/read-only action check.
- 用 `chatgpt-codex verify` 做最终健康检查、schema 和只读 Action 验证。
- `status` reports whether a token exists but never prints the bearer token itself.
- `status` 只报告 token 是否存在，不打印 bearer token 原文。

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
  --operating-system auto \
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

Optional additional authorized projects:

可选添加更多已授权项目：

```bash
chatgpt-codex workspace add --name "$PROJECT_NAME" --path "$PROJECT_PATH"
chatgpt-codex workspace list
```

Do not let ChatGPT switch to arbitrary paths. It may only use workspace names returned by `list_workspaces`.

不要让 ChatGPT 切换到任意路径。它只能使用 `list_workspaces` 返回的工作区名称。

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

Agent route selection:

Agent 入口选择：

- Set `ACCESS_PLAN=built-in-quick-tunnel` when the user did not provide Cloudflare login plus a managed domain.
- 当用户没有提供 Cloudflare 登录和托管域名时，设置 `ACCESS_PLAN=built-in-quick-tunnel`。
- Set `ACCESS_PLAN=custom-domain` when both are available, and set `PUBLIC_BASE_URL=https://chatgpt-codex.<domain>`.
- 当两者都具备时，设置 `ACCESS_PLAN=custom-domain`，并设置 `PUBLIC_BASE_URL=https://chatgpt-codex.<domain>`。
- Set `ACCESS_PLAN=local-only` only for local tests or explicit user requests.
- 仅在本地测试或用户明确要求时设置 `ACCESS_PLAN=local-only`。

Start the local server:

启动本地服务：

```bash
chatgpt-codex serve --ttl-minutes 120
```

If the user chooses the built-in quick tunnel:

如果用户选择内置临时隧道：

```bash
chatgpt-codex tunnel
```

After the public URL is known:

拿到公网 URL 后：

```bash
chatgpt-codex set-public-url "$PUBLIC_BASE_URL"
chatgpt-codex access status
chatgpt-codex verify
```

If the user approved browser automation and is logged into ChatGPT in Chrome:

如果用户已授权浏览器自动化，并且已在 Chrome 登录 ChatGPT：

```bash
chatgpt-codex open-chatgpt
```

Use Chrome automation to create or edit the GPT, paste `chatgpt-codex gpt-instructions`, import the schema URL, set Bearer auth with `chatgpt-codex token`, and save as private. Do not request or store ChatGPT credentials, cookies, or API keys.

使用 Chrome 自动化创建或编辑 GPT，粘贴 `chatgpt-codex gpt-instructions`，导入 schema URL，用 `chatgpt-codex token` 设置 Bearer 鉴权，并保存为私有。不要索要或保存 ChatGPT 凭据、cookie 或 API key。

In the GPT conversation, project switching flow is:

GPT 对话中的项目切换流程：

1. Call `workspace_status` before file, code, or command work and show the current local directory.
2. Call `list_workspaces` when the user asks what projects are available.
3. Call `switch_workspace` only with an authorized workspace name.
4. After switching, state the active workspace name and local path.

中文：

1. 文件、代码或命令操作前调用 `workspace_status`，并显示当前本地目录。
2. 用户询问可用项目时调用 `list_workspaces`。
3. 只用已授权工作区名称调用 `switch_workspace`。
4. 切换后说明当前工作区名称和本地路径。

## Verification / 验证

Before saying setup is complete, verify. For local-only testing, use the local server URL. For ChatGPT web use, use the public HTTPS URL.

确认完成前，必须验证。仅本地测试时使用本地服务地址；ChatGPT 网页端真实使用时使用公网 HTTPS 地址。

Preferred AI-native verification:

优先使用 AI-native 验证：

```bash
chatgpt-codex api-smoke
chatgpt-codex access status
chatgpt-codex verify
```

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
