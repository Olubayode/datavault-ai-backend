import json
from pathlib import Path
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException
import pandas as pd
from pydantic import BaseModel

from app.routers.auth import current_user
from app.routers.projects import owned_project
from app.services.ai_analysis_agent import answer_dataset_question_with_ai
from app.services.store import connect, iso_now


router = APIRouter(prefix="/workspace-analytics", tags=["workspace analytics"])


class ProjectQuestion(BaseModel):
    project_id: str
    question: str


def latest_dataset_path(project_id: str) -> str:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT file_path FROM files
            WHERE project_id = ? AND purpose = 'dataset'
            ORDER BY uploaded_at DESC
            LIMIT 1
            """,
            (project_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="Upload a CSV or Excel dataset first")
    return row["file_path"]


def load_dataframe(path: str) -> pd.DataFrame:
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError("Unsupported dataset format")


def summarize_dataframe(path: str) -> dict[str, Any]:
    df = load_dataframe(path)
    numeric = df.select_dtypes(include="number")
    missing = df.isna().sum().sort_values(ascending=False)

    summary: dict[str, Any] = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": list(df.columns),
        "missing_values": {str(k): int(v) for k, v in missing.head(12).items() if int(v) > 0},
        "kpis": [],
        "chart_data": [],
        "recommendations": [],
    }

    if not numeric.empty:
        means = numeric.mean(numeric_only=True).sort_values(ascending=False).head(4)
        summary["kpis"] = [{"label": str(name), "value": round(float(value), 2)} for name, value in means.items()]

        first_numeric = numeric.columns[0]
        summary["chart_data"] = [
            {"name": str(index), "value": round(float(value), 2)}
            for index, value in numeric[first_numeric].head(12).items()
        ]

    if summary["missing_values"]:
        summary["recommendations"].append("Review missing-value hotspots before modeling or reporting.")
    if not summary["recommendations"]:
        summary["recommendations"].append("Dataset is ready for exploratory AI analysis.")

    return summary


@router.get("/{project_id}/summary")
def summarize_uploaded_dataset(project_id: str, user=Depends(current_user)):
    owned_project(project_id, user["id"])
    return summarize_dataframe(latest_dataset_path(project_id))


@router.post("/ask")
def ask_uploaded_dataset(payload: ProjectQuestion, user=Depends(current_user)):
    owned_project(payload.project_id, user["id"])
    dataset_path = latest_dataset_path(payload.project_id)
    result = answer_dataset_question_with_ai(question=payload.question, dataset_path=dataset_path)

    chat = {
        "id": str(uuid.uuid4()),
        "project_id": payload.project_id,
        "user_message": payload.question,
        "ai_response": json.dumps(result),
        "created_at": iso_now(),
    }

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO chats (id, project_id, user_message, ai_response, created_at)
            VALUES (:id, :project_id, :user_message, :ai_response, :created_at)
            """,
            chat,
        )

    return chat


@router.get("/{project_id}/chats")
def list_chats(project_id: str, user=Depends(current_user)):
    owned_project(project_id, user["id"])
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM chats WHERE project_id = ? ORDER BY created_at ASC",
            (project_id,),
        ).fetchall()
    return [dict(row) for row in rows]
