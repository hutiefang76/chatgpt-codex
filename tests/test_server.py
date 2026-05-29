import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from chatgpt_codex.config import AppConfig
from chatgpt_codex.server import create_server


def open_without_proxy(request):
    opener = build_opener(ProxyHandler({}))
    return opener.open(request, timeout=5)


class ServerTests(unittest.TestCase):
    def test_server_requires_bearer_token_for_actions(self):
        with tempfile.TemporaryDirectory() as workspace:
            server = create_server(
                AppConfig(
                    workspace=Path(workspace),
                    token="secret-token",
                    host="127.0.0.1",
                    port=0,
                    public_base_url="https://actions.example.com",
                )
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/list_files"
                request = Request(url, data=b"{}", method="POST", headers={"Content-Type": "application/json"})

                with self.assertRaises(HTTPError) as raised:
                    open_without_proxy(request)

                self.assertEqual(raised.exception.code, 401)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_authorized_list_files_action_returns_workspace_entries(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            (root / "hello.txt").write_text("hello", encoding="utf-8")
            server = create_server(
                AppConfig(
                    workspace=root,
                    token="secret-token",
                    host="127.0.0.1",
                    port=0,
                    public_base_url="https://actions.example.com",
                )
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/list_files"
                payload = json.dumps({"path": ".", "recursive": True}).encode("utf-8")
                request = Request(
                    url,
                    data=payload,
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer secret-token",
                    },
                )

                response = open_without_proxy(request)
                body = json.loads(response.read().decode("utf-8"))

                self.assertEqual(response.status, 200)
                self.assertEqual(body["entries"][0]["path"], "hello.txt")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
