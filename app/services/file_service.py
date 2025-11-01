# app/services/file_service.py
"""
File handling service for upload and validation
"""
from fastapi import UploadFile, HTTPException
from app.config import settings
from app.utils.text_extractor import TextExtractor
from app.core.logger import get_logger
import os
import aiofiles
from pathlib import Path

logger = get_logger(__name__)


class FileService:
    """Handles file upload, validation, and text extraction"""
    
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self.max_file_size = settings.MAX_FILE_SIZE
        self.allowed_extensions = settings.ALLOWED_EXTENSIONS
        self.text_extractor = TextExtractor()
        
        # Create upload directory if it doesn't exist
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
    
    def validate_file(self, file: UploadFile) -> None:
        """
        Validate uploaded file extension and size
        
        Args:
            file: Uploaded file object
            
        Raises:
            HTTPException: If validation fails
        """
        # Check file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} not allowed. Allowed types: {', '.join(self.allowed_extensions)}"
            )
        
        logger.info(f"File validation passed for {file.filename}")
    
    async def save_file(self, file: UploadFile) -> str:
        """
        Save uploaded file to local storage
        
        Args:
            file: Uploaded file object
            
        Returns:
            Path to saved file
        """
        try:
            file_path = os.path.join(self.upload_dir, file.filename)
            
            # Save file asynchronously
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                
                # Check file size
                if len(content) > self.max_file_size:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File size exceeds maximum allowed size of {self.max_file_size / (1024*1024)}MB"
                    )
                
                await f.write(content)
            
            logger.info(f"File saved successfully: {file_path}")
            return file_path
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    async def extract_text(self, file_path: str) -> str:
        """
        Extract text content from resume file
        
        Args:
            file_path: Path to the resume file
            
        Returns:
            Extracted text content
        """
        try:
            text = await self.text_extractor.extract(file_path)
            logger.info(f"Text extracted from {file_path}, length: {len(text)}")
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            raise