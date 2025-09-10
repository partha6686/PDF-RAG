

from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
from enum import Enum

class ProcessStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ProcessInfo:
    def __init__(self, process_id: str, document_id: str, status: ProcessStatus = ProcessStatus.PENDING):
        self.process_id = process_id
        self.document_id = document_id
        self.status = status
        self.progress_percent = 0
        self.message = "Processing started..."
        self.created_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None

class ProcessTracker:
    """Simple in-memory process tracker"""

    def __init__(self):
        self._processes: Dict[str, ProcessInfo] = {}
        self._lock = asyncio.Lock()

    async def create_process(self, process_id: str, document_id: str) -> ProcessInfo:
        """Create a new process"""
        async with self._lock:
            process = ProcessInfo(process_id, document_id)
            self._processes[process_id] = process
            return process

    async def get_process(self, process_id: str) -> Optional[ProcessInfo]:
        """Get process by ID"""
        async with self._lock:
            return self._processes.get(process_id)

    async def update_process(self, process_id: str, status: ProcessStatus,
                           progress_percent: int = 0, message: str = "",
                           error: Optional[str] = None) -> bool:
        """Update process status"""
        async with self._lock:
            if process_id not in self._processes:
                return False

            process = self._processes[process_id]
            process.status = status
            process.progress_percent = progress_percent
            process.message = message
            process.error = error

            if status in [ProcessStatus.COMPLETED, ProcessStatus.FAILED]:
                process.completed_at = datetime.utcnow()

            return True

    async def delete_process(self, process_id: str) -> bool:
        """Delete process (cleanup)"""
        async with self._lock:
            if process_id in self._processes:
                del self._processes[process_id]
                return True
            return False

    async def cleanup_old_processes(self, max_age_hours: int = 24):
        """Clean up old completed processes"""
        async with self._lock:
            cutoff_time = datetime.utcnow().replace(hour=datetime.utcnow().hour - max_age_hours)
            to_delete = []

            for process_id, process in self._processes.items():
                if (process.status in [ProcessStatus.COMPLETED, ProcessStatus.FAILED] and
                    process.completed_at and process.completed_at < cutoff_time):
                    to_delete.append(process_id)

            for process_id in to_delete:
                del self._processes[process_id]

# Global process tracker instance
process_tracker = ProcessTracker()
