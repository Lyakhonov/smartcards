import io
from typing import Optional
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


class StorageService:
    def __init__(self):
        # клиент для внутренней работы (docker)
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

        # клиент для генерации URL (ВАЖНО!)
        self.public_client = Minio(
            settings.MINIO_PUBLIC_ENDPOINT.replace("http://", "").replace(
                "https://", ""
            ),
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_PUBLIC_ENDPOINT.startswith("https"),
        )

        self.bucket = settings.MINIO_BUCKET

    def ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error:
            raise

    def upload_bytes(
        self, data: bytes, object_name: str, content_type: Optional[str] = None
    ):
        f = io.BytesIO(data)
        f.seek(0)

        self.client.put_object(
            self.bucket,
            object_name,
            data=f,
            length=len(data),
            content_type=content_type or "application/octet-stream",
        )

    def get_presigned_url(self, object_name: str, expires: int = 3600):
        try:
            # ВАЖНО: используем public_client
            return self.public_client.presigned_get_object(
                self.bucket,
                object_name,
                expires=timedelta(seconds=expires),
            )
        except Exception as e:
            print("❌ presigned error:", e)
            return None

    def delete_object(self, object_name: str):
        try:
            self.client.remove_object(self.bucket, object_name)
        except S3Error:
            raise


storage = StorageService()
