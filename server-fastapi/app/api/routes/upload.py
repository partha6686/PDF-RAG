from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uuid
from datetime import datetime
from typing import Dict, Any, List

from app.core.auth import get_current_user
from app.core.config import settings
from app.models.schemas import DocumentUploadResponse, DocumentListResponse, DocumentMetadata
from app.models.database import get_db, Document as DBDocument
from app.services.storage_service import StorageService
from app.services.document_processor import DocumentProcessor

router = APIRouter()

# Initialize document processor
document_processor = DocumentProcessor()

@router.post("/", response_model=DocumentUploadResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload PDF file for processing"""
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Check file size
    if file.size and file.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
        )
    
    try:
        # Generate unique identifiers
        document_id = str(uuid.uuid4())
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Initialize storage service
        storage_service = StorageService()
        
        # Upload file to MinIO
        from io import BytesIO
        file_stream = BytesIO(content)
        s3_key = storage_service.upload_file(
            file_data=file_stream,
            filename=f"{document_id}_{file.filename}",
            content_type="application/pdf"
        )
        
        # Create database record
        db_document = DBDocument(
            document_id=document_id,
            user_id=current_user["user_id"],
            filename=f"{document_id}_{file.filename}",
            original_name=file.filename,
            file_size=file_size,
            s3_key=s3_key,
            processing_status="pending",
            chunk_count=0,
            qdrant_collection=f"doc_{document_id}",
            created_at=datetime.utcnow()
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        # Start background processing
        background_tasks.add_task(
            document_processor.process_document,
            document_id
        )
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=db_document.filename,
            s3_key=s3_key,
            processing_status="pending",
            message="PDF uploaded successfully. Processing started in background."
        )
    
    except Exception as e:
        db.rollback()
        # TODO: Clean up MinIO file if needed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )

@router.get("/documents", response_model=DocumentListResponse)
async def list_user_documents(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all documents for the current user"""
    try:
        documents = db.query(DBDocument).filter(
            DBDocument.user_id == current_user["user_id"]
        ).order_by(DBDocument.created_at.desc()).all()
        
        document_list = [DocumentMetadata.model_validate(doc) for doc in documents]
        
        return DocumentListResponse(
            documents=document_list,
            total=len(document_list)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch documents: {str(e)}"
        )

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific document and its chunks"""
    try:
        # Find document
        document = db.query(DBDocument).filter(
            DBDocument.document_id == document_id,
            DBDocument.user_id == current_user["user_id"]
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # TODO: Delete from MinIO
        # storage_service = StorageService()
        # storage_service.delete_file(document.s3_key)
        
        # TODO: Delete from Qdrant
        # qdrant_service = QdrantService()
        # await qdrant_service.delete_document_collection(document_id)
        
        # Delete from database
        db.delete(document)
        db.commit()
        
        return {
            "message": f"Document {document_id} deleted successfully",
            "document_id": document_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )