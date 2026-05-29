from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.routers.auth import current_user
from app.routers.projects import owned_project
from app.services.store import connect, save_uploaded_file


router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{project_id}")
def list_files(project_id: str, user=Depends(current_user)):
    owned_project(project_id, user["id"])
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, project_id, file_name, file_type, file_size, purpose, uploaded_at FROM files WHERE project_id = ? ORDER BY uploaded_at DESC",
            (project_id,),
        ).fetchall()
    return [dict(row) for row in rows]


async def upload_file(project_id: str, file: UploadFile, purpose: str, user):
    owned_project(project_id, user["id"])
    content = await file.read()
    try:
        return save_uploaded_file(
            project_id=project_id,
            file_name=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
            purpose=purpose,
            content=content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{project_id}/dataset")
async def upload_dataset(project_id: str, file: UploadFile = File(...), user=Depends(current_user)):
    return await upload_file(project_id, file, "dataset", user)


@router.post("/{project_id}/prototype-pdf")
async def upload_prototype_pdf(project_id: str, file: UploadFile = File(...), user=Depends(current_user)):
    return await upload_file(project_id, file, "prototype_pdf", user)
