from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db, PatientHistory
from schemas import PatientHistoryOutput

router = APIRouter()

@router.get("/history", response_model=List[PatientHistoryOutput])
def get_patient_history(db: Session = Depends(get_db)):
    """
    Mengambil riwayat diagnosa pasien dari database
    """
    histories = db.query(PatientHistory).order_by(PatientHistory.created_at.desc()).all()
    return histories
