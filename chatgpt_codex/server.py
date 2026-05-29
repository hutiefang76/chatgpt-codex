import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict

from .config import AppConfig
from .executor import CommandExecutor
from .openapi import make_openapi_document
from .workspace import WorkspaceTools


PRIVACY_TEXT = """ChatGPT Codex runs on your own computer.

Requests are processed locally against the workspace you configured. The project does not collect, store, or sell data. ChatGPT receives the action arguments and results needed to answer your prompt. Keep your bearer token private.

ChatGPT Codex 运行在你自己的电脑上。

请求会在你配置的 workspace 内本地处理。本项目不收集、不存储、不出售数据。ChatGPT 会收到回答你的请求所需的 Action 参数和结果。请妥善保管 bearer token。
"""


def create_server(config: AppConfig) -> ThreadingHTTPServer:
    """Create a bearer-protected HTTP action server.

    创建带 bearer 鉴权的 HTTP Action 服务。
    """

    workspace_tools = WorkspaceTools(config.workspace)
    executor = CommandExecutor(config.workspace)

    class Handler(BaseHTTPRequestHandler):
        server_version = "ChatGPTCodex/0.1"

        def do_GET(self):
            if self.path == "/health":
                self._send_json(
                    {
                        "ok": True,
                        "workspace": str(config.workspace),
                        "public_base_url": config.public_base_url.rstrip("/"),
                    }
                )
                return
            if self.path == "/openapi.json":
                self._send_json(make_openapi_document(config.public_base_url))
                return
            if self.path == "/privacy":
                self._send_text(PRIVACY_TEXT)
                return
            self._send_json({"error": "not found"}, status=404)

        def do_POST(self):
            if not self._authorized():
                self._send_json({"error": "missing or invalid bearer token"}, status=401)
                return
            actions: Dict[str, Callable[[Dict[str, Any]], Dict[str, object]]] = {
                "/list_files": lambda body: workspace_tools.list_files(
                    body.get("path", "."),
                    bool(body.get("recursive", True)),
                    body.get("pattern", "*"),
                    int(body.get("max_results", 200)),
                ),
                "/read_file": lambda body: workspace_tools.read_file(body["path"], int(body.get("max_bytes", 200000))),
                "/search_text": lambda body: workspace_tools.search_text(
                    body["query"],
                    body.get("path", "."),
                    int(body.get("max_results", 100)),
                    bool(body.get("regex", False)),
                ),
                "/write_file": lambda body: workspace_tools.write_file(body["path"], body.get("content", "")),
                "/apply_patch": lambda body: workspace_tools.apply_patch(body["patch"]),
                "/exec_command": lambda body: executor.run(
                    body["command"],
                    body.get("cwd", "."),
                    int(body.get("timeout_seconds", 60)),
                ),
            }
            action = actions.get(self.path)
            if action is None:
                self._send_json({"error": "not found"}, status=404)
                return
            try:
                self._send_json(action(self._read_json()))
            except KeyError as exc:
                self._send_json({"error": f"missing required field: {exc.args[0]}"}, status=400)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=400)

        def log_message(self, format, *args):
            return

        def _authorized(self) -> bool:
            expected = f"Bearer {config.token}"
            return self.headers.get("Authorization", "") == expected

        def _read_json(self) -> Dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw)

        def _send_json(self, value: Dict[str, object], status: int = 200) -> None:
            data = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_text(self, value: str, status: int = 200) -> None:
            data = value.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return ThreadingHTTPServer((config.host, config.port), Handler)
