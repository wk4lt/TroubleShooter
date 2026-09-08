from fastapi import APIRouter

from pathlib import Path

from app.config import settings
from app.context.openviking_adapter import openviking_adapter

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("")
async def list_knowledge():
    root = Path(settings.rag_knowledge_dir)
    return {
        "source_directory": str(root),
        "configured": root.exists(),
        "resource_uri": settings.openviking_resource_uri,
    }


@router.post("/reindex")
async def reindex_knowledge():
    root = Path(settings.rag_knowledge_dir)
    if not root.is_dir():
        return {"error": f"知识目录不存在: {root}"}
    return await openviking_adapter.import_resource(root)
