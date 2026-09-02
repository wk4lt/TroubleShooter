from typing import Any, Dict, List, Optional

from app.skills.loader import list_skill_summaries, read_skill
from app.tools.registry import registry

SYSTEM_PROMPT = (
    "你是一个企业级 AI Agent,负责自主执行用户任务。"
    "当任务需要查询、检索或获取数据时,必须直接调用工具获取真实数据,"
    "不要凭空编造结果,不要先输出寒暄或询问用户。"
    "调用工具后,基于工具返回的真实结果进行推理并给出最终结论。"
)


def build_system_prompt(skill: Optional[str] = None) -> str:
    if skill:
        body = read_skill(skill)
        if body:
            return (
                SYSTEM_PROMPT
                + "\n\n"
                + f"用户指定使用技能「{skill}」,必须严格遵循以下说明执行:\n\n"
                + body
            )

    summaries = list_skill_summaries()
    if not summaries:
        return SYSTEM_PROMPT

    lines = [SYSTEM_PROMPT, "", "可用技能(Skill):"]
    for s in summaries:
        desc = s["description"] or "(无描述)"
        lines.append(f"- {s['name']}: {desc}")
    lines.append("当任务涉及上述技能时,先调用 read_skill 工具读取该技能的完整说明再执行。")
    return "\n".join(lines)


def get_tool_specs() -> List[Dict[str, Any]]:
    return registry.all_specs()
