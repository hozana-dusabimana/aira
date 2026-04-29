from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.ai.description_generator import generate_description
from app.ai.image_analyzer import get_analyzer
from app.core.permissions import get_current_user
from app.database import get_db
from app.models.ai_analysis import AIAnalysis
from app.models.user import User
from app.schemas.incident import AIAnalysisOut

router = APIRouter()


@router.post("/analyze-image")
def analyze_image(
    image: UploadFile = File(...),
    _: User = Depends(get_current_user),
) -> dict:
    """Standalone AI analysis (does NOT create an incident record)."""
    contents = image.file.read()
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    analyzer = get_analyzer()
    result = analyzer.analyze(contents)
    return {
        "caption": result.caption,
        "scene_label": result.scene_label,
        "detected_objects": result.detected_objects,
        "confidence_score": result.confidence_score,
        "incident_type": result.incident_type,
        "severity_level": result.severity_level,
        "model_version": result.model_version,
        "description": generate_description(result),
    }


@router.get("/analysis/{incident_id}", response_model=AIAnalysisOut)
def get_analysis(
    incident_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: User = Depends(get_current_user),
) -> AIAnalysis:
    analysis = db.query(AIAnalysis).filter(AIAnalysis.incident_id == incident_id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis
