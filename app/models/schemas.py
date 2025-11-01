# app/models/schemas.py
"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class UploadResponse(BaseModel):
    """Response model for file upload"""
    message: str
    file_id: str
    candidate_id: str
    filename: str
    upload_time: datetime


class Education(BaseModel):
    """Education information schema"""
    degree: Optional[str] = None
    institution: Optional[str] = None
    year: Optional[str] = None
    field: Optional[str] = None


class Experience(BaseModel):
    """Work experience schema"""
    company: Optional[str] = None
    position: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None


class CandidateCreate(BaseModel):
    """Schema for creating a new candidate"""
    candidate_id: str
    education: Dict[str, Any] = Field(default_factory=dict)
    experience: Dict[str, Any] = Field(default_factory=dict)
    skills: List[str] = Field(default_factory=list)
    hobbies: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    introduction: str = ""


class CandidateSummary(BaseModel):
    """Summary view of candidate"""
    id: str
    candidate_id: str
    name: Optional[str] = None
    skills: List[str]
    experience_years: Optional[str] = None
    created_at: Optional[datetime] = None


class CandidateDetail(BaseModel):
    """Full candidate information"""
    id: str
    candidate_id: str
    education: Dict[str, Any]
    experience: Dict[str, Any]
    skills: List[str]
    hobbies: List[str]
    certifications: List[str]
    projects: List[str]
    introduction: str
    created_at: Optional[datetime] = None


class QuestionRequest(BaseModel):
    """Request model for Q&A endpoint"""
    question: str = Field(..., min_length=1, description="Natural language question about the candidate")


class QuestionResponse(BaseModel):
    """Response model for Q&A endpoint"""
    question: str
    answer: str
    candidate_id: str