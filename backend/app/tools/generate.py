from datetime import datetime

from app.storage.context import current_session_id
from app.storage.sessions import sessions
from app.tools.registry import registry


def _store():
    session_id = current_session_id.get() or "default"
    return sessions.get_or_create(session_id).files


@registry.tool(
    name="generate_file",
    description=(
        "在当前工作区生成一个文件并返回下载信息。"
        "根据 file_type 生成不同格式:markdown 会自动加上标题与生成时间,"
        "json/csv/text 按原内容写入。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "生成的文件名,需带扩展名,如 report.md、data.json、result.csv",
            },
            "file_type": {
                "type": "string",
                "enum": ["markdown", "json", "csv", "text"],
                "description": "文件类型",
            },
            "content": {"type": "string", "description": "文件正文内容"},
        },
        "required": ["filename", "content"],
    },
)
def generate_file(filename: str, content: str, file_type: str = "text"):
    generated_at = datetime.now().isoformat()

    if file_type == "markdown":
        body = f"# {filename}\n\n> 生成时间: {generated_at}\n\n{content}\n"
    elif file_type == "json":
        body = content
    elif file_type == "csv":
        body = content
    else:
        body = f"{content}\n\n--- 由 AI Agent 生成于 {generated_at} ---\n"

    meta = _store().save_text(filename, body)
    return {
        "file_id": meta["file_id"],
        "filename": meta["filename"],
        "size": meta["size"],
        "generated_at": generated_at,
    }
