from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any
import asyncio

from app.core.auth import get_current_user
from app.models.database import get_db, Document as DBDocument
from app.services.document_processor import DocumentProcessor
from app.services.process_tracker import process_tracker

router = APIRouter()

# Initialize document processor
document_processor = DocumentProcessor()

@router.post("/process/{document_id}")
async def process_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger document processing"""
    try:
        # Verify document exists and belongs to user
        document = db.query(DBDocument).filter(
            DBDocument.document_id == document_id,
            DBDocument.user_id == current_user["user_id"]
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        if document.processing_status == "processing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document is already being processed"
            )

        if document.processing_status == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document has already been processed"
            )

        # Add processing task to background
        background_tasks.add_task(
            document_processor.process_document,
            document_id
        )

        return {
            "message": f"Document {document_id} processing started",
            "document_id": document_id,
            "status": "processing"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start processing: {str(e)}"
        )

@router.post("/process-pending")
async def process_pending_documents(
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Process all pending documents for current user"""
    try:
        # Add processing task to background
        background_tasks.add_task(
            document_processor.process_pending_documents
        )

        return {
            "message": "Pending document processing started",
            "status": "processing"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start pending processing: {str(e)}"
        )

@router.get("/stats")
async def get_processing_stats(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get document processing statistics"""
    try:
        stats = document_processor.get_processing_stats()
        return {
            "processing_stats": stats,
            "user_id": current_user["user_id"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get processing stats: {str(e)}"
        )

@router.get("/status/{document_id}")
async def get_document_status(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get processing status for a specific document"""
    try:
        document = db.query(DBDocument).filter(
            DBDocument.document_id == document_id,
            DBDocument.user_id == current_user["user_id"]
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        return {
            "document_id": document_id,
            "filename": document.original_name,
            "processing_status": document.processing_status,
            "chunk_count": document.chunk_count,
            "created_at": document.created_at,
            "processed_at": document.processed_at
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document status: {str(e)}"
        )

@router.get("/process/{process_id}")
async def get_process_status(
    process_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get processing status for a specific process ID"""
    try:
        process = await process_tracker.get_process(process_id)

        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process not found"
            )

        return {
            "process_id": process_id,
            "document_id": process.document_id,
            "status": process.status,
            "progress_percent": process.progress_percent,
            "message": process.message,
            "created_at": process.created_at,
            "completed_at": process.completed_at,
            "error": process.error
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get process status: {str(e)}"
        )
