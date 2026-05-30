# Claude Playbook / Claude 执行手册

Use [skills/chatgpt-codex/SKILL.md](./skills/chatgpt-codex/SKILL.md), then follow [AGENTS.md](./AGENTS.md) if more repository-level context is needed.

请优先使用 [skills/chatgpt-codex/SKILL.md](./skills/chatgpt-codex/SKILL.md)，需要更多仓库级上下文时再参考 [AGENTS.md](./AGENTS.md)。

This repository is designed so Claude asks only for the minimal human inputs: Chrome login to ChatGPT, workspace path, optional Chrome login to Cloudflare, optional Cloudflare-managed domain, and local authorization. Claude then detects macOS or Windows, chooses a temporary HTTPS tunnel by default, uses `chatgpt-codex.<domain>` when Cloudflare login and domain are available, saves local setup permissions, verifies the service, and hands back or applies the exact ChatGPT Builder fields after the user logs into ChatGPT manually.

本仓库设计目标是让 Claude 只向用户索要真人必须提供的最小信息：Chrome 登录 ChatGPT、workspace 路径、可选的 Chrome 登录 Cloudflare、可选的 Cloudflare 管理域名，以及本地授权。随后 Claude 自动识别 macOS 或 Windows、默认选择临时 HTTPS 隧道、在 Cloudflare 登录和域名都具备时使用 `chatgpt-codex.<domain>`、保存本地配置授权、验证服务，并在用户手动登录 ChatGPT 后交付或填写可用于 ChatGPT Builder 的字段。

Prefer `chatgpt-codex channel register`, `chatgpt-codex channel status`, `chatgpt-codex serve`, and `chatgpt-codex api-smoke` before browser automation. Do not set a TTL for normal personal use unless the user asks for a short-lived session. Use `chatgpt-codex channel renew` when the Builder auth token or public URL must be refreshed, and `chatgpt-codex channel revoke` to disable the channel immediately.

浏览器自动化前，优先使用 `chatgpt-codex channel register`、`chatgpt-codex channel status`、`chatgpt-codex serve` 和 `chatgpt-codex api-smoke`。普通个人自用不要设置 TTL，除非用户明确要求短时会话。需要刷新 Builder 鉴权 token 或公网 URL 时用 `chatgpt-codex channel renew`，需要立即停用通道时用 `chatgpt-codex channel revoke`。
