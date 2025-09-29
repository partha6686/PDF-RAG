from minio import Minio
from minio.error import S3Error
import io
import uuid
from typing import BinaryIO
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    """MinIO S3-compatible storage service"""
    
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False  # Use HTTP for local development
        )
        self.bucket_name = "pdf-documents"
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"✅ Created MinIO bucket: {self.bucket_name}")
            else:
                logger.info(f"✅ MinIO bucket exists: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Failed to create bucket: {e}")
            raise
    
    def upload_file(self, file_data: BinaryIO, filename: str, content_type: str = "application/pdf") -> str:
        """Upload file to MinIO and return the object key"""
        try:
            # Generate unique object key
            file_extension = filename.split('.')[-1] if '.' in filename else ''
            object_key = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
            
            # Get file size
            file_data.seek(0, 2)  # Seek to end
            file_size = file_data.tell()
            file_data.seek(0)  # Reset to beginning
            
            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=file_data,
                length=file_size,
                content_type=content_type
            )
            
            logger.info(f"✅ Uploaded file to MinIO: {object_key}")
            return object_key
            
        except S3Error as e:
            logger.error(f"Failed to upload file: {e}")
            raise
    
    def download_file(self, object_key: str) -> BinaryIO:
        """Download file from MinIO"""
        try:
            response = self.client.get_object(self.bucket_name, object_key)
            return io.BytesIO(response.read())
        except S3Error as e:
            logger.error(f"Failed to download file {object_key}: {e}")
            raise
    
    def delete_file(self, object_key: str) -> bool:
        """Delete file from MinIO"""
        try:
            self.client.remove_object(self.bucket_name, object_key)
            logger.info(f"✅ Deleted file from MinIO: {object_key}")
            return True
        except S3Error as e:
            logger.error(f"Failed to delete file {object_key}: {e}")
            return False
    
    def get_file_url(self, object_key: str, expires_in_seconds: int = 3600) -> str:
        """Get presigned URL for file access"""
        try:
            return self.client.presigned_get_object(
                self.bucket_name, 
                object_key, 
                expires=expires_in_seconds
            )
        except S3Error as e:
            logger.error(f"Failed to generate URL for {object_key}: {e}")
            raise