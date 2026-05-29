# AI-Native Setup / AI-Native 自动配置

This repository can be operated directly by Codex or Claude.

这个仓库可以直接交给 Codex 或 Claude 操作。

The primary agent entry is the bundled skill:

主要 agent 入口是仓库内置 skill：

- `skills/chatgpt-codex/SKILL.md`

## User Prompt / 用户可直接复制的提示词

```text
Please use the chatgpt-codex skill in this repository to set up my ChatGPT local coding bridge.

Ask me only for the minimal human inputs:
- confirm I am logged into ChatGPT in Chrome
- workspace path
- optional: confirm I am logged into Cloudflare in Chrome
- optional: Cloudflare-managed domain
- local authorization for you to detect the OS, choose the route, install needed helpers, start services, open Chrome, configure Builder after human login, write the workspace, and execute commands inside the workspace

Use a temporary HTTPS tunnel when I do not provide Cloudflare login plus a domain. Use the fixed hostname chatgpt-codex.<domain> when both are available.

Then install, configure, start, verify, and give me the exact ChatGPT Builder fields. Do not ask me to choose the OS, access plan, port, or subdomain unless I explicitly override defaults.

Do not ask for my ChatGPT password, browser cookies, OpenAI API key, or unrelated secrets.
```

```text
请使用本仓库里的 chatgpt-codex skill，把这个仓库配置成我的 ChatGPT 本地编程桥。

只问我真人必须提供的最小信息：
- 确认我已在 Chrome 登录 ChatGPT
- workspace 路径
- 可选：确认我已在 Chrome 登录 Cloudflare
- 可选：Cloudflare 管理的域名
- 本地授权：允许你自动识别系统、选择入口方案、安装必要辅助工具、启动服务、打开 Chrome、在真人登录后配置 Builder、写入 workspace，并在 workspace 内执行命令

如果我没有同时提供 Cloudflare 登录和域名，使用临时 HTTPS 隧道。如果两者都具备，使用固定域名 chatgpt-codex.<domain>。

然后完成安装、配置、启动、验证，并给我可直接填写到 ChatGPT Builder 的字段。除非我明确要覆盖默认值，不要问我选择操作系统、访问方案、端口或子域名。

不要索要我的 ChatGPT 密码、浏览器 cookie、OpenAI API key 或无关密钥。
```

## Agent Checklist / Agent 检查清单

- Collect only the minimal human inputs before changing local state.
- 修改本地状态前只收集真人必须提供的最小信息。
- Run `./scripts/install.sh` on macOS or `.\scripts\install.ps1` on Windows PowerShell.
- macOS 运行 `./scripts/install.sh`；Windows PowerShell 运行 `.\scripts\install.ps1`。
- Run `chatgpt-codex init`.
- 运行 `chatgpt-codex init`。
- Run `chatgpt-codex route-options` and `chatgpt-codex authorize` to save choices in `.chatgpt-codex/permissions.json`.
- 运行 `chatgpt-codex route-options` 和 `chatgpt-codex authorize`，把选项保存到 `.chatgpt-codex/permissions.json`。
- If the user wants manual file editing, copy root `permissions.example.json` with `scripts/prepare-permissions.sh` or `scripts/prepare-permissions.ps1`.
- 如果用户想手工编辑文件，用 `scripts/prepare-permissions.sh` 或 `scripts/prepare-permissions.ps1` 复制根目录的 `permissions.example.json`。
- Run `chatgpt-codex doctor`.
- 运行 `chatgpt-codex doctor`。
- Start `chatgpt-codex serve`.
- 启动 `chatgpt-codex serve`。
- Use a temporary HTTPS tunnel when no Cloudflare login/domain are provided; use `chatgpt-codex.<domain>` when both are provided.
- 没有 Cloudflare 登录/域名时使用临时 HTTPS 隧道；两者都提供时使用 `chatgpt-codex.<domain>`。
- Open ChatGPT Builder with `chatgpt-codex open-chatgpt` only after browser automation is approved and the user has logged in manually.
- 只有在用户授权浏览器自动化并手动登录后，才用 `chatgpt-codex open-chatgpt` 打开 ChatGPT Builder。
- Verify `/health`, `/openapi.json`, and one authenticated read-only action.
- 验证 `/health`、`/openapi.json` 和一个带鉴权的只读 Action。
- Print `chatgpt-codex gpt-instructions`.
- 打印 `chatgpt-codex gpt-instructions`。
- Give the user the token privately for the Builder auth field.
- 将 token 私下交给用户，用于 Builder 鉴权字段。
