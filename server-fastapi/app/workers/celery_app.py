from celery import Celery
import os
import asyncio
import logging
from datetime import datetime

from app.core.config import settings
from app.utils.text_processor import TextProcessor
from app.utils.embeddings import EmbeddingService
from app.services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)

# Create Celery app
def create_celery():
    celery_app = Celery(
        "pdf_processing",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
        include=['app.workers.celery_app']
    )
    
    celery_app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_routes={
            'app.workers.celery_app.pdf_processing_task': {'queue': 'pdf_processing'},
        }
    )
    
    return celery_app

# Global Celery instance
celery_app = create_celery()

@celery_app.task(bind=True, name='pdf_processing_task')
def pdf_processing_task(self, file_path: str, original_name: str, document_id: str, user_id: str, job_id: str):
    """
    Celery task for processing PDF documents
    """
    logger.info(f"Starting PDF processing: {original_name} (User: {user_id}, Doc: {document_id})")
    
    async def process_pdf():
        try:
            # Initialize services
            text_processor = TextProcessor()
            embedding_service = EmbeddingService()
            qdrant_service = QdrantService()
            
            # Step 1: Extract text from PDF (5%)
            logger.info('📄 Extracting text from PDF...')
            self.update_state(
                state='PROGRESS',
                meta={'percent': 5, 'message': '📄 Extracting text from PDF...'}
            )
            
            raw_text = await text_processor.extract_text_from_pdf(file_path)
            logger.info(f"Extracted {len(raw_text)} characters")
            
            # Step 2: Clean and normalize text (5%)
            logger.info('🧹 Cleaning and normalizing text...')
            self.update_state(
                state='PROGRESS', 
                meta={'percent': 10, 'message': '🧹 Cleaning and normalizing text...'}
            )
            
            cleaned_text = text_processor.clean_text(raw_text)
            
            # Step 3: Chunk the text (5%)
            logger.info('✂️ Chunking text into segments...')
            self.update_state(
                state='PROGRESS',
                meta={'percent': 15, 'message': '✂️ Chunking text into segments...'}
            )
            
            chunks = text_processor.chunk_text(
                cleaned_text, 
                chunk_size=settings.CHUNK_SIZE, 
                overlap=settings.CHUNK_OVERLAP
            )
            logger.info(f"Created {len(chunks)} text chunks")
            
            # Step 4: Generate embeddings (75% - 15% to 90%)
            logger.info(f'🧠 Starting embedding generation for {len(chunks)} chunks...')
            self.update_state(
                state='PROGRESS',
                meta={'percent': 20, 'message': f'🧠 Generating embeddings for {len(chunks)} chunks...'}
            )
            
            chunk_texts = [chunk['text'] for chunk in chunks]
            
            def embedding_progress_callback(status_message):
                """Progress callback for embedding generation"""
                # Extract percentage from status message
                import re
                match = re.search(r'\\((\\d+)%\\)', status_message)
                embedding_percent = int(match.group(1)) if match else 0
                
                # Map embedding progress (0-100%) to overall progress (20-90%)
                overall_percent = 20 + int((embedding_percent / 100) * 70)
                
                self.update_state(
                    state='PROGRESS',
                    meta={'percent': overall_percent, 'message': status_message}
                )
            
            embeddings = await embedding_service.generate_batch_embeddings(
                chunk_texts, 
                progress_callback=embedding_progress_callback
            )
            
            # Step 5: Store in vector database (5%)
            logger.info('💾 Storing chunks in vector database...')
            self.update_state(
                state='PROGRESS',
                meta={'percent': 95, 'message': '💾 Storing chunks in vector database...'}
            )
            
            stored_count = await qdrant_service.store_document_chunks(
                user_id=user_id,
                document_id=document_id,
                chunks=chunks,
                embeddings=embeddings
            )
            
            # Step 6: Cleanup and completion (5%)
            logger.info('🧹 Cleaning up temporary files...')
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted temporary file: {file_path}")
            
            # Final success state
            logger.info('🎉 PDF processing completed successfully!')
            self.update_state(
                state='PROGRESS',
                meta={'percent': 100, 'message': '🎉 PDF processing completed successfully!'}
            )
            
            return {
                'document_id': document_id,
                'user_id': user_id,
                'original_name': original_name,
                'chunks_stored': stored_count,
                'processing_time': datetime.now().isoformat(),
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            
            # Cleanup on failure
            if os.path.exists(file_path):
                os.remove(file_path)
                
            self.update_state(
                state='FAILURE',
                meta={'error': str(e), 'message': f'❌ Processing failed: {str(e)}'}
            )
            raise
    
    # Run the async function
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(process_pdf())
    finally:
        loop.close()