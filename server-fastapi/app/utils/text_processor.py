import PyPDF2
import re
import io
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class TextProcessor:
    """Service for processing PDF documents and text chunking"""
    
    @staticmethod
    async def extract_text_from_pdf(file_path: str) -> str:
        """Extract text content from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\\n"
                
                if not text.strip():
                    raise ValueError("No text could be extracted from the PDF")
                
                logger.info(f"Extracted {len(text)} characters from PDF")
                return text
        
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            raise
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize extracted text"""
        try:
            # Remove excessive whitespace
            text = re.sub(r'\\n+', '\\n', text)
            text = re.sub(r'\\s+', ' ', text)
            
            # Remove special characters that might interfere with processing
            text = re.sub(r'[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\x7f-\\xff]', '', text)
            
            # Strip and normalize
            text = text.strip()
            
            logger.info(f"Cleaned text: {len(text)} characters")
            return text
        
        except Exception as e:
            logger.error(f"Text cleaning failed: {e}")
            return text  # Return original if cleaning fails
    
    @staticmethod
    def chunk_text(
        text: str, 
        chunk_size: int = 2000, 
        overlap: int = 400
    ) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks"""
        try:
            chunks = []
            start = 0
            
            while start < len(text):
                end = start + chunk_size
                
                # If we're not at the end, try to find a good break point
                if end < len(text):
                    # Look for sentence endings within the last 200 characters
                    search_start = max(start + chunk_size - 200, start)
                    chunk_text = text[start:end]
                    
                    # Find the last sentence ending
                    last_period = chunk_text.rfind('.')
                    last_exclamation = chunk_text.rfind('!')
                    last_question = chunk_text.rfind('?')
                    
                    last_sentence_end = max(last_period, last_exclamation, last_question)
                    
                    if last_sentence_end > len(chunk_text) * 0.5:  # Only if it's not too early
                        end = start + last_sentence_end + 1
                
                chunk_text = text[start:end].strip()
                
                if chunk_text:
                    chunks.append({
                        'text': chunk_text,
                        'size': len(chunk_text),
                        'start': start,
                        'end': end
                    })
                
                # Move start position with overlap
                start = max(start + chunk_size - overlap, end)
                
                # Avoid infinite loop
                if start >= len(text):
                    break
            
            logger.info(f"Created {len(chunks)} text chunks")
            return chunks
        
        except Exception as e:
            logger.error(f"Text chunking failed: {e}")
            # Return single chunk as fallback
            return [{
                'text': text,
                'size': len(text),
                'start': 0,
                'end': len(text)
            }]