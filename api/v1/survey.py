from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db, SurveyFeedback
from schemas import SurveyInput, SurveyOutput

router = APIRouter()

@router.post("/survey")
def submit_survey(survey: SurveyInput, db: Session = Depends(get_db)):
    new_survey = SurveyFeedback(
        rating=survey.rating,
        ease_of_use=survey.ease_of_use,
        accuracy=survey.accuracy,
        comments=survey.comments
    )
    db.add(new_survey)
    db.commit()
    return {"message": "Survey berhasil disimpan"}

@router.get("/survey", response_model=List[SurveyOutput])
def get_survey_feedback(db: Session = Depends(get_db)):
    """
    Mengambil semua data ulasan/survey dari database
    """
    surveys = db.query(SurveyFeedback).order_by(SurveyFeedback.created_at.desc()).all()
    return surveys
