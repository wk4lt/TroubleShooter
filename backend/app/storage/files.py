import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional

DATA_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "files"


class FileStore:
    """Per-session file storage, isolated by directory."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.base_dir = DATA_ROOT / session_id
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

    def save_upload(
        self, filename: str, content: bytes, relpath: Optional[str] = None
    ) -> Dict:
        self._ensure_dir()
        relpath = self._sanitize_relpath(relpath or filename)
        file_id = uuid.uuid4().hex[:12]
        path = self.base_dir / file_id
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
