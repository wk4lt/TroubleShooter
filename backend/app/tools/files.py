from pathlib import Path

from app.config import settings
from app.storage.context import current_session_id
from app.storage.sessions import sessions
from app.tools.registry import registry


def _store():
    session_id = current_session_id.get() or "default"
    return sessions.get_or_create(session_id).files


@registry.tool(
    name="list_files",
    description="列出当前工作区中的所有文件。工作区是 WORKSPACE_DIR，返回每个文件的 file_id、文件名、相对路径和大小。",
    parameters={"type": "object", "properties": {}},
)
def list_files():
    return {"files": _store().list()}


@registry.tool(
    name="read_file",
    description=(
        "读取 WORKSPACE_DIR 中指定文本文件的受控窗口。默认最多读取 200 行和 12000 字符；"
        "大文件不会一次性塞入上下文，可用 start_line/max_lines/max_chars 分段读取。"
        "filename 可以是文件名或相对路径(如 subdir/a.txt)。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "要读取的文件名或相对路径"},
            "start_line": {
                "type": "integer", "minimum": 1,
                "description": "开始读取的行号，默认 1",
            },
            "max_lines": {
                "type": "integer", "minimum": 1, "maximum": 500,
                "description": "最多读取行数，默认 200",
            },
            "max_chars": {
                "type": "integer", "minimum": 200, "maximum": 20000,
                "description": "最多读取字符数，默认 12000",
            },
        },
        "required": ["filename"],
    },
)
def read_file(
    filename: str,
    start_line: int = 1,
    max_lines: int = 200,
    max_chars: int = 12000,
):
    store = _store()
    meta = store.find_by_name(filename) or store.find_by_relpath(filename)
    if meta is None:
        return {"error": f"文件不存在: {filename}"}
    path = Path(meta["path"])
    size_bytes = path.stat().st_size
    if size_bytes > settings.tool_max_file_read_bytes:
        return {
            "error": f"文件过大，未读取：{filename}",
            "size_bytes": size_bytes,
            "max_supported_bytes": settings.tool_max_file_read_bytes,
            "strategy": "请使用 Skill 脚本按时间、关键词或日志级别过滤后再读取结果",
        }
    start_line = max(1, int(start_line))
    max_lines = max(1, min(int(max_lines), settings.tool_max_file_read_lines, 500))
    max_chars = max(200, min(int(max_chars), 20000, settings.tool_max_file_read_chars))
    content_lines = []
    chars = 0
    end_line = start_line - 1
    truncated = False
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if line_number < start_line:
                    continue
                if len(content_lines) >= max_lines:
                    truncated = True
                    break
                remaining = max_chars - chars
                if remaining <= 0:
                    truncated = True
                    break
                if len(line) > remaining:
                    content_lines.append(line[:remaining])
                    end_line = line_number
                    truncated = True
                    break
                content_lines.append(line)
                chars += len(line)
                end_line = line_number
    except UnicodeDecodeError:
        return {"error": f"文件 {filename} 不是文本文件,无法读取内容"}
    result = {
        "filename": meta["relpath"],
        "content": "".join(content_lines),
        "size_bytes": size_bytes,
        "start_line": start_line,
        "end_line": end_line,
        "truncated": truncated,
    }
    if truncated:
        result["next_start_line"] = end_line + 1
        result["strategy"] = "继续调用 read_file 并将 next_start_line 作为 start_line 传入，或先用 Skill 脚本过滤日志"
    return result


@registry.tool(
    name="write_file",
    description="在 WORKSPACE_DIR 中写入一个新文本文件。",
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
    if len(content) > settings.tool_max_write_chars:
        return {
            "error": f"写入内容过大：{len(content)} 字符",
            "max_chars": settings.tool_max_write_chars,
            "strategy": "请拆分为多个文件，或先压缩内容",
        }
    meta = _store().save_text(filename, content)
    return {"file_id": meta["file_id"], "filename": filename, "size": meta["size"]}
