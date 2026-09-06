import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from app.config import settings
from app.storage.context import current_skill, current_workspace_dir
from app.tools.registry import registry


def _skill_root() -> Path:
    return Path(settings.skills_dir).resolve()


def _resolve_script(skill: str, script: str) -> Path:
    root = _skill_root()
    skill_dir = (root / skill).resolve()
    if skill_dir.parent != root or not skill_dir.is_dir():
        raise ValueError(f"技能不存在或不可执行: {skill}")

    script_path = (skill_dir / script).resolve()
    if skill_dir not in script_path.parents or not script_path.is_file():
        raise ValueError(f"技能脚本不存在或路径非法: {script}")
    return script_path


def _command_for(script_path: Path) -> List[str]:
    if script_path.suffix == ".py":
        return [sys.executable, str(script_path)]
    if script_path.suffix == ".js":
        return ["node", str(script_path)]
    if script_path.suffix == ".sh":
        return ["bash", str(script_path)]
    raise ValueError("当前仅支持 .py、.js、.sh skill 脚本")


@registry.tool(
    name="run_skill_script",
    description=(
        "执行用户选定 Skill 目录中的脚本并返回标准输出。"
        "只能执行该 Skill 目录内的 .py、.js、.sh 文件，不经过 shell；"
        "脚本当前工作目录为 WORKSPACE_DIR，用户文件都在该目录；"
        "执行股票 Skill 时必须优先使用此工具获取真实数据。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "skill": {"type": "string", "description": "当前任务选定的 Skill 名称"},
            "script": {
                "type": "string",
                "description": "Skill 目录内的脚本相对路径，例如 scripts/quote.py",
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "传给脚本的位置参数和选项",
            },
            "timeout": {
                "type": "integer",
                "minimum": 1,
                "maximum": 120,
                "description": "脚本最大执行秒数，默认 60 秒",
            },
        },
        "required": ["skill", "script"],
    },
)
def run_skill_script(
    skill: str,
    script: str,
    args: Optional[List[str]] = None,
    timeout: int = 60,
):
    selected_skill = current_skill.get()
    if selected_skill and skill != selected_skill:
        raise ValueError(f"当前任务只允许执行选定 Skill: {selected_skill}")
    script_path = _resolve_script(skill, script)
    command = _command_for(script_path)
    safe_timeout = max(1, min(int(timeout), 120))
    env = os.environ.copy()
    env["SKILLS_ROOT"] = str(_skill_root())
    workspace_dir = Path(current_workspace_dir.get() or os.getcwd()).resolve()
    workspace_dir.mkdir(parents=True, exist_ok=True)
    env["WORKSPACE_DIR"] = str(workspace_dir)
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        completed = subprocess.run(
            command + [str(arg) for arg in (args or [])],
            cwd=str(workspace_dir),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=safe_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "error": f"脚本执行超时（>{safe_timeout}s）",
            "workspace_dir": str(workspace_dir),
            "stdout": (exc.stdout or "")[-12000:],
            "stderr": (exc.stderr or "")[-4000:],
        }

    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "workspace_dir": str(workspace_dir),
        "stdout": completed.stdout[-16000:],
        "stderr": completed.stderr[-6000:],
    }
