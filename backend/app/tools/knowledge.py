from typing import Optional

from app.context.openviking_adapter import OpenVikingAdapter
from app.storage.context import current_skill
from app.tools.registry import registry


@registry.tool(
    name="search_knowledge",
    description=(
        "在 Skill 执行过程中检索企业内部知识库，适用于设计文档、问题解决 SOP、接口说明和故障排查。"
        "这不是用户临时文件检索工具，不要要求用户上传文件来使用它；用户文件请使用 read_file。"
            "检索由官方 OpenViking 服务执行；回答时必须引用返回的 URI。"
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
async def search_knowledge(
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
    # These optional business filters are not mapped to an OpenViking query yet.
    _ = subsystem_id, knowledge_type
    # Tool calls execute in a worker-owned event loop.  Give that loop its own
    # official client and close it before returning, avoiding cross-loop reuse.
    adapter = OpenVikingAdapter()
    try:
        return await adapter.find(query=query, limit=top_k)
    finally:
        await adapter.close()
