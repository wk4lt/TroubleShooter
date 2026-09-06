from typing import Optional

from app.rag.service import knowledge_service
from app.storage.context import current_skill
from app.tools.registry import registry


@registry.tool(
    name="search_knowledge",
    description=(
        "在 Skill 执行过程中检索企业内部知识库，适用于设计文档、问题解决 SOP、接口说明和故障排查。"
        "这不是用户临时文件检索工具，不要要求用户上传文件来使用它；用户文件请使用 read_file。"
        "优先传入 subsystem_id 和 knowledge_type 缩小范围；回答时必须引用返回的 source 和 chunk_id。"
        "知识库目录约定为 backend/data/knowledge/<subsystem_id>/<knowledge_type>/文件。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "要检索的问题或关键词"},
            "subsystem_id": {"type": "string", "description": "子系统标识，例如 order-system"},
            "knowledge_type": {
                "type": "string",
                "description": "知识类型，例如 design、sop、faq",
            },
            "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
        },
        "required": ["query"],
    },
)
def search_knowledge(
    query: str,
    subsystem_id: Optional[str] = None,
    knowledge_type: Optional[str] = None,
    top_k: int = 5,
):
    selected_skill = current_skill.get()
    if not selected_skill:
        return {
            "error": "search_knowledge 只能在已选定 Skill 的执行过程中调用",
            "hint": "请先选择对应 Skill，再由 Skill 流程调用企业知识检索",
        }
    return knowledge_service.search(
        query=query,
        top_k=top_k,
        subsystem_id=subsystem_id,
        knowledge_type=knowledge_type,
    )
