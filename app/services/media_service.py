# app/services/media_service.py
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import uuid
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class MediaService:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4")
        )

    def generate_presigned_upload_url(self, file_name: str, file_type: str) -> dict:
        object_key = f"uploads/{uuid.uuid4()}-{file_name}"
        
        try:
            response = self.s3_client.generate_presigned_post(
                Bucket=settings.S3_BUCKET_NAME,
                Key=object_key,
                Fields={"Content-Type": file_type},
                Conditions=[{"Content-Type": file_type}],
                ExpiresIn=settings.S3_PRESIGNED_URL_EXPIRATION,
            )
            return {"upload_url": response['url'], "fields": response['fields'], "file_key": object_key}
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None

media_service = MediaService()