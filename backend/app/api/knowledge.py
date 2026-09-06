from fastapi import APIRouter

from app.rag.service import knowledge_service

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("")
async def list_knowledge():
    return {"documents": knowledge_service.list_documents()}


@router.post("/reindex")
async def reindex_knowledge():
    return knowledge_service.refresh()
