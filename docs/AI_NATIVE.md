# AI-Native Setup / AI-Native 自动配置

This repository can be operated directly by Codex or Claude.

这个仓库可以直接交给 Codex 或 Claude 操作。

The primary agent entry is the bundled skill:

主要 agent 入口是仓库内置 skill：

- `skills/chatgpt-codex/SKILL.md`

## User Prompt / 用户可直接复制的提示词

```text
Please use the chatgpt-codex skill in this repository to set up my ChatGPT local coding bridge.

Ask me for the required inputs first:
- operating system, macOS or Windows
- workspace path
- access plan: local-only test, built-in quick tunnel, custom domain, or existing HTTPS route
- local port, default 8766
- whether my ChatGPT account can create Custom GPTs with Actions
- permission to open Chrome and automate ChatGPT Builder after I log in manually
- permission to start local background services
- permission to install helper tools when the chosen access plan requires them
- custom domain or HTTPS routing details if needed

Then install, configure, start, verify, and give me the exact ChatGPT Builder fields.

Do not ask for my ChatGPT password, browser cookies, OpenAI API key, or unrelated secrets.
```

```text
请使用本仓库里的 chatgpt-codex skill，把这个仓库配置成我的 ChatGPT 本地编程桥。

先问我必要信息：
- 操作系统：macOS 或 Windows
- workspace 路径
- 访问方案：仅本地测试、内置临时隧道、自定义域名，或已有 HTTPS 入口
- 本地端口，默认 8766
- 我的 ChatGPT 账号是否能创建带 Actions 的 Custom GPT
- 是否允许打开 Chrome，并在我手动登录后自动配置 ChatGPT Builder
- 是否允许启动本地后台服务
- 当所选入口方案需要辅助工具时，是否允许自动安装
- 如需要，询问自定义域名或 HTTPS 路由信息

然后完成安装、配置、启动、验证，并给我可直接填写到 ChatGPT Builder 的字段。

不要索要我的 ChatGPT 密码、浏览器 cookie、OpenAI API key 或无关密钥。
```

## Agent Checklist / Agent 检查清单

- Collect required inputs before changing local state.
- 修改本地状态前先收集必要信息。
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
- Start the built-in tunnel only if the user chose that route.
- 仅在用户选择内置隧道方案时启动 tunnel。
- Open ChatGPT Builder with `chatgpt-codex open-chatgpt` only after browser automation is approved and the user has logged in manually.
- 只有在用户授权浏览器自动化并手动登录后，才用 `chatgpt-codex open-chatgpt` 打开 ChatGPT Builder。
- Verify `/health`, `/openapi.json`, and one authenticated read-only action.
- 验证 `/health`、`/openapi.json` 和一个带鉴权的只读 Action。
- Print `chatgpt-codex gpt-instructions`.
- 打印 `chatgpt-codex gpt-instructions`。
- Give the user the token privately for the Builder auth field.
- 将 token 私下交给用户，用于 Builder 鉴权字段。
