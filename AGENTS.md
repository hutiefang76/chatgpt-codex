# AI Agent Playbook / AI Agent 执行手册

Use the bundled skill first: [skills/chatgpt-codex/SKILL.md](./skills/chatgpt-codex/SKILL.md).

优先使用仓库内置 skill：[skills/chatgpt-codex/SKILL.md](./skills/chatgpt-codex/SKILL.md)。

You are helping a user turn ChatGPT web into a local coding assistant through this repository.

你正在帮助用户通过本仓库，把 ChatGPT 网页版配置成本地编程助手。

## Outcome / 目标结果

By the end, the user should have:

最终用户应得到：

- a local server running for one chosen workspace;
- 一个指向指定 workspace 的本地服务；
- a public HTTPS URL that reaches that server;
- 一个能访问该服务的公网 HTTPS 地址；
- a generated bearer token kept private;
- 一个已生成并妥善保管的 bearer token；
- ChatGPT Builder fields ready to paste;
- 可直接粘贴到 ChatGPT Builder 的配置字段；
- a verified read-only Action call.
- 一个验证通过的只读 Action 调用。
- direct interface smoke results from temporary workspaces.
- 临时工作区的直接接口冒烟测试结果。

## Ask First / 先问用户

Ask only for the minimal human inputs before making changes:

执行前只询问真人必须提供的最小信息：

1. Human login to ChatGPT in the Playwright persistent profile: required. The user logs in manually; never ask for credentials.
2. Workspace path to expose: required.
3. Browser human login to Cloudflare: optional, only for stable Cloudflare-hosted routing.
4. Cloudflare-managed domain: optional. If present, the fixed hostname is `chatgpt-codex.<domain>`.
5. Local authorization: required. Confirm permission to detect the OS, choose the route, install needed helpers, start local services, open the Playwright browser, configure Builder after human login, write the workspace, and execute commands inside the workspace.

中文：

1. 在 Playwright 持久化 profile 中真人登录 ChatGPT：必须。用户手动登录；不要索要凭据。
2. 要暴露的 workspace 路径：必须。
3. 浏览器真人登录 Cloudflare：可选，仅用于稳定的 Cloudflare 托管入口。
4. Cloudflare 管理的域名：可选。如果提供，固定 hostname 为 `chatgpt-codex.<domain>`。
5. 本地授权：必须。确认允许自动识别系统、选择入口方案、安装必要辅助工具、启动本地服务、打开 Playwright 浏览器、在真人登录后配置 Builder、写入 workspace，并在 workspace 内执行命令。

Do not ask the user to choose the OS, access plan, local port, or subdomain unless they explicitly want to override defaults. Detect the OS, use port `8766`, pick a temporary HTTPS tunnel when no Cloudflare login/domain are available, and pick `https://chatgpt-codex.<domain>` when they are available.

不要要求用户选择操作系统、访问方案、本地端口或子域名，除非用户明确要覆盖默认值。自动识别系统，默认端口 `8766`；没有 Cloudflare 登录/域名时使用临时 HTTPS 隧道，两者具备时使用 `https://chatgpt-codex.<domain>`。

Never ask for ChatGPT passwords, browser cookies, OpenAI API keys, or unrelated secrets.

不要索要 ChatGPT 密码、浏览器 cookie、OpenAI API key 或无关密钥。

## Execute / 执行

Use `permissions.example.json` in the repository root as the manual template. If the user wants a file to edit, copy it with `./scripts/prepare-permissions.sh` on macOS or `.\scripts\prepare-permissions.ps1` on Windows PowerShell. If the user already gave the required answers, prefer `chatgpt-codex authorize` to create `.chatgpt-codex/permissions.json` directly.

使用仓库根目录的 `permissions.example.json` 作为手工模板。如果用户想手动编辑文件，macOS 用 `./scripts/prepare-permissions.sh` 复制，Windows PowerShell 用 `.\scripts\prepare-permissions.ps1` 复制。如果用户已经提供必要答案，优先用 `chatgpt-codex authorize` 直接创建 `.chatgpt-codex/permissions.json`。

macOS:

macOS：

```bash
./scripts/install.sh
. .venv/bin/activate
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
chatgpt-codex channel register --workspace "$WORKSPACE" --public-base-url "$PUBLIC_BASE_URL"
chatgpt-codex doctor
```

Windows PowerShell:

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
. .\.venv\Scripts\Activate.ps1
$Workspace = "C:\absolute\path\to\project"
$PublicBaseUrl = "https://actions.example.com"
chatgpt-codex route-options
chatgpt-codex authorize `
  --workspace "$Workspace" `
  --operating-system windows `
  --access-plan built-in-quick-tunnel `
  --public-base-url "$PublicBaseUrl" `
  --allow-browser-automation `
  --allow-start-services `
  --allow-install-helpers `
  --allow-workspace-write `
  --allow-command-execution
chatgpt-codex channel register --workspace "$Workspace" --public-base-url "$PublicBaseUrl"
chatgpt-codex doctor
```

Start the local server:

启动本地服务：

```bash
chatgpt-codex serve
```

If the user chose the built-in quick tunnel, start:

如果用户选择内置临时隧道，启动：

```bash
chatgpt-codex tunnel
```

If browser automation is approved, use Playwright after the user has logged in manually:

如果用户授权浏览器自动化，请在用户手动登录后打开 ChatGPT Builder：

```bash
chatgpt-codex builder open-login
chatgpt-codex builder doctor
chatgpt-codex builder configure --mode ui
chatgpt-codex builder smoke
```

Use `chatgpt-codex builder sniff` to discover internal Builder API routes only inside the same Playwright browser context. Use Computer Use only as a fallback. Never ask for or store ChatGPT passwords, cookies, browser session data, or API keys.

使用 `chatgpt-codex builder sniff` 只在同一个 Playwright 浏览器会话中发现内部 Builder API 路由。Computer Use 仅作为兜底。不要索要或保存 ChatGPT 密码、cookie、浏览器会话数据或 API key。

## Verify / 验证

Verify these before saying setup is complete:

确认完成前必须验证：

```bash
chatgpt-codex api-smoke
chatgpt-codex channel status
curl --noproxy '*' "$PUBLIC_BASE_URL/health"
curl --noproxy '*' "$PUBLIC_BASE_URL/openapi.json"
```

Windows PowerShell:

Windows PowerShell：

```powershell
curl.exe --noproxy "*" "$PublicBaseUrl/health"
curl.exe --noproxy "*" "$PublicBaseUrl/openapi.json"
```

Then test one authenticated read-only action with the configured token.

然后用配置里的 token 测试一个带鉴权的只读 Action。

## Final Handoff / 最终交付

Run:

运行：

```bash
chatgpt-codex gpt-instructions
chatgpt-codex token
```

Tell the user to paste the token only into the ChatGPT Builder Action authentication field.

告诉用户只把 token 粘贴到 ChatGPT Builder 的 Action 鉴权字段。
