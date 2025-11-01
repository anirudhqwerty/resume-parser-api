# app/__init__.py
"""
FastAPI Resume Parser Application
"""
from fastapi import FastAPI
from app.core.logger import get_logger

logger = get_logger(__name__)

__version__ = "1.0.0"