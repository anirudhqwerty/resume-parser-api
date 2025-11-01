# app/utils/text_extractor.py
"""
Text extraction utilities for PDF and DOCX files with LaTeX cleanup
"""
import PyPDF2
from docx import Document
from app.core.logger import get_logger
import os
import re

logger = get_logger(__name__)


class TextExtractor:
    """Extract text from PDF and DOCX files"""
    
    async def extract(self, file_path: str) -> str:
        """
        Extract text from file based on extension
        
        Args:
            file_path: Path to the file
            
        Returns:
            Extracted text content
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            return await self._extract_from_pdf(file_path)
        elif file_ext == '.docx':
            return await self._extract_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
    
    async def _extract_from_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF file with LaTeX cleanup
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted and cleaned text
        """
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # Clean LaTeX artifacts
            text = self._clean_latex_artifacts(text)
            
            logger.info(f"Extracted and cleaned {len(text)} characters from PDF")
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise
    
    async def _extract_from_docx(self, file_path: str) -> str:
        """
        Extract text from DOCX file
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            Extracted text
        """
        try:
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            
            logger.info(f"Extracted {len(text)} characters from DOCX")
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {str(e)}")
            raise
    
    def _clean_latex_artifacts(self, text: str) -> str:
        """
        Clean common LaTeX PDF extraction artifacts
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove common LaTeX symbol replacements that PyPDF2 misreads
        replacements = {
            # Email artifacts
            'ï': '',  # Often appears before @
            'ï ': '',
            '# ': '',  # LaTeX phone/email separator
            '§ ': '',  # LaTeX symbols
            '¶ ': '',
            
            # Quote marks
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            
            # Special spaces
            '\xa0': ' ',  # Non-breaking space
            '\u200b': '',  # Zero-width space
            
            # LaTeX dash variants
            '–': '-',  # en-dash
            '—': '-',  # em-dash
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Fix email patterns where @ gets corrupted
        # Pattern: lettersp@email or letterspandemail
        text = re.sub(r'([a-z])p@([a-z])', r'\1@\2', text, flags=re.IGNORECASE)
        
        # Remove multiple spaces
        text = re.sub(r' +', ' ', text)
        
        # Remove spaces around @
        text = re.sub(r'\s*@\s*', '@', text)
        
        return text