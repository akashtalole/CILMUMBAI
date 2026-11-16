"""Document archive and registry (SPEC-001)."""

from hishob.archive.fetch import FetchFailure
from hishob.archive.service import Archive, DocumentRef, NotADocumentError

__all__ = ["Archive", "DocumentRef", "FetchFailure", "NotADocumentError"]
