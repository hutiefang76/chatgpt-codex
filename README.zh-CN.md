# ChatGPT 本地编程桥

[English](README.md) | [简体中文](README.zh-CN.md)

ChatGPT Codex 通过 Custom GPT Actions，把 ChatGPT 网页版变成可以读写本地代码的编程助手。生产级主路径是一条命令：用户只需要在打开的浏览器里登录 ChatGPT，然后等待本地桥、公网入口、Builder 配置和冒烟测试完成。

本地服务只依赖 Python 标准库即可运行。ChatGPT 网页端不能直接访问 `localhost`，所以真实使用 ChatGPT Actions 时需要公网 HTTPS 入口。内置 `tunnel` 命令使用 `cloudflared`；你也可以提供自己的 HTTPS 入口。

## 功能

- 为一个已注册本地 workspace 暴露带 Bearer 鉴权的 HTTP API。
- 让私有 GPT 在该 workspace 内列文件、读文件、搜索、写文件、打 patch、执行命令。
- 自动生成 ChatGPT Actions 可导入的 OpenAPI 文档。
- 所有文件路径都限制在已注册 workspace 根目录下。
- 只允许按已注册 workspace 名称切换项目，不允许任意路径跳转。
- 默认拦截常见危险 shell 命令。
- 为 Codex 或 Claude 提供 AI-native 命令目录，便于配置、检查和恢复。

## 环境要求

- 支持 macOS 和 Windows。
- Python 3.9 或更新版本。
- Builder 自动化需要带 `npx` 的 Node.js/npm。本地服务本身不需要 Node。
- 一个能创建带 Actions 的 Custom GPT 的 ChatGPT 账号或套餐。不要假设免费账号可以创建或编辑 GPT；先运行 `chatgpt-codex chatgpt-preflight`，并在登录后检查 Builder 页面。
- 本地系统允许该工具读写你配置的 workspace。
- 可选：`cloudflared`，仅用于内置 `chatgpt-codex tunnel` 命令，或 `setup` 默认使用的临时隧道。
- 可选：如果你想使用 `chatgpt-codex.example.com` 这类稳定域名，需要一个 Cloudflare 管理的域名。

## 真人必须提供的信息

目标体验要尽量少打扰真人：

1. 在 Playwright 持久化 profile 中真人登录 ChatGPT：必须。Agent 不得索要 ChatGPT 密码、cookie、会话或 API key。
2. Workspace 路径：必须，例如 `/Users/me/project/demo`。
3. 浏览器真人登录 Cloudflare：可选，仅用于稳定的 Cloudflare 托管域名。
4. Cloudflare 管理的域名：可选。如果提供，固定主机名是 `chatgpt-codex.<domain>`。
5. 本地授权：必须。允许 agent 自动识别系统、选择入口方案、安装必要辅助工具、启动服务、打开 Playwright 浏览器、在真人登录后配置 Builder、写入 workspace，并在 workspace 内执行命令。

默认行为：如果没有 Cloudflare 登录和域名，使用临时 HTTPS 隧道供 ChatGPT 网页端访问。如果两者都具备，使用 `chatgpt-codex.<domain>`。仅本地模式只用于测试或用户明确要求。

## 本地授权文件

AI-native 配置时，把用户的本地授权选择保存到 `.chatgpt-codex/permissions.json`。根目录的 `permissions.example.json` 是安全模板。用户可以在 macOS 用 `./scripts/prepare-permissions.sh` 复制，在 Windows PowerShell 用 `.\scripts\prepare-permissions.ps1` 复制；如果已提供必要答案，也可以让 agent 直接写入校验后的值：

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

## 快速开始

macOS：

```bash
git clone git@github.com:hutiefang76/chatgpt-codex.git
cd chatgpt-codex
./scripts/install.sh
. .venv/bin/activate
chatgpt-codex setup --workspace /absolute/path/to/your/project
```

Windows PowerShell：

```powershell
git clone git@github.com:hutiefang76/chatgpt-codex.git
cd chatgpt-codex
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
. .\.venv\Scripts\Activate.ps1
chatgpt-codex setup --workspace "C:\absolute\path\to\your\project"
```

如果 PowerShell 阻止激活脚本，在当前终端运行 `Set-ExecutionPolicy -Scope Process Bypass -Force`，然后重新激活。

`setup` 会准备本地桥、启动或使用公网 HTTPS 入口、验证 Action API、打开 ChatGPT Builder、等待真人登录、捕获保存后的 GPT 地址，并在可行时运行 `builder smoke`。临时隧道第一个地址不可达时会自动换新地址重试。完成后桥会继续运行，直到按 `Ctrl-C`。

只看计划、不启动浏览器和隧道：

```bash
chatgpt-codex setup --workspace /absolute/path/to/your/project --dry-run
```

## AI-Native 自动配置

把这个仓库交给 Codex 或 Claude，让它使用内置 skill：

- [skills/chatgpt-codex/SKILL.md](skills/chatgpt-codex/SKILL.md)

Agent 可读入口：

- [AGENTS.md](AGENTS.md)
- [CLAUDE.md](CLAUDE.md)
- [docs/AI_NATIVE.md](docs/AI_NATIVE.md)

也可以通过 CLI 打印交接说明：

```bash
chatgpt-codex skill
chatgpt-codex ai-native
chatgpt-codex agent-brief
```

Agent 应优先使用机器可读命令：

```bash
chatgpt-codex --lang zh status
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

`status` 会报告配置路径、当前 workspace、已注册 workspaces、本地/公网 URL、辅助工具状态、语言和 token 是否已配置。它永远不会打印 bearer token 原文。

`ai-commands` 会打印本地命令目录，覆盖语言选择、配置、检查、workspace 切换、Builder 字段、运行时和访问生命周期。

`chatgpt-preflight` 会打印 ChatGPT 侧前提条件、登录入口、Builder 自动化边界，以及从当前本地配置推导出的 Builder 字段；它不会打印 bearer token 原文。

`api-smoke` 会启动一个临时本地服务并直接测试 Action 接口：鉴权、健康检查、schema、workspace 状态、workspace 列表、文件列表/读取/写入/搜索/补丁、命令执行、workspace 切换和安全拦截。它不会触碰你的真实 workspace。

`setup-smoke` 是配置路径的确定性本地验收测试。它使用临时 workspace 验证本地服务、`api-smoke`、bootstrap 重新绑定 workspace、Builder dry-run 命令和 Node Builder bridge 自测，不需要登录 ChatGPT。

## Builder 自动化

默认 Builder 路径是 Playwright，并使用独立的持久化 profile。它不复用用户日常 Chrome profile，Chrome 插件不是默认依赖。用户只需要在 Playwright 浏览器里手动登录一次；GPT 保存后属于用户自己的 ChatGPT 账号，在普通浏览器里刷新也能看到。

常用命令：

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

`builder payload --json` 会生成 GPT 名称、描述、instructions、schema URL、privacy URL、可见性和自动化元数据，但不会打印 bearer token。

`builder setup` 会在 Playwright 持久化 profile 中打开 ChatGPT Builder，等待用户完成登录或浏览器验证，填写稳定的 Builder 字段，尝试自动配置 Action/鉴权/保存，等待保存后的 `https://chatgpt.com/g/...` 地址，并写入 `.chatgpt-codex/builder.json`。

如果 `builder setup` 在宽限时间后仍停在 ChatGPT 或 Cloudflare 验证页，它会返回 `stage: "builder_fallback_required"`，并给出机器可读的 Chrome/Computer Use 兜底交接信息。顶层 `setup` 遇到这种情况时会保持本地桥和公网入口继续运行，agent 可以直接用用户普通浏览器接管，不会丢掉已经保存的 URL 或 token。只有你明确想等到普通超时时，才使用 `--fallback none`。

`builder smoke` 会打开保存后的 GPT，提交一次 `workspace_status` 冒烟提示，并且只有页面出现 workspace 状态结果时才返回成功。`builder configure --mode hybrid` 会同时捕获脱敏后的 Builder 网络流量。`builder sniff` 是显式内部 API 发现流程：在打开的浏览器里执行一次 Builder 保存或配置动作，然后按 `Ctrl-C`，脱敏后的 route map 会保存到 `.chatgpt-codex/builder-routes.json`。

内部 API replay 必须留在同一个 Playwright 浏览器会话中执行。不要导出 cookie、session 或 ChatGPT 凭据。内部路由只作为不稳定的加速数据；验证不通过就回退到 UI 自动化。

## 通道生命周期

首次注册会把当前本地工具安装绑定到你传入的指定 workspace 路径。高层命令会自动完成：

```bash
chatgpt-codex setup --workspace /absolute/path/to/your/project
```

默认没有提供 Cloudflare 账号或域名时，setup 会最多尝试 6 个临时公网隧道地址，避免全新安装因为某一个随机 quick-tunnel 地址慢或不可达就直接失败。

如果你已经知道 HTTPS 地址，也可以使用底层注册命令：

```bash
chatgpt-codex channel register \
  --workspace /absolute/path/to/your/project \
  --public-base-url https://chatgpt-codex.example.com
```

本地密钥存储在仓库根目录的 `.chatgpt-codex/config.json`。这个文件包含公网 URL、已注册 workspace 路径、当前 workspace 名称和 bearer token。`.chatgpt-codex/` 会被 Git 忽略，macOS/Linux 上配置文件会写成私有权限。不要提交或公开它。

生命周期命令：

```bash
chatgpt-codex channel status
chatgpt-codex channel revoke
chatgpt-codex channel renew
chatgpt-codex channel renew --public-base-url https://new-public-url.example.com
chatgpt-codex channel renew --ttl-minutes 120
```

`channel status` 永不打印 token。`channel revoke` 会立即停用通道并静默轮换 token。`channel renew` 会重新激活访问，并只为 ChatGPT Builder 打印一次当前 token。

底层访问命令也保留：

```bash
chatgpt-codex rotate-token
chatgpt-codex access revoke
chatgpt-codex access status
```

默认个人自用访问在服务运行期间不过期。如果你明确想使用短时会话，可以用 `chatgpt-codex serve --ttl-minutes 120` 启动，或在 renew 时加 `--ttl-minutes`。

## 切换项目

添加另一个已授权项目：

```bash
chatgpt-codex workspace add --name api --path /absolute/path/to/api
chatgpt-codex workspace add --name web --path /absolute/path/to/web --activate
chatgpt-codex workspace list
chatgpt-codex workspace switch api
```

在 GPT 对话里，让 GPT 调用 `workspace_status`、`list_workspaces` 和 `switch_workspace`。文件或命令操作前，应先显示当前本地目录。

## 产品闭环流程

1. 收集真人最小输入和本地授权。
2. 在 macOS 或 Windows PowerShell 安装启动器。
3. 运行 `chatgpt-codex setup --workspace <path>`。
4. 在打开的 Playwright 浏览器里完成 ChatGPT 登录。
5. 让 setup 验证本地桥、配置 Builder、捕获保存后的 GPT 地址，并运行 `builder smoke`。
6. 如果 Playwright 返回 `builder_fallback_required`，让 agent 按输出交接信息使用 Chrome/Computer Use；setup 会保持桥存活。
7. 在 GPT 对话里，文件或命令操作前使用 `workspace_status`、`list_workspaces` 和 `switch_workspace`。

## 底层命令

`chatgpt-codex bootstrap` 仍可用于只配置本地侧。它会注册通道、启动服务、启动临时隧道并自动捕获公网 URL，然后验证并打印 Builder 字段。它不会执行高层 Builder setup 流程。

```bash
chatgpt-codex bootstrap --workspace /absolute/path/to/your/project
chatgpt-codex bootstrap --workspace /absolute/path/to/your/project --public-base-url https://actions.example.com
chatgpt-codex bootstrap --workspace /absolute/path/to/your/project --no-tunnel
```

## 开发验证

```bash
python3 -m unittest discover -s tests
py -3 -m unittest discover -s tests
node --check scripts/chatgpt_builder_playwright.mjs
chatgpt-codex setup-smoke
```
