import stat

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from hishob.archive.storage import LocalStore, S3Store, create_archive_bucket


def test_local_store_never_overwrites(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = LocalStore(tmp_path)
    assert store.put_new("source/bmc/2026/abc.pdf", b"first", "application/pdf") is True
    assert store.put_new("source/bmc/2026/abc.pdf", b"second", "application/pdf") is False
    assert store.get("source/bmc/2026/abc.pdf") == b"first"
    mode = (tmp_path / "source/bmc/2026/abc.pdf").stat().st_mode
    assert not mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)


def test_local_store_refuses_keys_outside_its_root(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        LocalStore(tmp_path).put_new("../escape.txt", b"x", "text/plain")


@mock_aws
def test_s3_store_never_overwrites_and_locked_versions_cannot_be_deleted() -> None:
    s3 = boto3.client("s3", region_name="ap-south-1")
    create_archive_bucket(s3, "hishob-archive-test", "ap-south-1")
    store = S3Store(s3, "hishob-archive-test")
    assert store.put_new("k.pdf", b"first", "application/pdf") is True
    assert store.put_new("k.pdf", b"second", "application/pdf") is False
    version = s3.head_object(Bucket="hishob-archive-test", Key="k.pdf")["VersionId"]
    with pytest.raises(ClientError) as error:
        s3.delete_object(Bucket="hishob-archive-test", Key="k.pdf", VersionId=version)
    assert error.value.response["Error"]["Code"] == "AccessDenied"
    assert store.get("k.pdf") == b"first"
    assert store.exists("k.pdf") and not store.exists("missing.pdf")
