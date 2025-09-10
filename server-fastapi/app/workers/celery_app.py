from celery import Celery
import os
import asyncio
import logging
from datetime import datetime

from app.core.config import settings
from app.services.pdf_service import PDFService
from app.services.embedding_service import EmbeddingService
from app.services.storage_service import StorageService
from app.services.qdrant_service import QdrantService
from app.models.database import get_db, Document as DBDocument
from datetime import datetime

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
            pdf_service = PDFService()
            embedding_service = EmbeddingService()
            storage_service = StorageService()
            qdrant_service = QdrantService()

            # Get database session
            db = next(get_db())

            try:
                # Get document from database
                document = db.query(DBDocument).filter(
                    DBDocument.document_id == document_id
                ).first()

                if not document:
                    raise ValueError(f"Document {document_id} not found")

                # Update status to processing
                document.processing_status = "processing"
                db.commit()
                logger.info(f"Document {document_id} status updated to processing")

                # Step 1: Extract text from PDF (5%)
                logger.info('📄 Extracting text from PDF...')
                self.update_state(
                    state='PROGRESS',
                    meta={'percent': 5, 'message': '📄 Extracting text from PDF...'}
                )

                # Read PDF file
                with open(file_path, 'rb') as pdf_file:
                    pdf_bytes = pdf_file.read()

                text_content = pdf_service.extract_text_from_bytes(pdf_bytes)
                logger.info(f"Extracted {len(text_content)} characters")

                # Step 2: Create text chunks (5%)
                logger.info('✂️ Chunking text into segments...')
                self.update_state(
                    state='PROGRESS',
                    meta={'percent': 10, 'message': '✂️ Chunking text into segments...'}
                )

                chunks = pdf_service.create_text_chunks(
                    text_content,
                    chunk_size=settings.CHUNK_SIZE,
                    chunk_overlap=settings.CHUNK_OVERLAP
                )
                logger.info(f"Created {len(chunks)} text chunks")

                # Step 3: Generate embeddings (75% - 10% to 85%)
                logger.info(f'🧠 Starting embedding generation for {len(chunks)} chunks...')
                self.update_state(
                    state='PROGRESS',
                    meta={'percent': 15, 'message': f'🧠 Generating embeddings for {len(chunks)} chunks...'}
                )

                chunk_texts = [chunk["text"] for chunk in chunks]
                embeddings = await embedding_service.generate_embeddings(chunk_texts)

                if len(embeddings) != len(chunks):
                    raise ValueError(f"Embedding count mismatch: {len(embeddings)} vs {len(chunks)}")

                # Step 4: Store in vector database (10%)
                logger.info('💾 Storing chunks in vector database...')
                self.update_state(
                    state='PROGRESS',
                    meta={'percent': 90, 'message': '💾 Storing chunks in vector database...'}
                )

                stored_count = await qdrant_service.store_document_chunks(
                    user_id=user_id,
                    document_id=document_id,
                    chunks=chunks,
                    embeddings=embeddings
                )

                # Step 5: Update document status (5%)
                document.processing_status = "completed"
                document.chunk_count = stored_count
                document.processed_at = datetime.utcnow()
                db.commit()

                logger.info(f"Document {document_id} processed successfully: {stored_count} chunks stored")

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
                # Update document status to failed
                try:
                    document = db.query(DBDocument).filter(
                        DBDocument.document_id == document_id
                    ).first()
                    if document:
                        document.processing_status = "failed"
                        db.commit()
                except:
                    pass  # Don't let database errors mask the original error

                logger.error(f"Document processing failed for {document_id}: {e}")
                raise

            finally:
                db.close()

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
