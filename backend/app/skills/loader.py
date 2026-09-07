from pathlib import Path
from typing import Dict, List, Optional

from app.config import settings


def _parse(text: str):
    """解析 SKILL.md，支持普通值和 YAML 折叠多行 description。"""
    meta: Dict[str, str] = {}
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            block = text[3:end]
            body = text[end + 4 :].lstrip("\n")
            lines = block.splitlines()
            index = 0
            while index < len(lines):
                line = lines[index]
                stripped = line.strip()
                matched_key = next(
                    (key for key in ("name", "description") if stripped.startswith(f"{key}:")),
                    None,
                )
                if matched_key is None:
                    index += 1
                    continue

                value = stripped[len(matched_key) + 1 :].strip()
                if value in (">", ">-", "|", "|-"):
                    parts = []
                    index += 1
                    while index < len(lines):
                        continuation = lines[index]
                        if continuation and not continuation[0].isspace():
                            break
                        parts.append(continuation.strip())
                        index += 1
                    separator = " " if value.startswith(">") else "\n"
                    value = separator.join(part for part in parts if part).strip()
                    meta[matched_key] = value
                    continue

                meta[matched_key] = value.strip('"').strip("'")
                index += 1
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
