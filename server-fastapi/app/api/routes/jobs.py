from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any

from app.core.auth import get_current_user
from app.models.schemas import JobInfo
from app.workers.celery_app import celery_app

router = APIRouter()

@router.get("/{job_id}", response_model=JobInfo)
async def get_job_status(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get status of a processing job"""
    
    try:
        # Get job result from Celery
        result = celery_app.AsyncResult(job_id)
        
        # Map Celery states to our JobStatus enum
        status_mapping = {
            'PENDING': 'pending',
            'STARTED': 'active',
            'SUCCESS': 'completed',
            'FAILURE': 'failed',
            'RETRY': 'active',
            'REVOKED': 'failed'
        }
        
        job_status = status_mapping.get(result.state, 'pending')
        
        # Get progress info if available
        progress = None
        if result.state == 'PROGRESS' or (hasattr(result, 'info') and result.info):
            info = result.info or {}
            if isinstance(info, dict) and 'percent' in info:
                progress = {
                    'percent': info.get('percent', 0),
                    'message': info.get('message', 'Processing...')
                }
        
        return JobInfo(
            job_id=job_id,
            status=job_status,
            progress=progress,
            result=result.result if job_status == 'completed' else None,
            error=str(result.info) if job_status == 'failed' and result.info else None,
            created_at=result.date_done or result.args[0] if hasattr(result, 'args') else None,
            completed_at=result.date_done if job_status in ['completed', 'failed'] else None
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )