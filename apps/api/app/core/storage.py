"""MinIO / S3 兼容对象存储封装（Day25：知识库上传的原始文件落桶）。

单机 Demo 用同步 boto3 client；bucket 在首次写入时惰性创建，
避免 MinIO 未启动时影响 API 启动。
"""

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class Storage:
    def __init__(self) -> None:
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.minio_endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key.get_secret_value(),
            region_name="us-east-1",
        )
        self.bucket = "workpilot"

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            # 404 / NoSuchBucket 时创建；其余错误上抛，避免吞掉权限类问题。
            if e.response["Error"]["Code"] in {"404", "NoSuchBucket", "NotFound"}:
                self.client.create_bucket(Bucket=self.bucket)
            else:
                raise

    def put_bytes(self, key: str, data: bytes) -> None:
        self._ensure_bucket()
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentLength=len(data))

    def get_bytes(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def remove(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


storage = Storage()
