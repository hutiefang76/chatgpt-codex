import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .security import generate_token


# Local-only configuration. The generated token is a secret and should not be
# committed or shared.
# 本机配置文件。自动生成的 token 是密钥，不应提交或分享。
DEFAULT_CONFIG_DIR = ".chatgpt-codex"
DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_PERMISSIONS_FILE = "permissions.json"

ACCESS_PLANS = {
    "local-only": {
        "needs_public_https": False,
        "needs_cloudflared": False,
        "needs_domain": False,
    },
    "built-in-quick-tunnel": {
        "needs_public_https": True,
        "needs_cloudflared": True,
        "needs_domain": False,
    },
    "custom-domain": {
        "needs_public_https": True,
        "needs_cloudflared": False,
        "needs_domain": True,
    },
    "existing-https-route": {
        "needs_public_https": True,
        "needs_cloudflared": False,
        "needs_domain": False,
    },
}


@dataclass
class AppConfig:
    """Runtime settings for one exposed workspace.

    单个已暴露工作区的运行配置。
    """

    workspace: Path
    token: str
    host: str = "127.0.0.1"
    port: int = 8766
    public_base_url: str = "https://example.com"

    @classmethod
    def default(cls, workspace: Path) -> "AppConfig":
        return cls(workspace=Path(workspace).expanduser().resolve(), token=generate_token())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        return cls(
            workspace=Path(data["workspace"]).expanduser().resolve(),
            token=str(data["token"]),
            host=str(data.get("host", "127.0.0.1")),
            port=int(data.get("port", 8766)),
            public_base_url=str(data.get("public_base_url", "https://example.com")).rstrip("/"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace": str(self.workspace),
            "token": self.token,
            "host": self.host,
            "port": self.port,
            "public_base_url": self.public_base_url.rstrip("/"),
        }


@dataclass
class SetupPermissions:
    """User-approved setup choices saved inside the project.

    保存在项目内的用户授权和配置选项。
    """

    workspace: Path
    operating_system: str
    access_plan: str
    public_base_url: str
    allow_browser_automation: bool = False
    allow_start_services: bool = False
    allow_install_helpers: bool = False
    allow_workspace_write: bool = False
    allow_command_execution: bool = False
    hostname: str = ""
    created_at: str = ""

    @classmethod
    def create(
        cls,
        workspace: Path,
        operating_system: str,
        access_plan: str,
        public_base_url: str,
        allow_browser_automation: bool = False,
        allow_start_services: bool = False,
        allow_install_helpers: bool = False,
        allow_workspace_write: bool = False,
        allow_command_execution: bool = False,
        hostname: str = "",
    ) -> "SetupPermissions":
        if access_plan not in ACCESS_PLANS:
            raise ValueError(f"unknown access plan: {access_plan}")
        return cls(
            workspace=Path(workspace).expanduser().resolve(),
            operating_system=operating_system,
            access_plan=access_plan,
            public_base_url=public_base_url.rstrip("/"),
            allow_browser_automation=allow_browser_automation,
            allow_start_services=allow_start_services,
            allow_install_helpers=allow_install_helpers,
            allow_workspace_write=allow_workspace_write,
            allow_command_execution=allow_command_execution,
            hostname=hostname,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SetupPermissions":
        return cls(
            workspace=Path(data["workspace"]).expanduser().resolve(),
            operating_system=str(data["operating_system"]),
            access_plan=str(data["access_plan"]),
            public_base_url=str(data["public_base_url"]).rstrip("/"),
            allow_browser_automation=bool(data.get("allow_browser_automation", False)),
            allow_start_services=bool(data.get("allow_start_services", False)),
            allow_install_helpers=bool(data.get("allow_install_helpers", False)),
            allow_workspace_write=bool(data.get("allow_workspace_write", False)),
            allow_command_execution=bool(data.get("allow_command_execution", False)),
            hostname=str(data.get("hostname", "")),
            created_at=str(data.get("created_at", "")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace": str(self.workspace),
            "operating_system": self.operating_system,
            "access_plan": self.access_plan,
            "public_base_url": self.public_base_url.rstrip("/"),
            "allow_browser_automation": self.allow_browser_automation,
            "allow_start_services": self.allow_start_services,
            "allow_install_helpers": self.allow_install_helpers,
            "allow_workspace_write": self.allow_workspace_write,
            "allow_command_execution": self.allow_command_execution,
            "hostname": self.hostname,
            "created_at": self.created_at,
        }


def config_path(base_dir: Path) -> Path:
    return Path(base_dir) / DEFAULT_CONFIG_DIR / DEFAULT_CONFIG_FILE


def permissions_path(base_dir: Path) -> Path:
    return Path(base_dir) / DEFAULT_CONFIG_DIR / DEFAULT_PERMISSIONS_FILE


def load_config(path: Path) -> AppConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        return AppConfig.from_dict(json.load(handle))


def load_permissions(path: Path) -> SetupPermissions:
    with Path(path).open("r", encoding="utf-8") as handle:
        return SetupPermissions.from_dict(json.load(handle))


def save_config(config: AppConfig, path: Path, overwrite: bool = False) -> None:
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"config already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(config.to_dict(), handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    _set_private_permissions(target)


def save_permissions(permissions: SetupPermissions, path: Path, overwrite: bool = False) -> None:
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"permissions already exist: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(permissions.to_dict(), handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    _set_private_permissions(target)


def _set_private_permissions(path: Path) -> None:
    if os.name == "nt":
        # Windows privacy is controlled by the user's profile ACLs. chmod only
        # maps to the readonly bit there, so applying 0600 would be misleading.
        # Windows 上的隐私由用户目录 ACL 控制；chmod 只映射只读位。
        return
    Path(path).chmod(0o600)
