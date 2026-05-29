import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.routers.auth import current_user
from app.services.store import connect, ensure_default_project, iso_now, row_to_dict


router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectRequest(BaseModel):
    title: str
    description: str | None = None


def owned_project(project_id: str, user_id: str):
    with connect() as conn:
        project = row_to_dict(
            conn.execute("SELECT * FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id)).fetchone()
        )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("")
def list_projects(user=Depends(current_user)):
    ensure_default_project(user["id"])
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM projects WHERE user_id = ? ORDER BY created_at DESC",
            (user["id"],),
        ).fetchall()
    return [dict(row) for row in rows]


@router.post("")
def create_project(payload: ProjectRequest, user=Depends(current_user)):
    project_id = str(uuid.uuid4())
    project = {
        "id": project_id,
        "user_id": user["id"],
        "title": payload.title,
        "description": payload.description,
        "created_at": iso_now(),
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO projects (id, user_id, title, description, created_at)
            VALUES (:id, :user_id, :title, :description, :created_at)
            """,
            project,
        )
    return project
