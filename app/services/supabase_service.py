# app/services/supabase_service.py
"""
Supabase integration for file storage and metadata
"""
from supabase import create_client, Client
from fastapi import UploadFile, HTTPException
from app.config import settings
from app.core.logger import get_logger
from datetime import datetime
import uuid

logger = get_logger(__name__)


class SupabaseService:
    """Handle Supabase operations for storage and database"""
    
    def __init__(self):
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
        self.bucket_name = settings.SUPABASE_BUCKET_NAME
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the storage bucket exists"""
        try:
            buckets = self.client.storage.list_buckets()
            bucket_names = [bucket.name for bucket in buckets]
            
            if self.bucket_name not in bucket_names:
                self.client.storage.create_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
        except Exception as e:
            logger.warning(f"Could not verify bucket existence: {str(e)}")
    
    async def upload_file(self, file: UploadFile, file_path: str) -> str:
        """
        Upload file to Supabase storage
        
        Args:
            file: FastAPI UploadFile object
            file_path: Local path to file
            
        Returns:
            Storage path in Supabase
        """
        try:
            # Generate unique filename
            file_ext = file.filename.split('.')[-1]
            unique_filename = f"{uuid.uuid4()}.{file_ext}"
            storage_path = f"resumes/{unique_filename}"
            
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Upload to Supabase storage
            self.client.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": file.content_type}
            )
            
            logger.info(f"File uploaded to Supabase: {storage_path}")
            return storage_path
            
        except Exception as e:
            logger.error(f"Error uploading to Supabase: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to upload to Supabase: {str(e)}")
    
    async def save_metadata(self, metadata: dict) -> str:
        """
        Save file metadata to Supabase database
        
        Args:
            metadata: Dictionary containing file metadata
            
        Returns:
            ID of inserted record
        """
        try:
            # Add created_at timestamp
            metadata["created_at"] = datetime.utcnow().isoformat()
            metadata["id"] = str(uuid.uuid4())
            
            # Insert into resumes_metadata table
            response = self.client.table("resumes_metadata").insert(metadata).execute()
            
            if not response.data:
                raise Exception("No data returned from insert")
            
            metadata_id = response.data[0]["id"]
            logger.info(f"Metadata saved with ID: {metadata_id}")
            return metadata_id
            
        except Exception as e:
            logger.error(f"Error saving metadata to Supabase: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save metadata: {str(e)}")
    
    async def get_metadata(self, metadata_id: str) -> dict:
        """
        Retrieve metadata by ID
        
        Args:
            metadata_id: ID of metadata record
            
        Returns:
            Metadata dictionary
        """
        try:
            response = self.client.table("resumes_metadata").select("*").eq("id", metadata_id).execute()
            
            if not response.data:
                return None
            
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Error getting metadata from Supabase: {str(e)}")
            return None