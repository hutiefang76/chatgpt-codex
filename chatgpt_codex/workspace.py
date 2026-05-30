import fnmatch
import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from .security import PathSandbox


# Skip implementation details and heavyweight dependency/cache folders by
# default so ChatGPT sees the project, not tool internals.
# 默认跳过实现细节和较重的依赖/缓存目录，让 ChatGPT 看到项目本身。
IGNORED_NAMES = {
    ".DS_Store",
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".svn",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}


class WorkspaceTools:
    """File, search, patch, and write tools scoped to one workspace.

    限定在单个 workspace 内的文件、搜索、补丁和写入工具。
    """

    def __init__(self, workspace: Path):
        self.sandbox = PathSandbox(Path(workspace))
        self.workspace = self.sandbox.workspace

    def list_files(
        self,
        path: str = ".",
        recursive: bool = True,
        pattern: str = "*",
        max_results: int = 200,
    ) -> Dict[str, object]:
        root = self.sandbox.resolve(path)
        entries: List[Dict[str, object]] = []
        max_results = max(1, int(max_results or 200))
        truncated = False

        for candidate in self._walk(root, recursive=recursive):
            relative = self.sandbox.relative(candidate)
            if relative == "." or self._is_ignored(candidate) or not fnmatch.fnmatch(candidate.name, pattern or "*"):
                continue
            if len(entries) >= max_results:
                # A further matching entry exists beyond the limit.
                truncated = True
                break
            stat = candidate.stat()
            entries.append(
                {
                    "path": relative,
                    "type": "directory" if candidate.is_dir() else "file",
                    "size": stat.st_size if candidate.is_file() else 0,
                    "modified": int(stat.st_mtime),
                }
            )

        entries.sort(key=lambda item: item["path"])
        return {
            "path": self.sandbox.relative(root),
            "entries": entries,
            "truncated": truncated,
        }

    def read_file(self, path: str, max_bytes: int = 200000) -> Dict[str, object]:
        target = self.sandbox.resolve(path)
        data = target.read_bytes()
        max_bytes = max(1, int(max_bytes or 200000))
        truncated = len(data) > max_bytes
        content = data[:max_bytes].decode("utf-8", errors="replace")
        return {
            "path": self.sandbox.relative(target),
            "content": content,
            "bytes": len(data),
            "truncated": truncated,
        }

    def write_file(self, path: str, content: str) -> Dict[str, object]:
        target = self.sandbox.resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = (content or "").encode("utf-8")
        target.write_bytes(data)
        return {
            "path": self.sandbox.relative(target),
            "bytes_written": len(data),
        }

    def search_text(
        self,
        query: str,
        path: str = ".",
        max_results: int = 100,
        regex: bool = False,
    ) -> Dict[str, object]:
        if not query:
            raise ValueError("query is required")
        root = self.sandbox.resolve(path)
        max_results = max(1, int(max_results or 100))
        matcher = re.compile(query) if regex else re.compile(re.escape(query))
        matches: List[Dict[str, object]] = []

        for candidate in self._walk(root, recursive=True):
            if candidate.is_dir() or self._is_ignored(candidate):
                continue
            try:
                lines = candidate.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(lines, start=1):
                found = matcher.search(line)
                if not found:
                    continue
                matches.append(
                    {
                        "path": self.sandbox.relative(candidate),
                        "line": line_number,
                        "column": found.start() + 1,
                        "text": line,
                    }
                )
                if len(matches) >= max_results:
                    return {"query": query, "matches": matches, "truncated": True}
        return {"query": query, "matches": matches, "truncated": False}

    def apply_patch(self, patch: str) -> Dict[str, object]:
        operations = _parse_patch(patch)
        changed: List[str] = []
        for operation in operations:
            op_type = operation["type"]
            target = self.sandbox.resolve(operation["path"])
            relative = self.sandbox.relative(target)
            if op_type == "add":
                if target.exists():
                    raise ValueError(f"file already exists: {relative}")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("\n".join(operation["lines"]) + "\n", encoding="utf-8")
            elif op_type == "delete":
                target.unlink()
            elif op_type == "update":
                original = target.read_text(encoding="utf-8").splitlines()
                updated = _apply_hunks(original, operation["hunks"], relative)
                target.write_text("\n".join(updated) + "\n", encoding="utf-8")
            else:
                raise ValueError(f"unsupported patch operation: {op_type}")
            changed.append(relative)
        return {"changed_files": changed}

    def _walk(self, root: Path, recursive: bool) -> Iterable[Path]:
        if root.is_file():
            yield root
            return
        if not recursive:
            for child in root.iterdir():
                if not self._is_ignored(child):
                    yield child
            return
        for current_root, dirs, files in os.walk(root):
            current = Path(current_root)
            dirs[:] = sorted(name for name in dirs if name not in IGNORED_NAMES)
            for dirname in dirs:
                yield current / dirname
            for filename in sorted(files):
                if filename not in IGNORED_NAMES:
                    yield current / filename

    def _is_ignored(self, path: Path) -> bool:
        return any(part in IGNORED_NAMES for part in path.relative_to(self.workspace).parts)


def _parse_patch(patch: str) -> List[Dict[str, object]]:
    """Parse a small, deterministic subset of apply_patch syntax.

    解析一个小而确定的 apply_patch 语法子集。
    """

    lines = patch.splitlines()
    if not lines or lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
        raise ValueError("patch must start with *** Begin Patch and end with *** End Patch")
    operations: List[Dict[str, object]] = []
    index = 1
    while index < len(lines) - 1:
        line = lines[index]
        if line.startswith("*** Add File: "):
            path = line.removeprefix("*** Add File: ")
            index += 1
            added: List[str] = []
            while index < len(lines) - 1 and not lines[index].startswith("*** "):
                if not lines[index].startswith("+"):
                    raise ValueError("add file lines must start with +")
                added.append(lines[index][1:])
                index += 1
            operations.append({"type": "add", "path": path, "lines": added})
        elif line.startswith("*** Delete File: "):
            path = line.removeprefix("*** Delete File: ")
            operations.append({"type": "delete", "path": path})
            index += 1
        elif line.startswith("*** Update File: "):
            path = line.removeprefix("*** Update File: ")
            index += 1
            hunks: List[List[str]] = []
            while index < len(lines) - 1 and not lines[index].startswith("*** "):
                if lines[index] != "@@":
                    raise ValueError("update hunk must start with @@")
                index += 1
                hunk: List[str] = []
                while index < len(lines) - 1 and not lines[index].startswith("*** ") and lines[index] != "@@":
                    hunk.append(lines[index])
                    index += 1
                hunks.append(hunk)
            operations.append({"type": "update", "path": path, "hunks": hunks})
        else:
            raise ValueError(f"unknown patch operation: {line}")
    return operations


def _apply_hunks(original: Sequence[str], hunks: Sequence[Sequence[str]], path: str) -> List[str]:
    """Apply context hunks exactly; fuzzy patching would be too surprising.

    精确应用上下文 hunk；模糊匹配补丁容易产生意外结果。
    """

    output = list(original)
    search_start = 0
    for hunk in hunks:
        old_segment = [line[1:] for line in hunk if line.startswith((" ", "-"))]
        new_segment = [line[1:] for line in hunk if line.startswith((" ", "+"))]
        position = _find_segment(output, old_segment, search_start)
        if position < 0:
            raise ValueError(f"patch context not found in {path}")
        output[position : position + len(old_segment)] = new_segment
        search_start = position + len(new_segment)
    return output


def _find_segment(lines: Sequence[str], segment: Sequence[str], start: int) -> int:
    if not segment:
        return start
    for index in range(start, len(lines) - len(segment) + 1):
        if list(lines[index : index + len(segment)]) == list(segment):
            return index
    return -1
