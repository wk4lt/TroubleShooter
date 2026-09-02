from pathlib import Path
from typing import Dict, List, Optional

from app.config import settings


def _parse(text: str):
    """解析 SKILL.md:返回 (meta, body)。meta 只提取 name/description 两行。"""
    meta: Dict[str, str] = {}
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            block = text[3:end]
            body = text[end + 4 :].lstrip("\n")
            for line in block.splitlines():
                line = line.strip()
                for key in ("name", "description"):
                    if line.startswith(f"{key}:"):
                        meta[key] = line[len(key) + 1 :].strip().strip('"').strip("'")
    return meta, body


def _load() -> Dict[str, Dict]:
    skills: Dict[str, Dict] = {}
    root = Path(settings.skills_dir)
    if not root.is_dir():
        return skills

    for entry in sorted(root.iterdir()):
        skill_file: Optional[Path] = None
        if entry.is_dir():
            candidate = entry / "SKILL.md"
            if candidate.is_file():
                skill_file = candidate
        elif entry.suffix == ".md":
            skill_file = entry
        if skill_file is None:
            continue

        try:
            text = skill_file.read_text(encoding="utf-8")
        except OSError:
            continue

        meta, body = _parse(text)
        name = meta.get("name")
        if not name:
            name = entry.name if entry.is_dir() else entry.stem
        if not name:
            continue

        skills[name] = {
            "name": name,
            "description": meta.get("description", ""),
            "path": str(skill_file),
            "body": body,
        }

    return skills


_SKILLS: Optional[Dict[str, Dict]] = None


def _get_skills() -> Dict[str, Dict]:
    global _SKILLS
    if _SKILLS is None:
        _SKILLS = _load()
    return _SKILLS


def reload() -> Dict[str, Dict]:
    global _SKILLS
    _SKILLS = _load()
    return _SKILLS


def list_skill_summaries() -> List[Dict[str, str]]:
    return [
        {"name": s["name"], "description": s["description"]}
        for s in _get_skills().values()
    ]


def read_skill(name: str) -> Optional[str]:
    skill = _get_skills().get(name)
    if skill is None:
        return None
    return skill["body"]
