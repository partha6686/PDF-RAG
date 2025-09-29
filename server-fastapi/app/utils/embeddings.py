import google.generativeai as genai
from typing import List, Callable, Optional
import asyncio
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY)

class EmbeddingService:
    """Service for generating embeddings using Google Gemini"""
    
    def __init__(self):
        self.model_name = "models/text-embedding-004"
        self.dimension = 768
        self.batch_size = 10
        self.batch_delay = 0.05  # 50ms delay between batches
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            result = await asyncio.to_thread(
                genai.embed_content,
                model=self.model_name,
                content=text
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    async def generate_batch_embeddings(
        self, 
        texts: List[str], 
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts with progress tracking"""
        
        embeddings = []
        total_batches = (len(texts) + self.batch_size - 1) // self.batch_size
        
        logger.info(f"Generating embeddings for {len(texts)} texts in {total_batches} batches")
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(texts))
            batch_texts = texts[start_idx:end_idx]
            
            # Process batch concurrently
            batch_tasks = [
                self.generate_embedding(text) 
                for text in batch_texts
            ]
            
            try:
                batch_embeddings = await asyncio.gather(*batch_tasks)
                embeddings.extend(batch_embeddings)
                
                # Report progress
                progress_percent = int(((batch_idx + 1) / total_batches) * 100)
                if progress_callback:
                    status_message = f"🧠 Generating embeddings... Batch {batch_idx + 1}/{total_batches} ({progress_percent}%)"
                    progress_callback(status_message)
                
                logger.info(f"Completed batch {batch_idx + 1}/{total_batches} ({progress_percent}%)")
                
                # Add delay between batches to respect rate limits
                if batch_idx < total_batches - 1:
                    await asyncio.sleep(self.batch_delay)
                    
            except Exception as e:
                logger.error(f"Batch {batch_idx + 1} failed: {e}")
                # Add None embeddings for failed batch
                embeddings.extend([None] * len(batch_texts))
        
        logger.info(f"Generated {len([e for e in embeddings if e is not None])} valid embeddings")
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this service"""
        return self.dimension