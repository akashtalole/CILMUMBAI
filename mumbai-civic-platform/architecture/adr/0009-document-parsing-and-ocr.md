# ADR 0009: Text layer first, Claude vision for scans, Tesseract to pre-screen

**Status:** Accepted, pending a test on scanned Marathi papers · 15 November 2026

## Context

Sources are PDFs: some with a text layer, some scanned, many in Marathi, many with tables (budget books, bills of quantity). The quote check needs page-level text.

## Options

| Option | For | Against |
|---|---|---|
| PDF text layer (PyMuPDF) | Free, exact, fast | Only works when a text layer exists; table structure is lost |
| Amazon Textract | Managed; good at English forms and tables | I could not confirm that it reads Devanagari; per-page cost |
| Tesseract with Marathi and Hindi models | Open, runs anywhere, handles Devanagari | Weaker on poor scans and tables |
| **Claude reading page images** | Reads Devanagari and tables; can extract facts in the same pass | Token cost per page; output must be checked |
| Open layout models (for example docTR, PaddleOCR) on our own compute | No per-page fee | Operations; uneven Indic support |

## Decision

1. Use the text layer when present.
2. For scanned pages, send the page image to Claude for transcription and extraction together.
3. Run Tesseract on scanned pages as a cheap independent reading. Where the quote from step 2 does not appear in either the text layer or the Tesseract output, mark the fact `scan_unchecked` so a person can review it.
4. Use Textract only if a test shows it helps on English tables.

## Consequences

- Scanned Marathi pages are the most expensive and least certain input. Their facts carry a visible mark until reviewed.
- Budget tables are reconciled arithmetically against printed totals regardless of how they were read.

## To confirm

Textract's language list; accuracy of each route on twenty scanned committee pages.
