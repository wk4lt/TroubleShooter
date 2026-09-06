import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional

DATA_ROOT = Path(__file__).resolve().parent.parent.parent / "data"
SAFE_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class FileStore:
    """Per-session file storage, isolated by directory."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        # Frontend session IDs are UUIDs. Keep valid IDs readable on disk, but
        # never allow a user-controlled header to escape DATA_ROOT.
        storage_id = session_id if SAFE_SESSION_ID.fullmatch(session_id) else uuid.uuid5(
            uuid.NAMESPACE_URL, session_id
        ).hex
        self.base_dir = DATA_ROOT / storage_id
        self._files: Dict[str, Dict] = {}

    def _ensure_dir(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sanitize_relpath(relpath: str) -> str:
        relpath = relpath.replace("\\", "/").strip("/")
        parts = [p for p in relpath.split("/") if p not in ("", ".")]
        if any(p == ".." for p in parts):
            raise ValueError(f"非法路径: {relpath}")
        if not parts:
            raise ValueError("非法路径: 空路径")
        return "/".join(parts)

    @staticmethod
    def _sanitize_dirpath(path: str) -> str:
        path = path.replace("\\", "/").strip("/")
        parts = [part for part in path.split("/") if part not in ("", ".")]
        if any(part == ".." for part in parts):
            raise ValueError(f"非法目录路径: {path}")
        return "/".join(parts)

    def save_upload(
        self, filename: str, content: bytes, relpath: Optional[str] = None
    ) -> Dict:
        self._ensure_dir()
        relpath = self._sanitize_relpath(relpath or filename)
        file_id = uuid.uuid4().hex[:12]
        base_dir = self.base_dir.resolve()
        path = (base_dir / relpath).resolve()
        if base_dir not in path.parents:
            raise ValueError(f"非法路径: {relpath}")
        path.parent.mkdir(parents=True, exist_ok=True)
        for old_id, old_meta in list(self._files.items()):
            if old_meta["relpath"] == relpath:
                self._files.pop(old_id, None)
                try:
                    Path(old_meta["path"]).unlink()
                except OSError:
                    pass
        path.write_bytes(content)
        meta = {
            "file_id": file_id,
            "filename": os.path.basename(relpath),
            "relpath": relpath,
            "size": len(content),
            "path": str(path),
        }
        self._files[file_id] = meta
        return meta

    def save_text(self, filename: str, content: str) -> Dict:
        return self.save_upload(filename, content.encode("utf-8"), relpath=filename)

    def get(self, file_id: str) -> Optional[Dict]:
        return self._files.get(file_id)

    def find_by_name(self, filename: str) -> Optional[Dict]:
        for meta in reversed(list(self._files.values())):
            if meta["filename"] == filename:
                return meta
        return None

    def find_by_relpath(self, relpath: str) -> Optional[Dict]:
        relpath = relpath.replace("\\", "/").strip("/")
        for meta in reversed(list(self._files.values())):
            if meta["relpath"] == relpath:
                return meta
        return None

    def list(self) -> List[Dict]:
        return [
            {
                "file_id": m["file_id"],
                "filename": m["filename"],
                "relpath": m["relpath"],
                "size": m["size"],
            }
            for m in self._files.values()
        ]

    def list_directory(self, path: str = "") -> Dict:
        """Return immediate child directories and files below a logical path."""
        current = self._sanitize_dirpath(path)
        prefix = f"{current}/" if current else ""
        directories = set()
        files = []

        for meta in self._files.values():
            relpath = meta["relpath"]
            if not relpath.startswith(prefix):
                continue
            remainder = relpath[len(prefix) :]
            if "/" in remainder:
                directories.add(remainder.split("/", 1)[0])
            else:
                files.append(
                    {
                        "file_id": meta["file_id"],
                        "filename": meta["filename"],
                        "relpath": relpath,
                        "size": meta["size"],
                    }
                )

        return {
            "path": current,
            "directories": [
                {"name": name, "path": f"{prefix}{name}".strip("/")}
                for name in sorted(directories)
            ],
            "files": sorted(files, key=lambda item: item["filename"].lower()),
        }

    def delete(self, file_id: str) -> None:
        meta = self._files.pop(file_id, None)
        if meta is not None:
            try:
                os.remove(meta["path"])
            except OSError:
                pass

    def clear(self) -> None:
        self._files.clear()
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir, ignore_errors=True)
