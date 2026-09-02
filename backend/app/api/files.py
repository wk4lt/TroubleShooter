from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.logger import log_event
from app.storage.sessions import sessions

router = APIRouter(prefix="/api/files", tags=["files"])


def _resolve_session(x_session_id: str, query_session: str):
    session_id = x_session_id or query_session or "default"
    session = sessions.get_or_create(session_id)
    return session


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    relpath: str = Form(default=""),
    x_session_id: str = Header(default=""),
):
    session = _resolve_session(x_session_id, "")
    content = await file.read()
    try:
        meta = session.files.save_upload(
            file.filename or "unnamed", content, relpath or None
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    log_event(
        f"上传文件 {meta['relpath']} ({meta['size']}B)",
        level="info",
        source="files",
        session_id=session.session_id,
    )
    return {
        "file_id": meta["file_id"],
        "filename": meta["filename"],
        "relpath": meta["relpath"],
        "size": meta["size"],
    }


@router.get("")
async def list_files(x_session_id: str = Header(default="")):
    session = _resolve_session(x_session_id, "")
    return {"files": session.files.list()}


@router.get("/{file_id}")
async def download_file(
    file_id: str,
    x_session_id: str = Header(default=""),
    session: str = Query(default=""),
):
    s = _resolve_session(x_session_id, session)
    meta = s.files.get(file_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(meta["path"], filename=meta["filename"])


@router.delete("/{file_id}")
async def delete_file(file_id: str, x_session_id: str = Header(default="")):
    session = _resolve_session(x_session_id, "")
    if session.files.get(file_id) is None:
        raise HTTPException(status_code=404, detail="file not found")
    session.files.delete(file_id)
    return {"ok": True}
