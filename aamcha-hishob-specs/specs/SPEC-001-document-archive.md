# SPEC-001: Document archive and registry

| | |
|---|---|
| Status | In progress: all acceptance criteria pass in CI; awaiting second review and demo (started 16 Nov 2026 at the product owner's request, before review) |
| Milestone | M0 |
| Owner role | Data engineer |
| Depends on | |
| ADRs | 0001, 0022 |
| Personas served | All, indirectly; reviewers and researchers directly |

## 1. Problem and outcome

Every fact on the platform must trace back to the exact document it came from, as it was when fetched. Portals change and remove files. Today the corpus is a folder of PDFs with no record of where or when each came from.

When done, every source document is stored once, unchanged, addressed by its content hash, with a registry entry recording publisher, origin URL, fetch time, language, page count and licence. Nothing can alter or delete an archived document.

## 2. User stories

- As a reviewer, I want to open the exact document and page behind a fact, so that I can check it.
- As a data engineer, I want to add documents from a URL, a local file or a person's upload, so that every source reaches the archive the same way.
- As a researcher, I want to know when each document was fetched and from where, so that I can cite it.

## 3. Requirements

| Id | Requirement |
|---|---|
| R1 | The archive shall store each document under a key derived from the SHA-256 of its bytes. |
| R2 | When a document whose hash already exists is added, the archive shall not store a second copy and shall add the new origin to the existing registry entry. |
| R3 | The registry shall record for each document: hash, publisher, origin URL or upload reference, fetched or received time, media type, size, page count, the scripts found in the text (for example Devanagari, Latin), and licence. |
| R4 | The archive shall not offer any operation that modifies or deletes a stored document. |
| R5 | When a document is added, the system shall emit an `archive.document_added` event carrying the hash and publisher. |
| R6 | The system shall accept documents from three routes: fetch by URL, local file, and upload by an authenticated contributor. |
| R7 | If a fetch fails or returns a non-document response, then the system shall record the failure with its reason and shall not create a registry entry. |
| R8 | Where a document is uploaded by a contributor, the registry shall record the contributor's account id and shall not record their name or contact details. |
| R9 | The system shall extract and store the text of each page that has a text layer, keyed by hash and page number. |

## 4. Acceptance criteria

| Id | Given | When | Then | Verifies |
|---|---|---|---|---|
| AC1 | An empty archive | A PDF is added from a local file | It is stored at `source/<publisher>/<yyyy>/<sha256>.pdf` and a registry row exists with all R3 fields | R1, R3, R6 |
| AC2 | A document already archived | The same bytes are added from a different URL | No new object is stored; the registry row lists both origins | R2 |
| AC3 | An archived document | Any client tries to overwrite or delete it | The operation is refused; the stored bytes are unchanged | R4 |
| AC4 | An archive with a subscriber to events | A document is added | One `archive.document_added` event with hash and publisher is emitted | R5 |
| AC5 | A URL that returns an HTML error page | It is fetched | A failure is recorded with reason `not_a_document`; no registry row is created | R6, R7 |
| AC6 | A contributor's upload | It is archived | The registry holds the account id and no name, phone or email | R6, R8 |
| AC7 | A PDF with a text layer on pages 1 to 3 and a scanned page 4 | It is archived | Text for pages 1 to 3 is stored; page 4 is recorded as `no_text_layer` | R9 |

## 5. Interfaces and data contracts

```python
class Archive(Protocol):
    def add_file(self, path: Path, publisher: str, licence: str) -> DocumentRef: ...
    def add_url(self, url: str, publisher: str, licence: str) -> DocumentRef | FetchFailure: ...
    def add_upload(self, data: bytes, filename: str, account_id: str) -> DocumentRef: ...
    def open(self, sha256: str) -> BinaryIO: ...
    def page_text(self, sha256: str, page: int) -> str | None: ...   # None when no text layer
```

Registry table `registry.documents`: `sha256 PK, publisher, media_type, extension, size_bytes, page_count, scripts text[], licence, storage_key, first_seen_at`.
Table `registry.origins`: `sha256, origin_kind (url|file|upload), origin_ref, fetched_at, account_id NULL`.
Table `registry.pages`: `sha256, page, has_text_layer, text_key`.

Event (JSON on the queue): `{"type": "archive.document_added", "sha256": "…", "publisher": "bmc", "at": "…"}`

Storage: S3-compatible bucket with versioning and object lock in governance mode (MinIO locally).

## 6. Non-functional requirements

- Adding a 20 MB PDF completes in under 10 seconds locally, excluding network fetch.
- Fetching identifies itself with a generic client name and waits at least 5 seconds between requests to the same host.
- Never bypasses logins or captchas; such pages are added by a person as files.

## 7. Constitution

| Article | How this spec upholds it |
|---|---|
| C1 | Provides the document and page that every fact cites |
| C7 | R8: contributor identity stored as account id only |
| C9 | R4: archive is immutable; object lock |

## 8. Out of scope

Scheduled collection and change detection (SPEC-014). OCR of scanned pages (SPEC-005). Redaction of residents' images (SPEC-019).

## 9. Design notes

- Record the scripts found in page text (ISO 15924 codes such as `Deva`, `Latn`) by counting characters in each Unicode block. Telling Marathi from Hindi is left to the intake desk, which reads the text.
- Text extraction with PyMuPDF. Store page text as separate objects under `parsed/<sha256>/page-<n>.txt` so the loader's quote check reads one page cheaply.
- Object lock in governance mode allows an administrator to remove a document only through a documented legal process, recorded outside the application.

## 10. Tasks

| Id | Task | Size | Depends on | Verifies | State |
|---|---|---|---|---|---|
| T1 | Create `app/` skeleton, tooling, Docker Compose with MinIO and Postgres | M | | | Done |
| T2 | Registry schema and migrations | S | T1 | AC1 | Done |
| T3 | `add_file` with hashing, storage key and registry write | M | T2 | AC1, AC2 | Done |
| T4 | Immutability: object lock configuration and refusal tests | S | T3 | AC3 | Done |
| T5 | Event emission | S | T3 | AC4 | Done |
| T6 | `add_url` with polite fetching and failure records | M | T3 | AC5 | Done |
| T7 | `add_upload` with account id only | S | T3 | AC6 | Done |
| T8 | Page text extraction and storage | M | T3 | AC7 | Done |
| T9 | Command line: `hishob archive add <path or url> --publisher --licence` | S | T3, T6 | | Done |

## 11. Open questions

| Question | Owner | Assumption until answered |
|---|---|---|
| Licence of BMC and Mahatenders documents for republishing | Lawyer | Store and quote; do not republish whole documents |
| Retention for residents' uploads | Product lead | Kept until the contributor deletes their account |

## Change log

| Date | Change |
|---|---|
| 16 Nov 2026 | Implemented in `app/src/hishob/archive/`. Tests: `app/tests/integration/test_spec001_*.py`. T1's Docker Compose file is written but not run in the build environment. |
| 16 Nov 2026 | R3 records scripts found instead of detected languages, since Marathi and Hindi share a script; registry columns updated to match. Status moved to In progress. |
