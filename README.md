# ChatGPT Codex / ChatGPT 本地编程桥

Use ChatGPT web as a local coding assistant through Custom GPT Actions.

通过 Custom GPT Actions，把 ChatGPT 网页版变成本地编程助手。

The local server runs with only the Python standard library. ChatGPT web cannot reach `localhost` directly, so a public HTTPS route is required for real ChatGPT Actions use. The built-in `tunnel` command uses `cloudflared`; you can also provide your own HTTPS route.

本地服务只依赖 Python 标准库即可运行。ChatGPT 网页端不能直接访问 `localhost`，所以真实使用 ChatGPT Actions 时需要一个公网 HTTPS 入口。内置 `tunnel` 命令使用 `cloudflared`；你也可以自行提供 HTTPS 入口。

## What It Does / 功能

- Works as an AI-native setup tool: give the repository to Codex or Claude, answer a few setup questions, then wait for it to configure and verify the bridge.
- 作为 AI-native 配置工具使用：把仓库交给 Codex 或 Claude，回答几个配置问题，然后等待它完成配置和验证。
- Exposes a local, bearer-protected HTTP API for one workspace.
- 为一个工作区暴露带 Bearer 鉴权的本地 HTTP API。
- Lets a Custom GPT list, read, search, write, patch, and run commands in that workspace.
- 让自定义 GPT 可以在该工作区内列文件、读文件、搜索、写文件、打 patch、执行命令。
- Generates an OpenAPI document that ChatGPT Actions can import.
- 自动生成 ChatGPT Actions 可导入的 OpenAPI 文档。
- Keeps all paths sandboxed under the configured workspace.
- 所有路径都被限制在配置的 workspace 内。
- Blocks common destructive shell commands by default.
- 默认拦截常见危险命令。

## Requirements / 环境要求

- Supported OS: macOS and Windows.
- 支持的操作系统：macOS 和 Windows。
- Python 3.9 or newer.
- Python 3.9 或更新版本。
- A ChatGPT account/plan that can create Custom GPTs with Actions.
- 一个能创建带 Actions 的 Custom GPT 的 ChatGPT 账号/套餐。
- Local OS permission to read/write the workspace you configure.
- 本地系统授权该工具读写你配置的工作区。
- Optional: `cloudflared`, only for the built-in `chatgpt-codex tunnel` command.
- 可选：`cloudflared`，仅用于内置的 `chatgpt-codex tunnel` 命令。
- Optional: a Cloudflare-managed domain if you want a stable hostname such as `chatgpt-codex.example.com`.
- 可选：如果你想使用 `chatgpt-codex.example.com` 这类稳定域名，需要一个由 Cloudflare 管理的域名。

## Quick Start / 快速开始

### Skills Setup / Skills 自动配置

Give this repository to Codex or Claude and ask it to set up the bridge for you.

把这个仓库交给 Codex 或 Claude，让它帮你完成配置。

The main entry is the bundled skill:

主要入口是仓库内置 skill：

- [skills/chatgpt-codex/SKILL.md](./skills/chatgpt-codex/SKILL.md)

```bash
chatgpt-codex skills
```

`chatgpt-codex skill`, `chatgpt-codex ai-native`, and `chatgpt-codex agent-brief` print the same handoff text.

`chatgpt-codex skill`、`chatgpt-codex ai-native` 和 `chatgpt-codex agent-brief` 会打印同样的交接说明。

Or point the agent to:

或者让 agent 阅读：

- [AGENTS.md](./AGENTS.md)
- [CLAUDE.md](./CLAUDE.md)
- [docs/AI_NATIVE.md](./docs/AI_NATIVE.md)

Minimal human inputs:

真人最小输入：

- Chrome human login to ChatGPT is required. The agent must not ask for ChatGPT passwords, cookies, sessions, or API keys.
- 真人必须先在 Chrome 登录 ChatGPT。Agent 不得索要 ChatGPT 密码、cookie、会话或 API key。
- Workspace path is required, for example `/Users/me/project/demo`.
- 必须提供 workspace 路径，例如 `/Users/me/project/demo`。
- Chrome human login to Cloudflare is optional, only for a stable Cloudflare-managed custom hostname.
- Chrome 登录 Cloudflare 是可选项，仅在需要稳定的 Cloudflare 托管自定义域名时使用。
- A Cloudflare-managed domain is optional. If provided, the fixed hostname is `chatgpt-codex.<domain>`, for example `chatgpt-codex.hutiefang.net`.
- Cloudflare 管理的域名是可选项。如果提供，固定子域名为 `chatgpt-codex.<domain>`，例如 `chatgpt-codex.hutiefang.net`。
- One local authorization is required: allow the agent to detect the OS, choose the route, install needed helpers, start the service, open Chrome, configure Builder after human login, write the workspace, and execute commands inside the workspace.
- 需要一条本地授权：允许 agent 自动识别系统、选择入口方案、安装必要辅助工具、启动服务、打开 Chrome、在真人登录后配置 Builder、写入 workspace，并在 workspace 内执行命令。

Defaults: if no Cloudflare login and domain are provided, the agent uses a temporary HTTPS tunnel for ChatGPT web. If both are available, the agent may configure the stable hostname `chatgpt-codex.<domain>`. Local-only mode is for tests or explicit user requests. The account used to create the GPT must support Actions, and the GPT should be saved private unless the user intentionally shares access.

默认行为：如果没有 Cloudflare 登录和域名，agent 使用临时 HTTPS 隧道供 ChatGPT 网页端访问。如果两者都具备，agent 可以配置稳定域名 `chatgpt-codex.<domain>`。仅本地模式只用于测试或用户明确要求。创建 GPT 的账号必须支持 Actions，除非用户明确要共享访问，否则 GPT 应保存为私有。

Save the user's setup choices and permissions in the project root before automation:

自动操作前，先把用户选项和授权保存到项目根目录：

The root file `permissions.example.json` is a safe template. A user can copy it manually to `.chatgpt-codex/permissions.json`, or an AI agent can generate the real file with `chatgpt-codex authorize`.

根目录的 `permissions.example.json` 是安全模板。用户可以手工复制到 `.chatgpt-codex/permissions.json`，AI agent 也可以用 `chatgpt-codex authorize` 生成真实文件。

macOS helper:

macOS 辅助脚本：

```bash
./scripts/prepare-permissions.sh
```

Windows PowerShell helper:

Windows PowerShell 辅助脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prepare-permissions.ps1
```

The helper scripts only copy the template. Edit the copied file, or run `chatgpt-codex authorize --force` to replace it with validated values.

辅助脚本只复制模板。你可以编辑复制出的文件，也可以运行 `chatgpt-codex authorize --force` 用校验后的值替换它。

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

Windows PowerShell:

Windows PowerShell：

```powershell
chatgpt-codex authorize `
  --workspace "C:\absolute\path\to\your\project" `
  --operating-system auto `
  --access-plan built-in-quick-tunnel `
  --public-base-url https://temporary-or-stable-url.example.com `
  --allow-browser-automation `
  --allow-start-services `
  --allow-install-helpers `
  --allow-workspace-write `
  --allow-command-execution
```

This writes `.chatgpt-codex/permissions.json`. It stores setup choices and local permissions, not ChatGPT passwords, cookies, or API keys.

这会写入 `.chatgpt-codex/permissions.json`。里面只保存配置选项和本机授权，不保存 ChatGPT 密码、cookie 或 API key。

To see whether `cloudflared` or a domain is required for a route:

查看某种入口方案是否需要 `cloudflared` 或域名：

```bash
chatgpt-codex route-options
```

To print or write the template without shell-specific scripts:

不使用系统脚本时，也可以直接打印或写入模板：

```bash
chatgpt-codex permissions-template
chatgpt-codex permissions-template --output .chatgpt-codex/permissions.json
```

### AI-Native CLI Management / AI-Native 本地命令管理

Agents should use machine-readable commands first:

Agent 应优先使用机器可读命令：

```bash
chatgpt-codex status
chatgpt-codex ai-commands
chatgpt-codex set-public-url https://your-current-public-url
chatgpt-codex verify
```

`status` reports config paths, active workspace, registered workspaces, local/public URLs, helper availability, and whether a token is configured. It never prints the bearer token itself.

`status` 会报告配置路径、当前工作区、已登记工作区、本地/公网 URL、辅助工具状态，以及 token 是否已配置。它不会打印 bearer token 原文。

`ai-commands` prints the local command catalog for setup, inspection, workspace switching, Builder fields, and runtime.

`ai-commands` 会打印本地命令目录，覆盖配置、检查、工作区切换、Builder 字段和运行时。

When a temporary tunnel prints a new public URL, save it with `set-public-url` so OpenAPI and Builder fields stay aligned. Use `verify` after the server and public route are running.

临时隧道输出新的公网 URL 后，用 `set-public-url` 保存，确保 OpenAPI 和 Builder 字段一致。服务和公网入口启动后，用 `verify` 做闭环检查。

Closed-loop product flow:

产品闭环流程：

1. Collect minimal human inputs and local authorization.
2. Install and create `.chatgpt-codex/config.json`.
3. Register authorized workspaces and select `active_workspace`.
4. Start the local server.
5. Start or provide a public HTTPS route.
6. Save the final public URL with `set-public-url`.
7. Run `verify`.
8. Configure ChatGPT Builder with `gpt-instructions`, `openapi.json`, and `token`.
9. In GPT chat, use `workspace_status`, `list_workspaces`, and `switch_workspace` before file or command work.

中文：

1. 收集真人最小输入和本地授权。
2. 安装并创建 `.chatgpt-codex/config.json`。
3. 登记已授权工作区并选择 `active_workspace`。
4. 启动本地服务。
5. 启动或提供公网 HTTPS 入口。
6. 用 `set-public-url` 保存最终公网 URL。
7. 运行 `verify`。
8. 用 `gpt-instructions`、`openapi.json` 和 `token` 配置 ChatGPT Builder。
9. 在 GPT 对话里，文件或命令操作前使用 `workspace_status`、`list_workspaces` 和 `switch_workspace`。

### Manual Setup / 手动配置

macOS Terminal:

macOS 终端：

```bash
git clone git@github.com:hutiefang76/chatgpt-codex.git
cd chatgpt-codex
./scripts/install.sh
```

Windows PowerShell:

Windows PowerShell：

```powershell
git clone git@github.com:hutiefang76/chatgpt-codex.git
cd chatgpt-codex
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

The install script creates `.venv/` and a local `chatgpt-codex` launcher. It does not install runtime dependencies.

安装脚本会创建 `.venv/` 和本地 `chatgpt-codex` 启动器，不安装任何运行时第三方依赖。

Initialize a local config:

初始化本地配置：

macOS Terminal:

macOS 终端：

```bash
. .venv/bin/activate
chatgpt-codex init \
  --workspace /absolute/path/to/your/project \
  --public-base-url https://chatgpt-codex.example.com
```

Windows PowerShell:

Windows PowerShell：

```powershell
. .\.venv\Scripts\Activate.ps1
chatgpt-codex init `
  --workspace "C:\absolute\path\to\your\project" `
  --public-base-url https://chatgpt-codex.example.com
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass -Force` in that terminal and retry activation.

如果 PowerShell 阻止激活脚本，在当前终端运行 `Set-ExecutionPolicy -Scope Process Bypass -Force`，然后重新激活。

Start the local server:

启动本地服务：

```bash
chatgpt-codex serve
```

### Switching Projects In GPT / 在 GPT 里切换项目

Register every project locally first. GPT can only switch between these authorized names; it cannot switch to an arbitrary path typed in chat.

先在本地登记每个项目。GPT 只能在这些已授权名称之间切换，不能切换到对话里临时输入的任意路径。

```bash
chatgpt-codex workspace add --name demo --path /Users/me/project/demo --activate
chatgpt-codex workspace add --name notes --path "/Users/hutiefang/project/ggu/课程笔记"
chatgpt-codex workspace list
```

In ChatGPT, the user can say:

在 ChatGPT 里，用户可以直接说：

```text
当前项目是什么？
切换到 notes
列一下当前目录
```

The GPT should call `workspace_status`, `list_workspaces`, and `switch_workspace`, then show the active local directory before file, code, or command work.

GPT 应调用 `workspace_status`、`list_workspaces` 和 `switch_workspace`，并在文件、代码或命令操作前显示当前本地目录。

At this point the local API is running. For ChatGPT web to call it, expose it through a public HTTPS route. With the built-in quick tunnel, run in another terminal:

此时本地 API 已经可运行。若要让 ChatGPT 网页端调用它，需要通过公网 HTTPS 入口暴露服务。使用内置临时隧道时，在另一个终端运行：


```bash
chatgpt-codex tunnel
```

If you already have your own HTTPS route, point it at the local server instead.

如果你已经有自己的 HTTPS 入口，把它指向本地服务即可。

After the public URL is known:

拿到公网 URL 后：

```bash
chatgpt-codex set-public-url https://your-current-public-url
chatgpt-codex verify
```

Route choices:

入口方案：

- `local-only`: no `cloudflared`, no domain, local testing only.
- `local-only`：不需要 `cloudflared`，不需要域名，仅本地测试。
- `built-in-quick-tunnel`: requires `cloudflared`, no domain, gives a temporary public HTTPS URL.
- `built-in-quick-tunnel`：需要 `cloudflared`，不需要域名，提供临时公网 HTTPS 地址。
- `custom-domain`: requires a domain, but this project does not require `cloudflared` unless your chosen routing does.
- `custom-domain`：需要域名；本项目不强制 `cloudflared`，除非你的路由方案需要。
- `existing-https-route`: no `cloudflared` and no new domain if you already have a public HTTPS URL.
- `existing-https-route`：如果已有公网 HTTPS URL，不需要 `cloudflared`，也不需要新域名。

For a stable custom domain with the built-in tunnel approach, point the public route at:

如果你想使用内置隧道方案绑定稳定自定义域名，请把公网路由指向：

```text
http://127.0.0.1:8766
```

Then set `public_base_url` in `.chatgpt-codex/config.json` to your HTTPS route. With a Cloudflare-managed domain, use the fixed hostname `chatgpt-codex.<domain>`, for example:

然后把 `.chatgpt-codex/config.json` 里的 `public_base_url` 改成你的 HTTPS 入口。如果使用 Cloudflare 管理的域名，固定使用 `chatgpt-codex.<domain>`，例如：

```json
{
  "token": "keep-this-secret",
  "host": "127.0.0.1",
  "port": 8766,
  "public_base_url": "https://chatgpt-codex.hutiefang.net",
  "workspaces": {
    "demo": "/absolute/path/to/your/project"
  },
  "active_workspace": "demo"
}
```

On Windows, use an absolute path such as `C:\\absolute\\path\\to\\your\\project` in JSON, or use forward slashes like `C:/absolute/path/to/your/project`.

Windows 上的 JSON 路径可使用 `C:\\absolute\\path\\to\\your\\project`，也可以使用 `C:/absolute/path/to/your/project`。

## ChatGPT Builder Setup / ChatGPT Builder 配置

If browser automation is approved in `.chatgpt-codex/permissions.json`, Codex can open ChatGPT Builder for the user:

如果 `.chatgpt-codex/permissions.json` 已授权浏览器自动化，Codex 可以为用户打开 ChatGPT Builder：

```bash
chatgpt-codex open-chatgpt
```

The user logs in manually if needed. The agent should never ask for or save ChatGPT passwords, cookies, or browser session data. After login, the agent can use the printed Builder fields to complete the GPT configuration in Chrome when browser automation is available.

如果需要登录，用户自己在浏览器里完成。Agent 不应索要或保存 ChatGPT 密码、cookie 或浏览器会话数据。用户登录后，在具备浏览器自动化能力时，agent 可以用打印出的 Builder 字段在 Chrome 中完成 GPT 配置。

Print the exact setup text:

打印要粘贴到 Builder 里的配置说明：

```bash
chatgpt-codex gpt-instructions
```

In ChatGPT:

在 ChatGPT 中：

1. Open `Explore GPTs` -> `Create`.
2. Paste the printed instructions into the GPT instructions.
3. Add an Action.
4. Authentication: `API key`.
5. Auth type: `Bearer`.
6. API key: output of `chatgpt-codex token`.
7. Import schema URL: `https://your-domain/openapi.json`.
8. Privacy policy: `https://your-domain/privacy`.
9. Save as `Only me` unless you intentionally want to share it.

中文步骤：

1. 打开 `探索 GPT` -> `创建`。
2. 把 `chatgpt-codex gpt-instructions` 打印的内容粘贴到 GPT Instructions。
3. 添加一个 Action。
4. Authentication 选择 `API key`。
5. Auth type 选择 `Bearer`。
6. API key 填入 `chatgpt-codex token` 输出的 token。
7. Import schema URL 填：`https://your-domain/openapi.json`。
8. Privacy policy 填：`https://your-domain/privacy`。
9. 保存时建议选择 `Only me` / `只有我`，除非你明确想共享这个 GPT。

## Available Actions / 可用 Actions

- `list_files`: list files and directories. / 列出文件和目录。
- `read_file`: read a UTF-8 file. / 读取 UTF-8 文件。
- `search_text`: search workspace text. / 搜索工作区文本。
- `write_file`: create or replace a file. / 创建或替换文件。
- `apply_patch`: apply a limited `apply_patch` style patch. / 应用受限的 `apply_patch` 风格补丁。
- `exec_command`: run a shell command after safety checks. / 通过安全检查后执行 shell 命令。
- `workspace_status`: show the active workspace name and local path. / 显示当前工作区名称和本地路径。
- `list_workspaces`: list authorized workspaces. / 列出已授权工作区。
- `switch_workspace`: switch to an authorized workspace by name. / 按名称切换到已授权工作区。

## Security Model / 安全模型

This tool gives ChatGPT real access to a local workspace. Treat the bearer token like a password.

这个工具会让 ChatGPT 真正访问你的本地工作区。请把 bearer token 当作密码保管。

Built-in guardrails:

内置防护：

- All file paths must stay inside the configured workspace.
- 所有文件路径必须位于配置的 workspace 内。
- Project switching is limited to workspaces registered in `.chatgpt-codex/config.json`.
- 项目切换仅限 `.chatgpt-codex/config.json` 中登记过的工作区。
- Hidden implementation state such as `.git`, `.venv`, `node_modules`, and caches are skipped by file listing and search.
- 文件列表和搜索会跳过 `.git`、`.venv`、`node_modules`、缓存等实现细节目录。
- POST actions require `Authorization: Bearer <token>`.
- 所有 POST Action 都要求 `Authorization: Bearer <token>`。
- Commands like `rm -rf`, `git reset --hard`, `sudo`, `reboot`, `mkfs`, and similar destructive operations are blocked.
- 默认拦截 `rm -rf`、`git reset --hard`、`sudo`、`reboot`、`mkfs` 等危险操作。
- The project never needs your ChatGPT password, cookies, or API key.
- 本项目不需要你的 ChatGPT 密码、cookie 或 OpenAI API key。

Still important:

仍然要注意：

- Do not publish your `.chatgpt-codex/config.json`.
- 不要公开 `.chatgpt-codex/config.json`。
- Do not share a GPT that uses your private bearer token.
- 不要共享使用你私人 bearer token 的 GPT。
- Review action confirmations in ChatGPT before approving calls.
- 在 ChatGPT 里确认 Action 调用前，先检查它要执行的内容。
- Run it against one project workspace, not your home directory.
- 只把它指向具体项目目录，不要直接指向你的 home 目录。

## Development / 开发

Run tests:

运行测试：

macOS:

macOS：

```bash
python3 -m unittest discover -s tests
```

Windows PowerShell:

Windows PowerShell：

```powershell
py -3 -m unittest discover -s tests
```

Run without installing:

无需安装直接运行：

macOS:

macOS：

```bash
python3 -m chatgpt_codex --help
```

Windows PowerShell:

Windows PowerShell：

```powershell
py -3 -m chatgpt_codex --help
```

## Stop Services / 停止服务

Stop the server with `Ctrl-C`.

用 `Ctrl-C` 停止本地 server。

If you started a quick tunnel, stop that terminal with `Ctrl-C` as well.

如果启动了临时 tunnel，也在对应终端按 `Ctrl-C` 停止。
