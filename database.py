import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./hospitalai.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DocumentMetadata(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PatientHistory(Base):
    __tablename__ = "patient_histories"
    id = Column(Integer, primary_key=True, index=True)
    gender = Column(String)
    age = Column(Integer)
    symptoms = Column(String)
    recommended_department = Column(String)
    possibility_of_illness = Column(String)
    initial_handling = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class SurveyFeedback(Base):
    __tablename__ = "survey_feedbacks"
    id = Column(Integer, primary_key=True, index=True)
    rating = Column(Integer)
    ease_of_use = Column(String)
    accuracy = Column(String)
    comments = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
