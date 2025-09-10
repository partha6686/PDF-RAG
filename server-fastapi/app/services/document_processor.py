from sqlalchemy.orm import Session
from typing import Dict, Any, List
import logging
from datetime import datetime
import asyncio

from app.models.database import Document as DBDocument, get_db
from app.services.pdf_service import PDFService
from app.services.embedding_service import EmbeddingService
from app.services.storage_service import StorageService
from app.services.qdrant_service import QdrantService
from app.core.config import settings

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Service for processing documents end-to-end"""
    
    def __init__(self):
        self.pdf_service = PDFService()
        self.embedding_service = EmbeddingService()
        self.storage_service = StorageService()
        self.qdrant_service = QdrantService()
    
    async def process_document(self, document_id: str) -> Dict[str, Any]:
        """Process a document through the complete pipeline"""
        try:
            logger.info(f"Starting document processing for {document_id}")
            
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
                
                # Step 1: Download file from MinIO
                logger.info(f"Step 1: Downloading file from MinIO")
                file_data = self.storage_service.download_file(document.s3_key)
                
                # Step 2: Extract text from PDF
                logger.info(f"Step 2: Extracting text from PDF")
                text_content = self.pdf_service.extract_text_from_bytes(file_data)
                
                if not text_content.strip():
                    raise ValueError("No text content found in PDF")
                
                # Step 3: Create text chunks
                logger.info(f"Step 3: Creating text chunks")
                chunks = self.pdf_service.create_text_chunks(
                    text_content, 
                    chunk_size=settings.CHUNK_SIZE,
                    chunk_overlap=settings.CHUNK_OVERLAP
                )
                
                if not chunks:
                    raise ValueError("No chunks created from text")
                
                # Step 4: Generate embeddings
                logger.info(f"Step 4: Generating embeddings for {len(chunks)} chunks")
                chunk_texts = [chunk["text"] for chunk in chunks]
                embeddings = await self.embedding_service.generate_embeddings(chunk_texts)
                
                if len(embeddings) != len(chunks):
                    raise ValueError(f"Embedding count mismatch: {len(embeddings)} vs {len(chunks)}")
                
                # Step 5: Store in Qdrant
                logger.info(f"Step 5: Storing embeddings in Qdrant")
                stored_count = await self.qdrant_service.store_document_chunks(
                    user_id=document.user_id,
                    document_id=document_id,
                    chunks=chunks,
                    embeddings=embeddings
                )
                
                # Step 6: Update document status
                document.processing_status = "completed"
                document.chunk_count = stored_count
                document.processed_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"Document {document_id} processed successfully: {stored_count} chunks stored")
                
                return {
                    "success": True,
                    "document_id": document_id,
                    "chunk_count": stored_count,
                    "text_length": len(text_content),
                    "processing_time": (datetime.utcnow() - document.created_at).total_seconds()
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
            logger.error(f"Document processing error for {document_id}: {e}")
            return {
                "success": False,
                "document_id": document_id,
                "error": str(e)
            }
    
    async def reprocess_failed_documents(self) -> List[Dict[str, Any]]:
        """Reprocess all documents with failed status"""
        try:
            db = next(get_db())
            
            try:
                failed_docs = db.query(DBDocument).filter(
                    DBDocument.processing_status == "failed"
                ).all()
                
                logger.info(f"Found {len(failed_docs)} failed documents to reprocess")
                
                results = []
                for doc in failed_docs:
                    result = await self.process_document(doc.document_id)
                    results.append(result)
                    
                    # Add delay between processing to avoid overwhelming services
                    await asyncio.sleep(1)
                
                return results
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed document reprocessing error: {e}")
            return []
    
    async def process_pending_documents(self) -> List[Dict[str, Any]]:
        """Process all documents with pending status"""
        try:
            db = next(get_db())
            
            try:
                pending_docs = db.query(DBDocument).filter(
                    DBDocument.processing_status == "pending"
                ).all()
                
                logger.info(f"Found {len(pending_docs)} pending documents to process")
                
                results = []
                for doc in pending_docs:
                    result = await self.process_document(doc.document_id)
                    results.append(result)
                    
                    # Add delay between processing
                    await asyncio.sleep(2)
                
                return results
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Pending document processing error: {e}")
            return []
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get document processing statistics"""
        try:
            db = next(get_db())
            
            try:
                total_docs = db.query(DBDocument).count()
                completed_docs = db.query(DBDocument).filter(
                    DBDocument.processing_status == "completed"
                ).count()
                pending_docs = db.query(DBDocument).filter(
                    DBDocument.processing_status == "pending"
                ).count()
                processing_docs = db.query(DBDocument).filter(
                    DBDocument.processing_status == "processing"
                ).count()
                failed_docs = db.query(DBDocument).filter(
                    DBDocument.processing_status == "failed"
                ).count()
                
                return {
                    "total": total_docs,
                    "completed": completed_docs,
                    "pending": pending_docs,
                    "processing": processing_docs,
                    "failed": failed_docs
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error getting processing stats: {e}")
            return {}