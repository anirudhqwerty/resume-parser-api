# app/core/logger.py
"""
Centralized logging configuration for the application
"""
import logging
import sys
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the specified name.
    
    Args:
        name: Name of the logger (typically __name__ of the module)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
    
    return logger