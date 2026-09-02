from app.skills.loader import list_skill_summaries, read_skill as read_skill_body
from app.tools.registry import registry


@registry.tool(
    name="read_skill",
    description=(
        "读取指定技能(Skill)的完整说明文档。"
        "当任务涉及某个可用技能时,先调用此工具获取该技能的详细规范、步骤和模板,再据此执行。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "技能名称,见 system prompt 中的可用技能列表"},
        },
        "required": ["name"],
    },
)
def read_skill(name: str):
    body = read_skill_body(name)
    if body is None:
        available = [s["name"] for s in list_skill_summaries()]
        return {"error": f"技能不存在: {name}", "available": available}
    return {"name": name, "content": body}
