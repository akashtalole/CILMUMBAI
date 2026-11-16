"""Recognise what kind of document a set of bytes is, and refuse things that are not documents."""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class MediaType:
    mime: str
    extension: str


PDF = MediaType("application/pdf", "pdf")
PNG = MediaType("image/png", "png")
JPEG = MediaType("image/jpeg", "jpg")
TIFF = MediaType("image/tiff", "tif")
XLSX = MediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx")
DOCX = MediaType("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx")
CSV = MediaType("text/csv", "csv")
JSON = MediaType("application/json", "json")
GEOJSON = MediaType("application/geo+json", "geojson")
TEXT = MediaType("text/plain", "txt")

_HTML_STARTS = ("<!doctype html", "<html", "<head", "<body", "<?xml")


def sniff(data: bytes, filename: str | None = None, content_type: str | None = None) -> MediaType | None:
    """Return the media type, or None when the bytes are empty or not a document (for example an HTML page)."""
    if not data:
        return None
    if data.startswith(b"%PDF-"):
        return PDF
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return PNG
    if data.startswith(b"\xff\xd8\xff"):
        return JPEG
    if data.startswith((b"II*\x00", b"MM\x00*")):
        return TIFF
    name = (filename or "").lower()
    if data.startswith(b"PK\x03\x04"):
        if name.endswith(".xlsx"):
            return XLSX
        if name.endswith(".docx"):
            return DOCX
        return None
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    head = text.lstrip()[:200].lower()
    if head.startswith(_HTML_STARTS) or "html" in (content_type or "").lower():
        return None
    if head.startswith(("{", "[")):
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
        if parsed is not None:
            if isinstance(parsed, dict) and parsed.get("type") in {"FeatureCollection", "Feature"}:
                return GEOJSON
            return JSON
    if name.endswith(".csv") or "csv" in (content_type or "").lower():
        return CSV
    return TEXT
