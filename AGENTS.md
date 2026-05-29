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

## Ask First / 先问用户

Ask for these inputs before making changes:

执行前先询问这些信息：

1. Workspace path to expose.
2. Operating system: macOS or Windows.
3. Access plan: local-only test, built-in quick tunnel, custom domain, or existing HTTPS route.
4. Local port, default `8766`.
5. Whether their ChatGPT account can create Custom GPTs with Actions.
6. Permission to open Chrome and automate ChatGPT Builder after the user logs in manually.
7. Permission to start local background services.
8. Permission to install helper tools when the chosen access plan requires them.
9. If using a custom domain or existing HTTPS route, the hostname and routing details.

中文：

1. 要暴露的 workspace 路径。
2. 操作系统：macOS 或 Windows。
3. 访问方案：仅本地测试、内置临时隧道、自定义域名，或已有 HTTPS 入口。
4. 本地端口，默认 `8766`。
5. ChatGPT 账号是否能创建带 Actions 的 Custom GPT。
6. 是否允许打开 Chrome，并在用户手动登录后自动配置 ChatGPT Builder。
7. 是否允许启动本地后台服务。
8. 当所选入口方案需要辅助工具时，是否允许自动安装。
9. 如果使用自定义域名或已有 HTTPS 入口，提供 hostname 和路由信息。

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
  --operating-system "$OPERATING_SYSTEM" \
  --access-plan "$ACCESS_PLAN" \
  --public-base-url "$PUBLIC_BASE_URL" \
  --allow-browser-automation \
  --allow-start-services \
  --allow-install-helpers \
  --allow-workspace-write \
  --allow-command-execution
chatgpt-codex init --workspace "$WORKSPACE" --public-base-url "$PUBLIC_BASE_URL"
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
chatgpt-codex init --workspace "$Workspace" --public-base-url "$PublicBaseUrl"
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

If browser automation is approved, open ChatGPT Builder after the user has logged in manually:

如果用户授权浏览器自动化，请在用户手动登录后打开 ChatGPT Builder：

```bash
chatgpt-codex open-chatgpt
```

Use Chrome automation to create or edit the GPT. Never ask for or store ChatGPT passwords, cookies, browser session data, or API keys.

使用 Chrome 自动化创建或编辑 GPT。不要索要或保存 ChatGPT 密码、cookie、浏览器会话数据或 API key。

## Verify / 验证

Verify these before saying setup is complete:

确认完成前必须验证：

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
