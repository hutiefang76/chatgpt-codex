# Security Lifecycle / 安全生命周期

ChatGPT Codex exposes a local workspace through HTTP Actions. The safe personal-use model is: private GPT, private bearer token, explicit workspace registry, and a tunnel process that you stop when work is done. Access does not expire by default so long coding sessions are not interrupted.

ChatGPT Codex 会通过 HTTP Actions 暴露本地 workspace。推荐的个人自用安全模型是：私有 GPT、私有 bearer token、明确登记的 workspace，以及任务完成后停止隧道进程。访问默认不过期，避免长时间写代码时被中断。

## Layers / 分层

1. Public HTTPS route: lets ChatGPT web reach your computer while the tunnel or route is running.
2. Bearer token: required for every POST Action that can read, write, switch workspace, patch, search, or execute.
3. Access expiry: optional TTL enforced by the local server before each POST Action when explicitly enabled.
4. Workspace boundary: every path must resolve inside an authorized workspace.
5. Command policy: common destructive commands are blocked before shell execution.

中文：

1. 公网 HTTPS 入口：隧道或路由运行期间，让 ChatGPT 网页端能访问你的电脑。
2. Bearer token：所有可能读写、切换工作区、打补丁、搜索或执行命令的 POST Action 都必须携带。
3. 访问过期时间：显式开启时可设置 TTL；本地服务会在每次 POST Action 前强制检查。
4. Workspace 边界：所有路径都必须解析在已授权 workspace 内。
5. 命令策略：常见破坏性命令会在进入 shell 前被拦截。

## Recommended Commands / 推荐命令

```bash
chatgpt-codex serve
chatgpt-codex tunnel
chatgpt-codex access status
chatgpt-codex api-smoke
chatgpt-codex verify
```

Optional short-lived session:

可选短时会话：

```bash
chatgpt-codex serve --ttl-minutes 120
```

Refresh the token when needed:

需要刷新 token 时：

```bash
chatgpt-codex rotate-token
```

Stop exposure immediately:

需要立即停止暴露时：

```bash
chatgpt-codex access revoke
```

`access revoke` expires the current access session and rotates the token without printing the new token. Use `rotate-token` when you intentionally need a new token for ChatGPT Builder.

`access revoke` 会让当前访问会话立即过期，并轮换 token 但不打印新 token。只有在你确实需要更新 ChatGPT Builder 鉴权字段时，才使用 `rotate-token`。

## Duration / 有效期

The local server is reachable while its process is running. A temporary tunnel is reachable while its process is running and usually gets a new URL after restart. A custom HTTPS route can stay stable, but Actions still require the current bearer token. If no TTL is configured, the access session is active until you stop the service or run `chatgpt-codex access revoke`.

本地服务在进程运行期间可达。临时隧道在进程运行期间可达，重启后通常会得到新 URL。自定义 HTTPS 入口可以保持稳定，但 Action 仍然需要当前 bearer token。如果未配置 TTL，访问会话会一直有效，直到你停止服务或运行 `chatgpt-codex access revoke`。

With `--ttl-minutes`, POST Actions return `403` after expiry even if the server and tunnel are still running. Public GET endpoints such as `/health`, `/openapi.json`, and `/privacy` remain readable because ChatGPT Builder needs them for setup.

使用 `--ttl-minutes` 后，即使服务和隧道仍在运行，过期后的 POST Actions 也会返回 `403`。`/health`、`/openapi.json` 和 `/privacy` 这类公开 GET 端点仍可读取，因为 ChatGPT Builder 配置时需要它们。

## Token Handling / Token 处理

The token is stored in `.chatgpt-codex/config.json`, which is ignored by Git. `status`, `doctor`, and `access status` do not print the token. `token` and `rotate-token` are intentionally explicit commands because their output must be pasted into ChatGPT Builder.

token 存在 `.chatgpt-codex/config.json`，该文件会被 Git 忽略。`status`、`doctor` 和 `access status` 不打印 token。`token` 和 `rotate-token` 是有意设计的显式命令，因为它们的输出需要粘贴到 ChatGPT Builder。

Knowing the tunnel URL is not enough to operate the workspace. All POST Actions require `Authorization: Bearer <token>`. A random visitor with only the URL can read setup metadata such as `/openapi.json`, but cannot list files, read files, write files, switch projects, patch files, search text, or run commands.

仅知道隧道 URL 不足以操作 workspace。所有 POST Actions 都要求 `Authorization: Bearer <token>`。只有 URL 的随机访问者最多能读取 `/openapi.json` 这类配置元数据，不能列文件、读文件、写文件、切换项目、打补丁、搜索文本或执行命令。
