"""Acceptance tests for SPEC-001: document archive and registry."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import boto3
import httpx
import pytest
from moto import mock_aws

from hishob.archive import Archive, FetchFailure, NotADocumentError
from hishob.archive.events import SqsSink
from hishob.archive.fetch import Fetcher
from hishob.archive.registry import Registry
from hishob.archive.storage import LocalStore, S3Store, create_archive_bucket
from tests.conftest import FIXED_NOW, FIXTURES

pytestmark = pytest.mark.integration

TENDER = FIXTURES / "tender-en.pdf"
MIXED = FIXTURES / "tender-mixed.pdf"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _serving(body: bytes, content_type: str, status: int = 200) -> Fetcher:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(status, content=body, headers={"content-type": content_type})
    )
    return Fetcher(delay_s=0, transport=transport)


def _files_under(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file()]


# AC1 · R1, R3, R6 -----------------------------------------------------------------------------------------------


def test_spec001_ac1_file_is_stored_by_hash_with_a_full_registry_entry(make_archive, tmp_path) -> None:
    archive: Archive = make_archive()
    ref = archive.add_file(TENDER, publisher="bmc", licence="BMC public notice; quote with attribution")

    sha = _sha(TENDER)
    assert ref.created and ref.sha256 == sha
    assert ref.storage_key == f"source/bmc/2026/{sha}.pdf"
    assert (tmp_path / "archive" / ref.storage_key).read_bytes() == TENDER.read_bytes()

    row = archive.registry.get(sha)
    assert row is not None
    assert (row.publisher, row.media_type, row.extension) == ("bmc", "application/pdf", "pdf")
    assert row.size_bytes == TENDER.stat().st_size
    assert row.page_count == 2
    assert row.scripts == ["Latn"]
    assert row.licence.startswith("BMC public notice")
    assert row.first_seen_at == FIXED_NOW
    [origin] = archive.registry.origins(sha)
    assert origin.origin_kind == "file" and origin.origin_ref.endswith("tender-en.pdf")
    assert origin.fetched_at == FIXED_NOW


def test_spec001_ac1_rejects_bad_publisher_and_missing_licence(make_archive) -> None:
    archive: Archive = make_archive()
    with pytest.raises(ValueError):
        archive.add_file(TENDER, publisher="BMC Roads!", licence="x")
    with pytest.raises(ValueError):
        archive.add_file(TENDER, publisher="bmc", licence="  ")


# AC2 · R2 -------------------------------------------------------------------------------------------------------


def test_spec001_ac2_same_bytes_from_a_new_origin_are_stored_once(make_archive, sink, tmp_path) -> None:
    archive: Archive = make_archive(fetcher=_serving(TENDER.read_bytes(), "application/pdf"))
    first = archive.add_file(TENDER, publisher="bmc", licence="public")
    second = archive.add_url("https://portal.example.gov.in/tenders/ETH_0001.pdf", publisher="bmc", licence="public")

    assert isinstance(second, type(first))
    assert second.sha256 == first.sha256 and second.created is False
    assert len(_files_under(tmp_path / "archive")) == 1
    kinds = [o.origin_kind for o in archive.registry.origins(first.sha256)]
    assert kinds == ["file", "url"]
    assert len(sink.events) == 1  # nothing new was added the second time


def test_spec001_ac2_same_origin_twice_is_recorded_once(make_archive) -> None:
    archive: Archive = make_archive()
    archive.add_file(TENDER, publisher="bmc", licence="public")
    archive.add_file(TENDER, publisher="bmc", licence="public")
    assert len(archive.registry.origins(_sha(TENDER))) == 1


# AC3 · R4 -------------------------------------------------------------------------------------------------------


def test_spec001_ac3_archive_offers_no_way_to_change_or_remove_a_document() -> None:
    forbidden = ("delete", "remove", "overwrite", "replace", "update", "purge")
    names = [n for n in dir(Archive) if not n.startswith("__")]
    assert not [n for n in names if any(word in n.lower() for word in forbidden)]


def test_spec001_ac3_stored_bytes_survive_attempts_to_change_them(make_archive, tmp_path) -> None:
    archive: Archive = make_archive()
    ref = archive.add_file(TENDER, publisher="bmc", licence="public")
    store = LocalStore(tmp_path / "archive")
    assert store.put_new(ref.storage_key, b"tampered", "application/pdf") is False
    assert archive.open(ref.sha256).read() == TENDER.read_bytes()


@mock_aws
def test_spec001_ac3_on_s3_locked_versions_cannot_be_deleted(make_archive) -> None:
    s3 = boto3.client("s3", region_name="ap-south-1")
    create_archive_bucket(s3, "hishob-archive-test", "ap-south-1")
    s3.create_bucket(Bucket="hishob-data-test", CreateBucketConfiguration={"LocationConstraint": "ap-south-1"})
    archive: Archive = make_archive(sources=S3Store(s3, "hishob-archive-test"), data=S3Store(s3, "hishob-data-test"))
    ref = archive.add_file(TENDER, publisher="bmc", licence="public")

    version = s3.head_object(Bucket="hishob-archive-test", Key=ref.storage_key)["VersionId"]
    with pytest.raises(Exception, match="AccessDenied"):
        s3.delete_object(Bucket="hishob-archive-test", Key=ref.storage_key, VersionId=version)
    assert archive.open(ref.sha256).read() == TENDER.read_bytes()


# AC4 · R5 -------------------------------------------------------------------------------------------------------


def test_spec001_ac4_one_event_per_added_document(make_archive, sink) -> None:
    archive: Archive = make_archive()
    ref = archive.add_file(TENDER, publisher="bmc", licence="public")
    assert sink.events == [
        {"type": "archive.document_added", "sha256": ref.sha256, "publisher": "bmc", "at": FIXED_NOW.isoformat()}
    ]


@mock_aws
def test_spec001_ac4_events_reach_an_sqs_queue(conn, tmp_path) -> None:
    sqs = boto3.client("sqs", region_name="ap-south-1")
    queue = sqs.create_queue(QueueName="archive-events")["QueueUrl"]
    archive = Archive(Registry(conn), LocalStore(tmp_path / "a"), LocalStore(tmp_path / "d"), SqsSink(sqs, queue))
    ref = archive.add_file(TENDER, publisher="bmc", licence="public")

    [message] = sqs.receive_message(QueueUrl=queue, MaxNumberOfMessages=10)["Messages"]
    body = json.loads(message["Body"])
    assert body["type"] == "archive.document_added" and body["sha256"] == ref.sha256


# AC5 · R6, R7 ---------------------------------------------------------------------------------------------------


def test_spec001_ac5_html_error_page_is_recorded_as_a_failure(make_archive, sink) -> None:
    html = (FIXTURES / "error-page.html").read_bytes()
    archive: Archive = make_archive(fetcher=_serving(html, "text/html; charset=utf-8"))
    result = archive.add_url("https://portal.example.gov.in/tenders/list", publisher="mahatenders", licence="public")

    assert isinstance(result, FetchFailure) and result.reason == "not_a_document"
    [failure] = archive.registry.failures()
    assert failure.reason == "not_a_document" and failure.publisher == "mahatenders"
    assert archive.registry.conn.execute("SELECT count(*) FROM registry.documents").fetchone() == (0,)
    assert sink.events == []


def test_spec001_ac5_http_errors_are_recorded_as_failures(make_archive) -> None:
    archive: Archive = make_archive(fetcher=_serving(b"gone", "text/plain", status=404))
    result = archive.add_url("https://portal.example.gov.in/missing.pdf", publisher="bmc", licence="public")
    assert isinstance(result, FetchFailure) and result.reason == "http_404"
    assert [f.reason for f in archive.registry.failures()] == ["http_404"]


def test_spec001_ac5_a_document_fetched_by_url_is_archived(make_archive) -> None:
    archive: Archive = make_archive(fetcher=_serving(MIXED.read_bytes(), "application/pdf"))
    ref = archive.add_url("https://portal.example.gov.in/ETH_0002.pdf", publisher="bmc", licence="public")
    assert not isinstance(ref, FetchFailure) and ref.created
    [origin] = archive.registry.origins(ref.sha256)
    assert (origin.origin_kind, origin.origin_ref) == ("url", "https://portal.example.gov.in/ETH_0002.pdf")


# AC6 · R6, R8 ---------------------------------------------------------------------------------------------------


def test_spec001_ac6_uploads_keep_only_an_opaque_account_id(make_archive) -> None:
    archive: Archive = make_archive()
    photo = (FIXTURES / "site-board.png").read_bytes()
    ref = archive.add_upload(photo, filename="Sunita Patil 9820012345.png", account_id="acct_7f3k2m9q")

    assert ref.publisher == "contributor" and ref.media_type == "image/png"
    [origin] = archive.registry.origins(ref.sha256)
    assert origin.origin_kind == "upload" and origin.account_id == "acct_7f3k2m9q"
    assert origin.origin_ref.startswith("upload/")
    stored = json.dumps([str(v) for v in archive.registry.get(ref.sha256).__dict__.values()]) + origin.origin_ref
    assert "Sunita" not in stored and "9820012345" not in stored


@pytest.mark.parametrize("bad", ["sunita@example.com", "9820012345", "ab", "has space"])
def test_spec001_ac6_contact_details_are_refused_as_account_ids(make_archive, bad: str) -> None:
    archive: Archive = make_archive()
    with pytest.raises(ValueError):
        archive.add_upload(b"%PDF-1.7 x", filename="a.pdf", account_id=bad)


def test_spec001_ac6_uploads_that_are_not_documents_are_refused(make_archive) -> None:
    archive: Archive = make_archive()
    with pytest.raises(NotADocumentError):
        archive.add_upload(b"<html><body>hi</body></html>", filename="page.html", account_id="acct_7f3k2m9q")


# AC7 · R9 -------------------------------------------------------------------------------------------------------


def test_spec001_ac7_text_layer_pages_are_stored_and_scans_are_marked(make_archive) -> None:
    archive: Archive = make_archive()
    ref = archive.add_file(MIXED, publisher="bmc", licence="public")

    pages = archive.registry.pages(ref.sha256)
    assert [(p.page, p.has_text_layer) for p in pages] == [(1, True), (2, True), (3, True), (4, False)]
    assert "बृहन्मुंबई महानगरपालिका" in (archive.page_text(ref.sha256, 1) or "")
    assert "Rs. 1,15,50,000" in (archive.page_text(ref.sha256, 2) or "")
    assert archive.page_text(ref.sha256, 4) is None
    assert ref.scripts == ["Deva", "Latn"]
    with pytest.raises(KeyError):
        archive.page_text(ref.sha256, 5)
