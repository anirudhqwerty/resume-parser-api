# app/routes/qa.py
"""
Q&A endpoint for natural language questions about candidates
"""
from fastapi import APIRouter, HTTPException, Path, Depends, status
from app.models.schemas import QuestionRequest, QuestionResponse
from app.services.mongodb_service import MongoDBService
from app.services.huggingface_service import HuggingFaceService
from app.core.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


def get_mongodb_service() -> MongoDBService:
    """Dependency for MongoDB service"""
    return MongoDBService()


def get_hf_service() -> HuggingFaceService:
    """Dependency for HuggingFace service"""
    return HuggingFaceService()


@router.post(
    "/ask/{candidate_id}",
    response_model=QuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question about a candidate",
    responses={
        404: {"description": "Candidate not found"},
        400: {"description": "Invalid question format"},
        500: {"description": "Internal server error"},
        503: {"description": "LLM service unavailable"}
    }
)
async def ask_question(
    request: QuestionRequest,
    candidate_id: str = Path(
        ...,
        description="Candidate ID to ask about",
        min_length=1,
        max_length=100,
        pattern="^[a-zA-Z0-9_-]+$"
    ),
    mongodb_service: MongoDBService = Depends(get_mongodb_service),
    hf_service: HuggingFaceService = Depends(get_hf_service)
) -> QuestionResponse:
    """
    Ask a natural language question about a specific candidate.
    
    This endpoint retrieves candidate data from MongoDB and uses an LLM
    to generate contextual answers based on the candidate's information.
    
    Args:
        request: Question request containing the natural language question
        candidate_id: The candidate's unique identifier
        mongodb_service: MongoDB service instance (injected)
        hf_service: HuggingFace service instance (injected)
        
    Returns:
        QuestionResponse: Generated answer with metadata
        
    Raises:
        HTTPException: 
            - 404 if candidate not found
            - 400 if question is invalid
            - 503 if LLM service is unavailable
            - 500 for other server errors
    """
    try:
        # Validate question
        if not request.question or not request.question.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question cannot be empty"
            )
        
        logger.info(f"Processing question for candidate {candidate_id}: {request.question[:100]}...")
        
        # Retrieve candidate data
        candidate = await mongodb_service.get_candidate(candidate_id)
        
        if not candidate:
            logger.warning(f"Candidate {candidate_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID '{candidate_id}' not found"
            )
        
        # Very minimal validation - just check if we have ANY data
        if not _has_minimal_data(candidate):
            logger.warning(f"Candidate {candidate_id} has no usable data")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Candidate profile has no available information."
            )
        
        # Generate answer using LLM
        try:
            answer = await hf_service.answer_question(
                question=request.question.strip(),
                candidate_data=candidate
            )
        except ConnectionError as e:
            logger.error(f"LLM service connection error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Language model service is currently unavailable. Please try again later."
            )
        except ValueError as e:
            logger.error(f"Invalid input for LLM: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid question format: {str(e)}"
            )
        
        logger.info(f"Successfully answered question for candidate {candidate_id}")
        
        return QuestionResponse(
            question=request.question.strip(),
            answer=answer,
            candidate_id=candidate_id
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        # Log unexpected errors with full context
        logger.exception(
            f"Unexpected error answering question for candidate {candidate_id}",
            extra={
                "candidate_id": candidate_id,
                "question": request.question[:100] if request.question else None,
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your question"
        )


def _has_minimal_data(candidate: dict) -> bool:
    """
    Check if candidate has ANY usable data for Q&A.
    Very permissive - accepts name, skills, hobbies, or any basic info.
    
    Args:
        candidate: Candidate data dictionary
        
    Returns:
        bool: True if candidate has at least some data
    """
    # List of all possible fields that contain useful information
    useful_fields = [
        "name", "introduction", "full_name",  # Identity
        "skills", "hobbies",  # Lists
        "experience", "education", "projects",  # Structured data
        "summary", "bio", "description"  # Text descriptions
    ]
    
    # Check if ANY field exists and has content
    for field in useful_fields:
        value = candidate.get(field)
        if value:
            # String check
            if isinstance(value, str) and value.strip():
                return True
            # List or dict check (non-empty)
            if isinstance(value, (list, dict)) and value:
                return True
    
    return False