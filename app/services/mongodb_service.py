# app/services/mongodb_service.py
"""
MongoDB integration for candidate data storage
"""
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.core.logger import get_logger
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

logger = get_logger(__name__)


class MongoDBService:
    """Handle MongoDB operations for candidate data"""
    
    def __init__(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_DB_NAME]
        self.collection = self.db[settings.MONGODB_COLLECTION_NAME]
    
    async def create_candidate(self, candidate_data: Dict[str, Any]) -> str:
        """
        Create a new candidate record in MongoDB
        
        Args:
            candidate_data: Dictionary containing candidate information
            
        Returns:
            MongoDB document ID
        """
        try:
            # Add created_at timestamp
            candidate_data["created_at"] = datetime.utcnow()
            
            # Insert into MongoDB
            result = await self.collection.insert_one(candidate_data)
            
            logger.info(f"Candidate created with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error creating candidate in MongoDB: {str(e)}")
            raise
    
    async def get_candidate(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """
        Get candidate by candidate_id (from Supabase)
        
        Args:
            candidate_id: Candidate ID from Supabase metadata
            
        Returns:
            Candidate document or None
        """
        try:
            candidate = await self.collection.find_one({"candidate_id": candidate_id})
            return candidate
            
        except Exception as e:
            logger.error(f"Error getting candidate from MongoDB: {str(e)}")
            return None
    
    async def list_candidates(self) -> List[Dict[str, Any]]:
        """
        List all candidates
        
        Returns:
            List of candidate documents
        """
        try:
            cursor = self.collection.find({}).sort("created_at", -1)
            candidates = await cursor.to_list(length=100)
            
            logger.info(f"Retrieved {len(candidates)} candidates")
            return candidates
            
        except Exception as e:
            logger.error(f"Error listing candidates from MongoDB: {str(e)}")
            return []
    
    async def update_candidate(self, candidate_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update candidate information
        
        Args:
            candidate_id: Candidate ID from Supabase
            update_data: Dictionary with fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"candidate_id": candidate_id},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating candidate in MongoDB: {str(e)}")
            return False
    
    async def delete_candidate(self, candidate_id: str) -> bool:
        """
        Delete candidate by ID
        
        Args:
            candidate_id: Candidate ID from Supabase
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.collection.delete_one({"candidate_id": candidate_id})
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting candidate from MongoDB: {str(e)}")
            return False