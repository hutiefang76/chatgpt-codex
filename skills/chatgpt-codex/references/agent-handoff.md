# Agent Handoff / Agent 交接提示

## Copyable Prompt / 可复制提示词

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

## Completion Checklist / 完成检查

- Required inputs collected.
- 已收集必要信息。
- Local launcher installed with the macOS or Windows installer.
- 已使用 macOS 或 Windows 安装脚本安装本地启动器。
- Setup choices saved in `.chatgpt-codex/permissions.json`.
- 已在 `.chatgpt-codex/permissions.json` 保存配置选项。
- If manual editing is preferred, root `permissions.example.json` copied with the OS helper script.
- 如果偏好手工编辑，已用对应操作系统辅助脚本复制根目录的 `permissions.example.json`。
- Config created under `.chatgpt-codex/config.json`.
- 已在 `.chatgpt-codex/config.json` 创建配置。
- Local server started.
- 已启动本地服务。
- Public HTTPS route available when ChatGPT web access is required.
- 需要 ChatGPT 网页端访问时，公网 HTTPS 路由可用。
- `/health` works.
- `/health` 可访问。
- `/openapi.json` works.
- `/openapi.json` 可访问。
- Authenticated read-only Action works.
- 带鉴权只读 Action 可用。
- Builder fields printed.
- 已打印 Builder 字段。
- If browser automation is approved, ChatGPT Builder configured after the user logs in manually.
- 如果用户授权浏览器自动化，已在用户手动登录后配置 ChatGPT Builder。
