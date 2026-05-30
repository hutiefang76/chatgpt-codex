# Security Lifecycle / 安全生命周期

ChatGPT Codex exposes a local workspace through HTTP Actions. The safe operating model is: private GPT, private bearer token, explicit workspace registry, short access session, and a tunnel process that is stopped when work is done.

ChatGPT Codex 会通过 HTTP Actions 暴露本地 workspace。推荐安全模型是：私有 GPT、私有 bearer token、明确登记的 workspace、短时访问会话，以及任务完成后停止隧道进程。

## Layers / 分层

1. Public HTTPS route: lets ChatGPT web reach your computer while the tunnel or route is running.
2. Bearer token: required for every POST Action that can read, write, switch workspace, patch, search, or execute.
3. Access expiry: optional but recommended TTL enforced by the local server before each POST Action.
4. Workspace boundary: every path must resolve inside an authorized workspace.
5. Command policy: common destructive commands are blocked before shell execution.

中文：

1. 公网 HTTPS 入口：隧道或路由运行期间，让 ChatGPT 网页端能访问你的电脑。
2. Bearer token：所有可能读写、切换工作区、打补丁、搜索或执行命令的 POST Action 都必须携带。
3. 访问过期时间：推荐设置 TTL；本地服务会在每次 POST Action 前强制检查。
4. Workspace 边界：所有路径都必须解析在已授权 workspace 内。
5. 命令策略：常见破坏性命令会在进入 shell 前被拦截。

## Recommended Commands / 推荐命令

```bash
chatgpt-codex serve --ttl-minutes 120
chatgpt-codex tunnel
chatgpt-codex access status
chatgpt-codex api-smoke
chatgpt-codex verify
```

Refresh the token when needed:

需要刷新 token 时：

```bash
chatgpt-codex rotate-token --ttl-minutes 120
```

Stop exposure immediately:

需要立即停止暴露时：

```bash
chatgpt-codex access revoke
```

`access revoke` expires the current access session and rotates the token without printing the new token. Use `rotate-token` when you intentionally need a new token for ChatGPT Builder.

`access revoke` 会让当前访问会话立即过期，并轮换 token 但不打印新 token。只有在你确实需要更新 ChatGPT Builder 鉴权字段时，才使用 `rotate-token`。

## Duration / 有效期

The local server is reachable while its process is running. A temporary tunnel is reachable while its process is running and usually gets a new URL after restart. A custom HTTPS route can stay stable, but Actions still require the current bearer token and an active access session.

本地服务在进程运行期间可达。临时隧道在进程运行期间可达，重启后通常会得到新 URL。自定义 HTTPS 入口可以保持稳定，但 Action 仍然需要当前 bearer token 和有效访问会话。

With `--ttl-minutes`, POST Actions return `403` after expiry even if the server and tunnel are still running. Public GET endpoints such as `/health`, `/openapi.json`, and `/privacy` remain readable because ChatGPT Builder needs them for setup.

使用 `--ttl-minutes` 后，即使服务和隧道仍在运行，过期后的 POST Actions 也会返回 `403`。`/health`、`/openapi.json` 和 `/privacy` 这类公开 GET 端点仍可读取，因为 ChatGPT Builder 配置时需要它们。

## Token Handling / Token 处理

The token is stored in `.chatgpt-codex/config.json`, which is ignored by Git. `status`, `doctor`, and `access status` do not print the token. `token` and `rotate-token` are intentionally explicit commands because their output must be pasted into ChatGPT Builder.

token 存在 `.chatgpt-codex/config.json`，该文件会被 Git 忽略。`status`、`doctor` 和 `access status` 不打印 token。`token` 和 `rotate-token` 是有意设计的显式命令，因为它们的输出需要粘贴到 ChatGPT Builder。
