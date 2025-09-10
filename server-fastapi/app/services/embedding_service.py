import google.generativeai as genai
from typing import List, Dict, Any
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating embeddings using Google Gemini"""
    
    def __init__(self):
        # Configure Gemini API
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model_name = "models/text-embedding-004"
        self.batch_size = 100  # Process in batches to avoid rate limits
        self.delay_between_batches = 1  # 1 second delay between batches
        
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        try:
            if not texts:
                return []
            
            logger.info(f"Generating embeddings for {len(texts)} text chunks")
            
            all_embeddings = []
            
            # Process in batches to respect rate limits
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1
                total_batches = (len(texts) + self.batch_size - 1) // self.batch_size
                
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} texts)")
                
                batch_embeddings = await self._generate_batch_embeddings(batch)
                all_embeddings.extend(batch_embeddings)
                
                # Add delay between batches to respect rate limits
                if i + self.batch_size < len(texts):
                    await asyncio.sleep(self.delay_between_batches)
            
            logger.info(f"Successfully generated {len(all_embeddings)} embeddings")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    async def _generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts"""
        try:
            # Use ThreadPoolExecutor for blocking API calls
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                embeddings = await loop.run_in_executor(
                    executor, 
                    self._generate_embeddings_sync, 
                    texts
                )
            return embeddings
            
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            raise
    
    def _generate_embeddings_sync(self, texts: List[str]) -> List[List[float]]:
        """Synchronous embedding generation"""
        try:
            embeddings = []
            
            for text in texts:
                # Clean and truncate text if necessary
                cleaned_text = self._clean_text_for_embedding(text)
                
                # Generate embedding
                result = genai.embed_content(
                    model=self.model_name,
                    content=cleaned_text,
                    task_type="retrieval_document"
                )
                
                embeddings.append(result['embedding'])
                
                # Small delay between individual requests
                time.sleep(0.1)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Sync embedding generation failed: {e}")
            raise
    
    def _clean_text_for_embedding(self, text: str) -> str:
        """Clean and prepare text for embedding generation"""
        # Remove excessive whitespace
        cleaned = " ".join(text.split())
        
        # Truncate if too long (Gemini has token limits)
        max_length = 30000  # Conservative limit
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
            logger.warning(f"Text truncated from {len(text)} to {len(cleaned)} characters")
        
        return cleaned
    
    async def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for a single query"""
        try:
            cleaned_query = self._clean_text_for_embedding(query)
            
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(
                    executor,
                    lambda: genai.embed_content(
                        model=self.model_name,
                        content=cleaned_query,
                        task_type="retrieval_query"
                    )
                )
            
            return result['embedding']
            
        except Exception as e:
            logger.error(f"Query embedding generation failed: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """Test if Gemini API is accessible"""
        try:
            test_embedding = await self.generate_query_embedding("Test connection")
            return len(test_embedding) > 0
            
        except Exception as e:
            logger.error(f"Gemini API connection test failed: {e}")
            return False