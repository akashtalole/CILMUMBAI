"""Object storage with no way to overwrite or delete (SPEC-001/R4).

Two backends: a local directory for laptops, and S3 for the service.
On S3 the archive bucket also has versioning and object lock, so even a
client that bypasses this module cannot remove a stored version.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol


class ObjectStore(Protocol):
    def put_new(self, key: str, data: bytes, content_type: str) -> bool:
        """Store data under key if the key is free. Return False, changing nothing, if it exists."""

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def list(self, prefix: str) -> list[str]:
        """Keys under a prefix, sorted."""


class LocalStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError(f"key escapes the store: {key}")
        return path

    def put_new(self, key: str, data: bytes, content_type: str) -> bool:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb") as handle:
                handle.write(data)
        except FileExistsError:
            return False
        os.chmod(path, 0o444)
        return True

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def list(self, prefix: str) -> list[str]:
        root = self.root.resolve()
        base = self._path(prefix) if prefix else root
        if not base.exists():
            return []
        files = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()]
        return sorted(p.relative_to(root).as_posix() for p in files)


class S3Store:
    def __init__(self, client: Any, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    def put_new(self, key: str, data: bytes, content_type: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type, IfNoneMatch="*")
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in {"PreconditionFailed", "412"}:
                return False
            raise
        return True

    def get(self, key: str) -> bytes:
        body: bytes = self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        return body

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise
        return True

    def list(self, prefix: str) -> list[str]:
        keys: list[str] = []
        for page in self.client.get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=prefix):
            keys.extend(item["Key"] for item in page.get("Contents", []))
        return sorted(keys)


def create_archive_bucket(client: Any, bucket: str, region: str, retention_years: int = 10) -> None:
    """Create a bucket with versioning and object lock in governance mode. Used by tests and set-up scripts;
    production buckets are created by Terraform (SPEC-013)."""
    client.create_bucket(
        Bucket=bucket,
        CreateBucketConfiguration={"LocationConstraint": region},
        ObjectLockEnabledForBucket=True,
    )
    client.put_object_lock_configuration(
        Bucket=bucket,
        ObjectLockConfiguration={
            "ObjectLockEnabled": "Enabled",
            "Rule": {"DefaultRetention": {"Mode": "GOVERNANCE", "Years": retention_years}},
        },
    )
