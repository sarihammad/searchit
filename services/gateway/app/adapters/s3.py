"""
S3/MinIO adapter for object storage
"""

from typing import Optional, BinaryIO
import logging
from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger(__name__)

class S3Adapter:
    """Adapter for S3/MinIO operations"""
    
    def __init__(self):
        self.client = None
        self.bucket_name = settings.minio_bucket
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize MinIO client"""
        try:
            self.client = Minio(
                settings.minio_endpoint.replace("http://", "").replace("https://", ""),
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=False  # HTTP for local dev
            )
            
            # Ensure bucket exists
            self._ensure_bucket_exists()
            
            logger.info("MinIO client initialized", extra={
                "endpoint": settings.minio_endpoint,
                "bucket": self.bucket_name
            })
            
        except Exception as e:
            logger.error("Failed to initialize MinIO client", extra={
                "error": str(e)
            })
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info("MinIO bucket created", extra={
                    "bucket": self.bucket_name
                })
        except S3Error as e:
            logger.error("Failed to create MinIO bucket", extra={
                "bucket": self.bucket_name,
                "error": str(e)
            })
    
    def upload_file(
        self,
        object_name: str,
        file_path: str,
        content_type: Optional[str] = None
    ) -> bool:
        """Upload a file to MinIO"""
        try:
            self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type
            )
            
            logger.info("File uploaded successfully", extra={
                "object_name": object_name,
                "bucket": self.bucket_name
            })
            return True
            
        except S3Error as e:
            logger.error("Failed to upload file", extra={
                "object_name": object_name,
                "error": str(e)
            })
            return False
    
    def upload_data(
        self,
        object_name: str,
        data: BinaryIO,
        length: int,
        content_type: Optional[str] = None
    ) -> bool:
        """Upload data stream to MinIO"""
        try:
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=data,
                length=length,
                content_type=content_type
            )
            
            logger.info("Data uploaded successfully", extra={
                "object_name": object_name,
                "bucket": self.bucket_name
            })
            return True
            
        except S3Error as e:
            logger.error("Failed to upload data", extra={
                "object_name": object_name,
                "error": str(e)
            })
            return False
    
    def download_file(self, object_name: str, file_path: str) -> bool:
        """Download a file from MinIO"""
        try:
            self.client.fget_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=file_path
            )
            
            logger.info("File downloaded successfully", extra={
                "object_name": object_name,
                "file_path": file_path
            })
            return True
            
        except S3Error as e:
            logger.error("Failed to download file", extra={
                "object_name": object_name,
                "error": str(e)
            })
            return False
    
    def get_object_url(self, object_name: str) -> str:
        """Get presigned URL for object access"""
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=3600  # 1 hour
            )
            return url
        except S3Error as e:
            logger.error("Failed to get object URL", extra={
                "object_name": object_name,
                "error": str(e)
            })
            return ""
    
    def delete_object(self, object_name: str) -> bool:
        """Delete an object from MinIO"""
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            
            logger.info("Object deleted successfully", extra={
                "object_name": object_name
            })
            return True
            
        except S3Error as e:
            logger.error("Failed to delete object", extra={
                "object_name": object_name,
                "error": str(e)
            })
            return False
    
    def list_objects(self, prefix: str = "") -> list:
        """List objects in bucket with optional prefix"""
        try:
            objects = []
            for obj in self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix
            ):
                objects.append({
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified
                })
            
            return objects
            
        except S3Error as e:
            logger.error("Failed to list objects", extra={
                "prefix": prefix,
                "error": str(e)
            })
            return []
