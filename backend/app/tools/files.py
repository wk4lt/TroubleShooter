from pathlib import Path

from app.storage.context import current_session_id
from app.storage.sessions import sessions
from app.tools.registry import registry


def _store():
    session_id = current_session_id.get() or "default"
    return sessions.get_or_create(session_id).files


@registry.tool(
    name="list_files",
    description="列出当前工作区中的所有文件,返回每个文件的 file_id、文件名、相对路径和大小。",
    parameters={"type": "object", "properties": {}},
)
def list_files():
    return {"files": _store().list()}


@registry.tool(
    name="read_file",
    description="读取当前工作区中指定文件的内容。仅支持文本文件。filename 可以是文件名或相对路径(如 subdir/a.txt)。",
    parameters={
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "要读取的文件名或相对路径"},
        },
        "required": ["filename"],
    },
)
def read_file(filename: str):
    store = _store()
    meta = store.find_by_name(filename) or store.find_by_relpath(filename)
    if meta is None:
        return {"error": f"文件不存在: {filename}"}
    try:
        text = Path(meta["path"]).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"error": f"文件 {filename} 不是文本文件,无法读取内容"}
    return {"filename": meta["relpath"], "content": text}


@registry.tool(
    name="write_file",
    description="在当前工作区写入一个新文本文件。",
    parameters={
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "要写入的文件名,如 report.md"},
            "content": {"type": "string", "description": "文件内容"},
        },
        "required": ["filename", "content"],
    },
)
def write_file(filename: str, content: str):
    meta = _store().save_text(filename, content)
    return {"file_id": meta["file_id"], "filename": filename, "size": meta["size"]}
