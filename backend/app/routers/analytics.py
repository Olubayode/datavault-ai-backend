import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.ai_analysis_agent import answer_dataset_question_with_ai


router = APIRouter(prefix="/analytics", tags=["analytics"])


class AskRequest(BaseModel):
    question: str
    dataset_path: Optional[str] = None


def default_dataset_path() -> str:
    configured_path = os.getenv("DEFAULT_DATASET_PATH")
    if configured_path:
        return configured_path

    candidates = [
        Path("sample-data/Chile_real_estate_listings.csv"),
        Path("../sample-data/Chile_real_estate_listings.csv"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return str(candidates[0])


@router.post("/ask")
def ask_dataset(payload: AskRequest):
    """Standalone local test endpoint for Datavault AI analytics."""
    dataset_path = payload.dataset_path or default_dataset_path()

    try:
        return answer_dataset_question_with_ai(
            question=payload.question,
            dataset_path=dataset_path,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_path}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI analytics failed: {exc}")


@router.post("/{project_id}/ask")
def ask_project_dataset(project_id: int, payload: AskRequest):
    """
    Datavault-shaped endpoint.

    Replace this dataset_path lookup with your real project file lookup when the
    full backend repository is present.
    """
    dataset_path = payload.dataset_path or default_dataset_path()

    try:
        result = answer_dataset_question_with_ai(
            question=payload.question,
            dataset_path=dataset_path,
        )
        result["project_id"] = project_id
        return result
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No dataset found for project {project_id}.",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI analytics failed: {exc}")
