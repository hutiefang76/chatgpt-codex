import contextlib
import io
import tempfile
import threading
import unittest
from pathlib import Path

from chatgpt_codex import cli
from chatgpt_codex.cli import TRYCLOUDFLARE_RE, main
from chatgpt_codex.config import AppConfig, save_config
from chatgpt_codex.server import create_server


class TunnelUrlCaptureTests(unittest.TestCase):
    def test_extracts_quick_tunnel_url(self):
        line = "2024-01-01T00:00:00Z INF |  https://blue-cat-runs-42.trycloudflare.com  |"
        match = TRYCLOUDFLARE_RE.search(line)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(0), "https://blue-cat-runs-42.trycloudflare.com")

    def test_ignores_unrelated_urls(self):
        self.assertIsNone(TRYCLOUDFLARE_RE.search("https://example.com/openapi.json"))


class BootstrapParserTests(unittest.TestCase):
    def test_bootstrap_subcommand_is_registered(self):
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main(["bootstrap", "--help"])
        self.assertEqual(raised.exception.code, 0)


class BootstrapCoreTests(unittest.TestCase):
    """Exercises the deterministic core of `bootstrap` against a live server.

    `_bootstrap` itself blocks (serve + tunnel), but its readiness path
    (`_wait_health` + `_verify_actions`) is the part with logic, and it must
    succeed against a running server with no AI involvement.
    """

    def test_wait_health_and_verify_against_live_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            (workspace / "a.txt").write_text("hi", encoding="utf-8")
            cfg = Path(tmp) / "config.json"
            config = AppConfig(
                token="demo-token",
                workspaces={"ws": workspace},
                active_workspace="ws",
                host="127.0.0.1",
                port=0,
                public_base_url="http://placeholder",
            )
            server = create_server(config, cfg)
            base = f"http://127.0.0.1:{server.server_port}"
            config.public_base_url = base
            save_config(config, cfg, overwrite=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                self.assertTrue(cli._wait_health(base, 10))
                result = cli._verify_actions(config, base, 10)
                self.assertTrue(result["ok"], msg=result)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
