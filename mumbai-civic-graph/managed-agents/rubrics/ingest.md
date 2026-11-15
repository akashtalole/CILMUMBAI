# Ingest rubric (starter; tune the criteria to your corpus)

- `/mnt/session/outputs/facts.jsonl` exists and every line is valid JSON with `kind` of `node` or `edge`.
- Every record has `source_file`, `page`, a non-empty `quote`, `confidence` and `tier`.
- Every `label` and edge `type` is one listed in `/mnt/session/uploads/schema.md`.
- Every edge's `from` and `to` ids appear as node ids in the file or in `/mnt/session/uploads/entities.jsonl`.
- Amounts are integers in rupees and dates are ISO `YYYY-MM-DD`.
- `/mnt/session/outputs/report.md` lists every file under `/mnt/session/uploads/corpus/` as covered or not covered, with a reason for each one not covered.
- Each covered document has a verdict file under `/workspace/verdicts/`, and no fact marked `reject` there appears in `facts.jsonl`.
- `/mnt/session/outputs/review.jsonl` exists and holds every entity match the resolver marked `unsure`.
- No two person nodes were merged without a matching official identifier.
