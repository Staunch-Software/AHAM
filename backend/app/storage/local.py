import hashlib
import os
from pathlib import Path


class LocalFileStorage:
    """Files live under `root` (never served statically). Keys are validated to stay inside root."""

    def __init__(self, root: str):
        self.root = Path(root).resolve()
        (self.root / "_incoming").mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root not in p.parents:
            raise ValueError("invalid storage key")
        return p

    def _part(self, upload_id: str) -> Path:
        if not upload_id.replace("-", "").isalnum():
            raise ValueError("invalid upload id")
        return self.root / "_incoming" / f"{upload_id}.part"

    def part_size(self, upload_id: str) -> int:
        p = self._part(upload_id)
        return p.stat().st_size if p.exists() else 0

    def append_part(self, upload_id: str, offset: int, data: bytes) -> int:
        """Append at `offset`; offset must equal current size (resumable, gap-free)."""
        p = self._part(upload_id)
        size = self.part_size(upload_id)
        if offset != size:
            raise ValueError(f"offset mismatch: have {size}")
        with open(p, "ab") as f:
            f.write(data)
        return size + len(data)

    def read_part(self, upload_id: str) -> bytes:
        return self._part(upload_id).read_bytes()

    def part_sha256(self, upload_id: str) -> tuple[str, int]:
        h, n = hashlib.sha256(), 0
        with open(self._part(upload_id), "rb") as f:
            while chunk := f.read(1 << 20):
                h.update(chunk)
                n += len(chunk)
        return h.hexdigest(), n

    def finalize(self, upload_id: str, key: str) -> None:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(self._part(upload_id), dest)

    def put(self, key: str, data: bytes) -> None:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def discard_part(self, upload_id: str) -> None:
        self._part(upload_id).unlink(missing_ok=True)
