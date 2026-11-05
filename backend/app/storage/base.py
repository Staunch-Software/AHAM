import hashlib
import hmac
import time
from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings


class StorageBackend(Protocol):
    """Replaceable photo storage. Local filesystem now; an S3 backend can implement this later."""

    def part_size(self, upload_id: str) -> int: ...
    def append_part(self, upload_id: str, offset: int, data: bytes) -> int: ...
    def read_part(self, upload_id: str) -> bytes: ...
    def part_sha256(self, upload_id: str) -> tuple[str, int]: ...
    def finalize(self, upload_id: str, key: str) -> None: ...
    def put(self, key: str, data: bytes) -> None: ...
    def read(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> None: ...
    def discard_part(self, upload_id: str) -> None: ...


@lru_cache
def get_storage() -> StorageBackend:
    s = get_settings()
    if s.storage_backend == "local":
        from app.storage.local import LocalFileStorage

        return LocalFileStorage(s.storage_root)
    raise RuntimeError(f"Unsupported STORAGE_BACKEND: {s.storage_backend}")


def _sig(photo_id: str, variant: str, exp: int) -> str:
    key = get_settings().file_url_secret.encode()
    return hmac.new(key, f"{photo_id}.{variant}.{exp}".encode(), hashlib.sha256).hexdigest()


def sign_file_url(photo_id: str, variant: str = "original") -> str:
    """Short-lived URL. Minted only after the caller was authorized for the photo."""
    exp = int(time.time()) + get_settings().file_url_ttl_seconds
    return f"/api/v1/files/{photo_id}?variant={variant}&exp={exp}&sig={_sig(photo_id, variant, exp)}"


def verify_file_sig(photo_id: str, variant: str, exp: int, sig: str) -> bool:
    return exp >= time.time() and hmac.compare_digest(sig, _sig(photo_id, variant, exp))
