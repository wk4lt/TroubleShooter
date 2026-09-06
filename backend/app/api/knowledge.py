from fastapi import APIRouter, File, Form, HTTPException, UploadFile
import re

from app.rag.service import knowledge_service

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])
SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def _safe_component(value: str, label: str) -> str:
    value = value.strip()
    if not SAFE_COMPONENT.fullmatch(value):
        raise HTTPException(status_code=400, detail=f"{label} 只能包含字母、数字、下划线和短横线")
    return value


@router.get("")
async def list_knowledge():
    return {"documents": knowledge_service.list_documents()}


@router.post("/reindex")
async def reindex_knowledge():
    return knowledge_service.refresh()


@router.post("/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    subsystem_id: str = Form(...),
    knowledge_type: str = Form(...),
):
    safe_subsystem = _safe_component(subsystem_id, "子系统")
    safe_type = _safe_component(knowledge_type, "知识类型")
    filename = (file.filename or "").replace("/", "_").replace("\\", "_").strip()
    if not filename or filename in {".", ".."}:
        raise HTTPException(status_code=400, detail="文件名不能为空或非法")
    target = (knowledge_service.root / safe_subsystem / safe_type / filename).resolve()
    if knowledge_service.root not in target.parents:
        raise HTTPException(status_code=400, detail="文件路径非法")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(await file.read())
    knowledge_service.refresh()
    return {
        "source": f"{safe_subsystem}/{safe_type}/{filename}",
        "documents": knowledge_service.list_documents(),
    }
