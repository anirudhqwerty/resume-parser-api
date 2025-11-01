# app/routes/candidates.py
"""
Candidate listing and detail endpoints
"""
from fastapi import APIRouter, HTTPException, Path
from typing import List
from app.models.schemas import CandidateSummary, CandidateDetail
from app.services.mongodb_service import MongoDBService
from app.core.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

mongodb_service = MongoDBService()


@router.get("/candidates", response_model=List[CandidateSummary])
async def list_candidates():
    """
    List all candidates with summary details
    
    Returns:
        List of candidate summaries
    """
    try:
        candidates = await mongodb_service.list_candidates()
        
        summaries = []
        for candidate in candidates:
            # Extract name from introduction or use first skill
            name = None
            if candidate.get("introduction"):
                intro = candidate["introduction"]
                if len(intro) > 0:
                    # Try to extract name from first sentence
                    first_sentence = intro.split('.')[0]
                    if "name is" in first_sentence.lower():
                        name = first_sentence.split("name is")[-1].strip()
            
            # Try to estimate years of experience
            experience_years = None
            experience_data = candidate.get("experience", {})
            if isinstance(experience_data, dict) and "total_years" in experience_data:
                experience_years = experience_data["total_years"]
            
            summary = CandidateSummary(
                id=str(candidate["_id"]),
                candidate_id=candidate.get("candidate_id", ""),
                name=name,
                skills=candidate.get("skills", [])[:5],  # Top 5 skills
                experience_years=experience_years,
                created_at=candidate.get("created_at")
            )
            summaries.append(summary)
        
        return summaries
        
    except Exception as e:
        logger.error(f"Error listing candidates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list candidates: {str(e)}")


@router.get("/candidate/{candidate_id}", response_model=CandidateDetail)
async def get_candidate(
    candidate_id: str = Path(..., description="Candidate ID from Supabase")
):
    """
    Get full information for a single candidate
    
    Args:
        candidate_id: The candidate's unique ID
        
    Returns:
        Complete candidate details
    """
    try:
        candidate = await mongodb_service.get_candidate(candidate_id)
        
        if not candidate:
            raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")
        
        return CandidateDetail(
            id=str(candidate["_id"]),
            candidate_id=candidate.get("candidate_id", ""),
            education=candidate.get("education", {}),
            experience=candidate.get("experience", {}),
            skills=candidate.get("skills", []),
            hobbies=candidate.get("hobbies", []),
            certifications=candidate.get("certifications", []),
            projects=candidate.get("projects", []),
            introduction=candidate.get("introduction", ""),
            created_at=candidate.get("created_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting candidate {candidate_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get candidate: {str(e)}")