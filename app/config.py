# app/config.py
"""
Configuration management for the application.
Loads all environment variables and provides a centralized config object.
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Resume Parser API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_BUCKET_NAME: str = "resumes"
    
    # MongoDB
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "resume_parser"
    MONGODB_COLLECTION_NAME: str = "candidates"
    
    # Hugging Face
    HUGGINGFACE_API_KEY: str
    HUGGINGFACE_EXTRACTION_MODEL: str = "facebook/bart-large-cnn"
    HUGGINGFACE_QA_MODEL: str = "mistralai/Mistral-7B-Instruct-v0.2"
    
    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list = [".pdf", ".docx"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()