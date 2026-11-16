"""Split a document into pages and extract the text layer where there is one."""

from __future__ import annotations

from dataclasses import dataclass

import pymupdf

from hishob.archive import media


@dataclass(frozen=True)
class Page:
    number: int
    text: str | None  # None when the page has no text layer (for example a scan)


@dataclass(frozen=True)
class Analysis:
    pages: list[Page]

    @property
    def page_count(self) -> int:
        return len(self.pages)


def analyse(data: bytes, kind: media.MediaType) -> Analysis:
    if kind == media.PDF:
        try:
            with pymupdf.open(stream=data, filetype="pdf") as doc:  # type: ignore[no-untyped-call]
                pages = []
                for index, page in enumerate(doc, start=1):
                    text = page.get_text()
                    pages.append(Page(index, text if text.strip() else None))
        except (pymupdf.FileDataError, RuntimeError, ValueError):
            # A damaged PDF is still archived as received, with no pages, so the record shows it was seen.
            return Analysis([])
        return Analysis(pages)
    if kind in (media.CSV, media.JSON, media.GEOJSON, media.TEXT):
        text = data.decode("utf-8-sig")
        return Analysis([Page(1, text if text.strip() else None)])
    # Images and office files: one page with no text layer until a later step reads them.
    return Analysis([Page(1, None)])
