import hashlib
from typing import Any
import boto3
from botocore.exceptions import ClientError
from app.core.config import Settings


class S3Storage:
    """S3-compatible storage backend (AWS S3, MinIO, Cloudflare R2, Wasabi)."""

    def __init__(self, cfg: Settings):
        self.bucket = cfg.s3_bucket_name
        kw: dict[str, Any] = {"region_name": cfg.s3_region}
        if cfg.aws_access_key_id and cfg.aws_secret_access_key:
            kw["aws_access_key_id"] = cfg.aws_access_key_id
            kw["aws_secret_access_key"] = cfg.aws_secret_access_key
        if cfg.s3_endpoint_url:
            kw["endpoint_url"] = cfg.s3_endpoint_url
            kw["use_ssl"] = cfg.s3_use_ssl
        self.client = boto3.client("s3", **kw)
        self._parts: dict[str, bytearray] = {}

    def part_size(self, upload_id: str) -> int:
        return len(self._parts.get(upload_id, b""))

    def append_part(self, upload_id: str, offset: int, data: bytes) -> int:
        buf = self._parts.setdefault(upload_id, bytearray())
        if offset != len(buf):
            raise ValueError(f"offset mismatch: have {len(buf)}")
        buf.extend(data)
        return len(buf)

    def read_part(self, upload_id: str) -> bytes:
        return bytes(self._parts.get(upload_id, b""))

    def part_sha256(self, upload_id: str) -> tuple[str, int]:
        data = self.read_part(upload_id)
        return hashlib.sha256(data).hexdigest(), len(data)

    def finalize(self, upload_id: str, key: str) -> None:
        data = self._parts.pop(upload_id, None)
        if data is None:
            raise ValueError("upload not found")
        self.put(key, bytes(data))

    def put(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)

    def read(self, key: str) -> bytes:
        resp = self.client.get_object(Bucket=self.bucket, Key=key)
        return resp["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", 404):
                return False
            raise

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def discard_part(self, upload_id: str) -> None:
        self._parts.pop(upload_id, None)
