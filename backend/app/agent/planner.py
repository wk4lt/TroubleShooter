from typing import Any, Dict, List, Optional

from app.skills.loader import list_skill_summaries, read_skill
from app.tools.registry import registry

SYSTEM_PROMPT = (
    "你是一个企业级 AI Agent,负责自主执行用户任务。"
    "当任务需要查询、检索或获取数据时,必须直接调用工具获取真实数据,"
    "不要凭空编造结果,不要先输出寒暄或询问用户。"
    "调用工具后,基于工具返回的真实结果进行推理并给出最终结论。"
    "当当前 Skill 需要企业设计文档、SOP、接口规范或历史解决方案来定位问题时,调用 search_knowledge。"
    "search_knowledge 只检索企业内部知识库,不是用户上传文件工具；日志和用户文件仍使用对应文件工具。"
    "检索结果不足时要明确说明知识库没有找到依据,不得把猜测写成事实。"
)


def build_system_prompt(skill: Optional[str] = None, workspace_dir: Optional[str] = None) -> str:
    workspace_note = (
        f"当前任务工作目录是：{workspace_dir or '/backend/data/<session_id>'}。"
        "用户上传或生成的文件都位于该目录及其子目录中。"
        "执行 Skill 脚本时必须使用 WORKSPACE_DIR 访问这些文件，使用 SKILLS_ROOT 访问 Skill 脚本。"
    )
    if skill:
        body = read_skill(skill)
        if body:
            return (
                SYSTEM_PROMPT + "\n" + workspace_note
                + "\n\n"
                + f"用户指定使用技能「{skill}」,必须严格遵循以下说明执行:\n\n"
                + body
            )

    summaries = list_skill_summaries()
    if not summaries:
        return SYSTEM_PROMPT

    lines = [SYSTEM_PROMPT, workspace_note, "", "可用技能(Skill):"]
    for s in summaries:
        desc = s["description"] or "(无描述)"
        lines.append(f"- {s['name']}: {desc}")
    lines.append("当任务涉及上述技能时,先调用 read_skill 工具读取该技能的完整说明再执行。")
    return "\n".join(lines)


def get_tool_specs(skill: Optional[str] = None) -> List[Dict[str, Any]]:
    from app.tools.mcp_gateway import mcp_manager

    mcp_manager.initialize()
    allowed = mcp_manager.allowed_tool_names(skill)
    specs = registry.all_specs(allowed)
    # A selected Skill is already embedded in the system prompt, so asking
    # the model to read it again only creates redundant tool rounds.
    if skill:
        specs = [
            spec for spec in specs
            if spec.get("function", {}).get("name") != "read_skill"
        ]
    return specs
