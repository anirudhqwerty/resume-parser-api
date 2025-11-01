# app/routes/upload.py
"""
Upload endpoint for resume files
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from app.models.schemas import UploadResponse
from app.services.file_service import FileService
from app.services.supabase_service import SupabaseService
from app.services.mongodb_service import MongoDBService
from app.services.resume_parser import ResumeParser
from app.core.logger import get_logger
from datetime import datetime
import os

router = APIRouter()
logger = get_logger(__name__)

file_service = FileService()
supabase_service = SupabaseService()
mongodb_service = MongoDBService()
resume_parser = ResumeParser()


async def process_resume_background(file_path: str, metadata_id: str, filename: str):
    """
    Background task to process resume and store in MongoDB
    
    Args:
        file_path: Path to the uploaded file
        metadata_id: ID from Supabase metadata
        filename: Original filename
    """
    try:
        logger.info(f"Starting background processing for {filename}")
        
        # Extract text from resume
        text = await file_service.extract_text(file_path)
        
        # Parse resume using ML model
        parsed_data = await resume_parser.parse_resume(text)
        
        # Add candidate_id from Supabase
        parsed_data["candidate_id"] = metadata_id
        
        # Store in MongoDB
        await mongodb_service.create_candidate(parsed_data)
        
        logger.info(f"Successfully processed and stored candidate {metadata_id}")
        
        # Clean up local file
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        logger.error(f"Error in background processing: {str(e)}")


@router.post("/upload", response_model=UploadResponse)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a resume file (.pdf or .docx)
    
    Args:
        file: Resume file to upload
        
    Returns:
        UploadResponse with file metadata and candidate ID
    """
    try:
        # Validate file
        file_service.validate_file(file)
        
        # Save file locally temporarily
        file_path = await file_service.save_file(file)
        
        # Upload to Supabase storage
        storage_path = await supabase_service.upload_file(file, file_path)
        
        # Save metadata to Supabase
        upload_time = datetime.utcnow()
        metadata = {
            "filename": file.filename,
            "storage_path": storage_path,
            "upload_time": upload_time.isoformat(),
            "file_size": os.path.getsize(file_path),
            "content_type": file.content_type
        }
        
        metadata_id = await supabase_service.save_metadata(metadata)
        
        # Process resume in background
        background_tasks.add_task(
            process_resume_background,
            file_path,
            metadata_id,
            file.filename
        )
        
        return UploadResponse(
            message="File uploaded successfully and processing started",
            file_id=storage_path,
            candidate_id=metadata_id,
            filename=file.filename,
            upload_time=upload_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")