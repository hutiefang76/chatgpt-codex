import argparse
import json
import platform
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

from .config import (
    ACCESS_PLANS,
    AppConfig,
    SetupPermissions,
    config_path,
    load_config,
    load_permissions,
    permissions_path,
    save_config,
    save_permissions,
)
from .openapi import make_openapi_document
from .server import create_server


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="chatgpt-codex",
        description="Local coding bridge for ChatGPT Custom GPT Actions. / ChatGPT Custom GPT Actions 的本地编程桥。",
    )
    parser.add_argument("--config", default=None, help="Path to config.json. / config.json 路径。Defaults to .chatgpt-codex/config.json.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    init_parser = subcommands.add_parser("init", help="Create a local config file. / 创建本地配置文件。")
    init_parser.add_argument("--workspace", default=".", help="Workspace ChatGPT may access. / ChatGPT 可访问的工作区。")
    init_parser.add_argument("--workspace-name", default="", help="Name for this workspace. / 这个工作区的名称。")
    init_parser.add_argument("--public-base-url", default="https://example.com", help="Public HTTPS base URL. / 公网 HTTPS 根地址。")
    init_parser.add_argument("--host", default="127.0.0.1")
    init_parser.add_argument("--port", type=int, default=8766)
    init_parser.add_argument("--force", action="store_true")

    subcommands.add_parser("doctor", help="Check local prerequisites. / 检查本地环境。")
    subcommands.add_parser("token", help="Print the configured bearer token. / 打印已配置的 bearer token。")
    subcommands.add_parser("openapi", help="Print the OpenAPI document. / 打印 OpenAPI 文档。")
    subcommands.add_parser("gpt-instructions", help="Print Custom GPT setup instructions. / 打印 Custom GPT 配置说明。")
    subcommands.add_parser("route-options", help="Explain HTTPS route choices. / 说明 HTTPS 入口选项。")
    subcommands.add_parser("permissions", help="Print saved setup permissions. / 打印已保存的配置授权。")
    template_parser = subcommands.add_parser("permissions-template", help="Print or write a permissions template. / 打印或写入授权模板。")
    template_parser.add_argument("--output", default="", help="Optional output path. / 可选输出路径。")
    template_parser.add_argument("--force", action="store_true")
    subcommands.add_parser("open-chatgpt", help="Open ChatGPT Builder in the browser. / 在浏览器打开 ChatGPT Builder。")
    subcommands.add_parser("agent-brief", help="Print AI-native setup handoff for Codex or Claude. / 打印给 Codex 或 Claude 的自动配置说明。")
    subcommands.add_parser("ai-native", help="Alias of agent-brief. / agent-brief 的别名。")
    subcommands.add_parser("skills", help="Print the bundled skill handoff. / 打印内置 skill 交接说明。")
    subcommands.add_parser("skill", help="Alias of skills. / skills 的别名。")

    serve_parser = subcommands.add_parser("serve", help="Start the local HTTP action server. / 启动本地 HTTP Action 服务。")
    serve_parser.add_argument("--host", default=None)
    serve_parser.add_argument("--port", type=int, default=None)

    workspace_parser = subcommands.add_parser("workspace", help="Manage authorized workspaces. / 管理已授权工作区。")
    workspace_subcommands = workspace_parser.add_subparsers(dest="workspace_command", required=True)
    workspace_subcommands.add_parser("status", help="Show active workspace. / 显示当前工作区。")
    workspace_subcommands.add_parser("list", help="List authorized workspaces. / 列出已授权工作区。")
    workspace_add = workspace_subcommands.add_parser("add", help="Add an authorized workspace. / 添加已授权工作区。")
    workspace_add.add_argument("--name", required=True, help="Workspace name used in ChatGPT. / ChatGPT 中使用的工作区名称。")
    workspace_add.add_argument("--path", required=True, help="Absolute or relative local path. / 本地路径。")
    workspace_add.add_argument("--activate", action="store_true", help="Make it the active workspace now. / 立即切换为当前工作区。")
    workspace_switch = workspace_subcommands.add_parser("switch", help="Switch active workspace. / 切换当前工作区。")
    workspace_switch.add_argument("name", help="Workspace name. / 工作区名称。")

    tunnel_parser = subcommands.add_parser("tunnel", help="Start the built-in cloudflared tunnel to the local server. / 启动内置 cloudflared 隧道。")
    tunnel_parser.add_argument("--cloudflared", default="cloudflared")

    authorize_parser = subcommands.add_parser("authorize", help="Save setup choices and permissions. / 保存配置选项和授权。")
    authorize_parser.add_argument("--workspace", default=".", help="Workspace ChatGPT may access. / ChatGPT 可访问的工作区。")
    authorize_parser.add_argument("--operating-system", choices=["auto", "macos", "windows"], default="auto")
    authorize_parser.add_argument("--access-plan", choices=sorted(ACCESS_PLANS), default="local-only")
    authorize_parser.add_argument("--public-base-url", default="https://example.com")
    authorize_parser.add_argument("--hostname", default="")
    authorize_parser.add_argument("--allow-browser-automation", action="store_true")
    authorize_parser.add_argument("--allow-start-services", action="store_true")
    authorize_parser.add_argument("--allow-install-helpers", action="store_true")
    authorize_parser.add_argument("--allow-workspace-write", action="store_true")
    authorize_parser.add_argument("--allow-command-execution", action="store_true")
    authorize_parser.add_argument("--force", action="store_true")

    args = parser.parse_args(argv)
    cfg_path = Path(args.config).expanduser() if args.config else config_path(Path.cwd())

    if args.command == "init":
        workspace_path = Path(args.workspace).expanduser().resolve()
        workspace_name = args.workspace_name or workspace_path.name or "default"
        config = AppConfig(
            workspace=workspace_path,
            token=AppConfig.default(Path(args.workspace)).token,
            host=args.host,
            port=args.port,
            public_base_url=args.public_base_url.rstrip("/"),
            workspaces={workspace_name: workspace_path},
            active_workspace=workspace_name,
        )
        save_config(config, cfg_path, overwrite=args.force)
        print(f"Config written / 配置已写入: {cfg_path}")
        print("Keep this bearer token private / 请妥善保管此 bearer token:")
        print(config.token)
        return 0

    if args.command in {"agent-brief", "ai-native", "skills", "skill"}:
        print(_agent_brief())
        return 0
    if args.command == "route-options":
        print(_route_options())
        return 0
    if args.command == "open-chatgpt":
        url = "https://chatgpt.com/gpts/editor"
        opened = _open_chrome_or_default(url)
        if opened:
            print(f"Opened ChatGPT Builder / 已打开 ChatGPT Builder: {url}")
        else:
            print(f"Failed to open ChatGPT Builder / 打开 ChatGPT Builder 失败: {url}", file=sys.stderr)
        return 0 if opened else 1
    if args.command == "authorize":
        perm_path = permissions_path(Path.cwd())
        permissions = SetupPermissions.create(
            workspace=Path(args.workspace),
            operating_system=_selected_os(args.operating_system),
            access_plan=args.access_plan,
            public_base_url=args.public_base_url,
            allow_browser_automation=args.allow_browser_automation,
            allow_start_services=args.allow_start_services,
            allow_install_helpers=args.allow_install_helpers,
            allow_workspace_write=args.allow_workspace_write,
            allow_command_execution=args.allow_command_execution,
            hostname=args.hostname,
        )
        save_permissions(permissions, perm_path, overwrite=args.force)
        print(f"Permissions written / 授权已写入: {perm_path}")
        print(_access_plan_summary(args.access_plan))
        return 0
    if args.command == "permissions":
        try:
            permissions = load_permissions(permissions_path(Path.cwd()))
        except FileNotFoundError:
            print("No saved permissions. Run `chatgpt-codex authorize` first. / 未找到已保存授权，请先运行 `chatgpt-codex authorize`。", file=sys.stderr)
            return 1
        print(json.dumps(permissions.to_dict(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "permissions-template":
        template = _permissions_template()
        if args.output:
            target = Path(args.output).expanduser()
            if target.exists() and not args.force:
                print(f"Template already exists / 模板已存在: {target}", file=sys.stderr)
                return 1
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("w", encoding="utf-8") as handle:
                json.dump(template, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            print(f"Template written / 模板已写入: {target}")
            return 0
        print(json.dumps(template, indent=2, ensure_ascii=False))
        return 0

    config = load_config(cfg_path)

    if args.command == "doctor":
        return _doctor(config)
    if args.command == "token":
        print(config.token)
        return 0
    if args.command == "openapi":
        print(json.dumps(make_openapi_document(config.public_base_url), indent=2, ensure_ascii=False))
        return 0
    if args.command == "gpt-instructions":
        print(_gpt_instructions(config))
        return 0
    if args.command == "workspace":
        return _workspace_command(args, config, cfg_path)
    if args.command == "serve":
        if args.host:
            config.host = args.host
        if args.port:
            config.port = args.port
        server = create_server(config, cfg_path)
        print(f"Serving / 正在服务 {config.active_workspace}:{config.workspace} at http://{config.host}:{server.server_port}")
        print(f"OpenAPI: {config.public_base_url.rstrip('/')}/openapi.json")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped / 已停止。")
        return 0
    if args.command == "tunnel":
        local_url = f"http://{config.host}:{config.port}"
        cloudflared = shutil.which(args.cloudflared)
        if not cloudflared:
            print("cloudflared not found in PATH. Install it to use this tunnel command, or provide your own public HTTPS route. / PATH 中找不到 cloudflared；如需使用此 tunnel 命令请先安装，或自行提供公网 HTTPS 入口。", file=sys.stderr)
            return 1
        return subprocess.call([cloudflared, "tunnel", "--url", local_url])

    parser.error(f"unknown command: {args.command}")
    return 2


def _doctor(config: AppConfig) -> int:
    ok = True
    print(f"OS / 操作系统: {_platform_label()}")
    print(f"Active workspace / 当前工作区: {config.active_workspace}")
    print(f"Workspace path / 工作区路径: {config.workspace}")
    if not config.workspace.exists():
        print("  FAIL workspace does not exist / 工作区不存在")
        ok = False
    else:
        print("  OK workspace exists / 工作区存在")
    print(f"Authorized workspaces / 已授权工作区: {len(config.workspaces)}")
    print(f"Local server / 本地服务: http://{config.host}:{config.port}")
    print(f"Public base URL / 公网根地址: {config.public_base_url}")
    print(f"Bearer token / Bearer token: {'OK set / 已设置' if config.token else 'FAIL missing / 缺失'}")
    if not config.token:
        ok = False
    print(f"cloudflared: {'OK found / 已找到' if shutil.which('cloudflared') else 'OPTIONAL missing / 可选，未找到，仅 tunnel 命令需要'}")
    return 0 if ok else 1


def _workspace_command(args, config: AppConfig, cfg_path: Path) -> int:
    if args.workspace_command == "status":
        print(json.dumps(config.workspace_status(), indent=2, ensure_ascii=False))
        return 0
    if args.workspace_command == "list":
        print(json.dumps({"active_workspace": config.active_workspace, "workspaces": config.workspace_entries()}, indent=2, ensure_ascii=False))
        return 0
    if args.workspace_command == "add":
        config.add_workspace(args.name, Path(args.path), activate=args.activate)
        save_config(config, cfg_path, overwrite=True)
        print(f"Workspace added / 已添加工作区: {args.name} -> {Path(args.path).expanduser().resolve()}")
        if args.activate:
            print(f"Active workspace / 当前工作区: {config.active_workspace}")
        return 0
    if args.workspace_command == "switch":
        status = config.switch_workspace(args.name)
        save_config(config, cfg_path, overwrite=True)
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return 0
    return 2


def _platform_label() -> str:
    system = platform.system() or sys.platform
    release = platform.release()
    return f"{system} {release}".strip()


def _selected_os(value: str) -> str:
    if value != "auto":
        return value
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    return system or sys.platform


def _open_chrome_or_default(url: str) -> bool:
    system = platform.system().lower()
    try:
        if system == "darwin" and shutil.which("open"):
            return subprocess.call(["open", "-a", "Google Chrome", url]) == 0
        if system == "windows":
            return subprocess.call(["cmd", "/c", "start", "", "chrome", url]) == 0
    except OSError:
        pass
    return bool(webbrowser.open(url))


def _route_options() -> str:
    return """Route options / 访问入口选项

local-only:
- cloudflared required: no
- domain required: no
- ChatGPT web Actions: no, local testing only
- cloudflared：不需要
- 域名：不需要
- ChatGPT 网页 Actions：不能真实调用，仅本地测试

built-in-quick-tunnel:
- cloudflared required: yes
- domain required: no
- ChatGPT web Actions: yes, with a temporary public HTTPS URL
- cloudflared：需要
- 域名：不需要
- ChatGPT 网页 Actions：可以，使用临时公网 HTTPS 地址

custom-domain:
- cloudflared required: no for this project, unless your chosen routing uses it
- domain required: yes
- ChatGPT web Actions: yes, with your stable HTTPS domain
- cloudflared：本项目不强制，除非你的路由方案需要
- 域名：需要
- ChatGPT 网页 Actions：可以，使用稳定 HTTPS 域名

existing-https-route:
- cloudflared required: no
- domain required: no, if you already have a public HTTPS URL
- ChatGPT web Actions: yes, with that HTTPS URL
- cloudflared：不需要
- 域名：不需要，前提是已有公网 HTTPS URL
- ChatGPT 网页 Actions：可以，使用已有 HTTPS 地址
"""


def _access_plan_summary(access_plan: str) -> str:
    plan = ACCESS_PLANS[access_plan]
    return (
        f"Access plan / 访问方案: {access_plan}\n"
        f"Public HTTPS required / 需要公网 HTTPS: {'yes / 是' if plan['needs_public_https'] else 'no / 否'}\n"
        f"cloudflared required / 需要 cloudflared: {'yes / 是' if plan['needs_cloudflared'] else 'no / 否'}\n"
        f"Domain required / 需要域名: {'yes / 是' if plan['needs_domain'] else 'no / 否'}"
    )


def _permissions_template() -> dict:
    return {
        "schema_version": 1,
        "workspace": "/absolute/path/to/your/project",
        "operating_system": "macos",
        "access_plan": "built-in-quick-tunnel",
        "public_base_url": "https://actions.example.com",
        "allow_browser_automation": True,
        "allow_start_services": True,
        "allow_install_helpers": True,
        "allow_workspace_write": True,
        "allow_command_execution": True,
        "hostname": "actions.example.com",
        "created_at": "",
    }


def _gpt_instructions(config: AppConfig) -> str:
    base = config.public_base_url.rstrip("/")
    return f"""Custom GPT setup / Custom GPT 配置

1. Open ChatGPT -> Explore GPTs -> Create.
   打开 ChatGPT -> Explore GPTs / 探索 GPT -> Create / 创建。
2. Instructions:
   Instructions / 指令：

You are my local coding assistant for the workspace exposed through Actions.
Use workspace_status before file, code, or command work so you can show the current local directory. Use list_workspaces and switch_workspace when I ask to view or switch projects. Only switch to authorized workspace names returned by list_workspaces. After switching, state the active workspace name and local path. Use list_files, read_file, search_text, write_file, apply_patch, and exec_command for project work. Inspect files before editing. Keep changes scoped. Do not run destructive commands unless I explicitly ask for that exact action in the current chat.

你是我的本地编程助手，通过 Actions 访问我暴露的 workspace。
当我询问文件、代码、命令或当前项目时，先使用 workspace_status 显示当前本地目录。当我要求查看或切换项目时，使用 list_workspaces 和 switch_workspace。只能切换到 list_workspaces 返回的已授权工作区名称。切换后说明当前工作区名称和本地路径。项目操作使用 list_files、read_file、search_text、write_file、apply_patch 和 exec_command。编辑前先检查文件。保持改动范围清晰。除非我在当前对话中明确要求执行某个危险操作，否则不要运行破坏性命令。

3. Actions:
   Actions / 动作：
   - Authentication / 鉴权方式: API key
   - Auth type / 类型: Bearer
   - API key: use the token printed by `chatgpt-codex token`
   - API key：填入 `chatgpt-codex token` 打印的 token
   - Import schema URL / 导入 schema 地址: {base}/openapi.json
   - Privacy policy / 隐私政策: {base}/privacy

4. Save the GPT as Only me unless you intentionally want to share access.
   保存时选择 Only me / 只有我，除非你明确想共享访问权限。
"""


def _agent_brief() -> str:
    return """Skill setup handoff / Skill 自动配置交接说明

Give this repository to Codex or Claude and ask it to use the bundled skill:

skills/chatgpt-codex/SKILL.md

Then ask it to complete the local ChatGPT Actions setup.

把这个仓库交给 Codex 或 Claude，并要求它使用内置 skill：

skills/chatgpt-codex/SKILL.md

然后让它完成本地 ChatGPT Actions 配置。

Agent mission / Agent 任务：
1. Ask only for the minimal human inputs.
   只向用户询问真人必须提供的最小信息。
2. Install the local launcher.
   安装本地启动器。
3. Save setup choices and permissions in .chatgpt-codex/permissions.json.
   将配置选项和授权保存到 .chatgpt-codex/permissions.json。
4. Create config for the target workspace.
   为目标 workspace 创建配置。
5. Start the local server. If ChatGPT web should call it, set up or use a public HTTPS route.
   启动本地服务。如果 ChatGPT 网页端需要调用它，请配置或使用公网 HTTPS 入口。
6. Open ChatGPT Builder in Chrome only after browser automation is approved and the user has logged in manually.
   只有在用户授权浏览器自动化并手动登录后，才在 Chrome 中打开 ChatGPT Builder。
7. Verify /health, /openapi.json, and at least one authenticated read-only action.
   验证 /health、/openapi.json，以及至少一个带鉴权的只读 Action。
8. Print or apply the ChatGPT Builder fields.
   打印或填写 ChatGPT Builder 字段。

Required user inputs / 需要用户提供：
- Chrome human login to ChatGPT: required / Chrome 真人登录 ChatGPT：必须
- workspace path: required / workspace 路径：必须
- Chrome human login to Cloudflare: optional / Chrome 真人登录 Cloudflare：可选
- Cloudflare-managed domain: optional / Cloudflare 管理的域名：可选
- local authorization for OS detection, route selection, helper install, service start, Chrome opening, Builder configuration after human login, workspace writes, and workspace command execution / 本地授权：允许自动识别系统、选择入口方案、安装辅助工具、启动服务、打开 Chrome、在真人登录后配置 Builder、写入 workspace、并在 workspace 内执行命令

Defaults / 默认：
- Detect macOS or Windows automatically and use port 8766 unless the user overrides it.
  自动识别 macOS 或 Windows，默认端口 8766，除非用户明确覆盖。
- If no Cloudflare login and domain are available, use a temporary HTTPS tunnel for ChatGPT web.
  没有 Cloudflare 登录和域名时，使用临时 HTTPS 隧道供 ChatGPT 网页端访问。
- If both are available, use the fixed hostname https://chatgpt-codex.<domain>.
  两者都具备时，使用固定域名 https://chatgpt-codex.<domain>。
- Use local-only only for tests or explicit user requests.
  仅在测试或用户明确要求时使用仅本地模式。
- The ChatGPT account must support Actions, and the GPT should be saved private unless the user intentionally shares access.
  ChatGPT 账号必须支持 Actions；除非用户明确要共享访问，否则 GPT 应保存为私有。

Do not ask for / 不要索要：
- ChatGPT password / ChatGPT 密码
- browser cookies / 浏览器 cookie
- OpenAI API key / OpenAI API key
- unrelated secrets / 无关密钥

Suggested command sequence on macOS / macOS 建议命令序列：
```bash
./scripts/install.sh
. .venv/bin/activate
chatgpt-codex route-options
chatgpt-codex authorize \\
  --workspace "$WORKSPACE" \\
  --operating-system auto \\
  --access-plan "$ACCESS_PLAN" \\
  --public-base-url "$PUBLIC_BASE_URL" \\
  --allow-browser-automation \\
  --allow-start-services \\
  --allow-install-helpers \\
  --allow-workspace-write \\
  --allow-command-execution
chatgpt-codex init --workspace "$WORKSPACE" --public-base-url "$PUBLIC_BASE_URL"
chatgpt-codex doctor
chatgpt-codex serve
```

Suggested command sequence on Windows PowerShell / Windows PowerShell 建议命令序列：
```powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\install.ps1
. .\\.venv\\Scripts\\Activate.ps1
$Workspace = "C:\\absolute\\path\\to\\project"
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
chatgpt-codex serve
```

In another terminal if using the built-in quick tunnel / 如果使用内置临时隧道，在另一个终端运行：
```bash
chatgpt-codex tunnel
```

If browser automation is approved and the user has logged into ChatGPT manually / 如果用户已授权浏览器自动化并手动登录 ChatGPT：
```bash
chatgpt-codex open-chatgpt
```

After verification, print / 验证后打印：
```bash
chatgpt-codex gpt-instructions
chatgpt-codex token
```

The user should paste the token only into ChatGPT Builder's Action authentication field.

用户只应把 token 粘贴到 ChatGPT Builder 的 Action 鉴权字段。
"""
