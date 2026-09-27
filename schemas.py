from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class SourceInfo(BaseModel):
    document_name: str
    document_url: Optional[str] = None

class PatientInput(BaseModel):
    gender: str
    age: int
    symptoms: List[str]

class RecommendationOutput(BaseModel):
    recommended_department: list[str]
    possibility_of_illness: list[str]
    initial_handling: list[str]
    sources: List[SourceInfo] = []

class DocumentUpdate(BaseModel):
    name: str
    url: Optional[str] = None

class SurveyInput(BaseModel):
    rating: int
    ease_of_use: str
    accuracy: str
    comments: Optional[str] = None

class SurveyOutput(BaseModel):
    id: int
    rating: int
    ease_of_use: str
    accuracy: str
    comments: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PatientHistoryOutput(BaseModel):
    id: int
    gender: str
    age: int
    symptoms: str
    recommended_department: str
    possibility_of_illness: str
    initial_handling: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class DocumentOutput(BaseModel):
    id: int
    name: str
    url: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
