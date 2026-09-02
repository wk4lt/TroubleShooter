from fastapi import APIRouter

from app.skills.loader import list_skill_summaries

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
async def get_skills():
    return {"skills": list_skill_summaries()}
