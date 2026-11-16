# Ingest rubric (starter; tune after the first real batches)

- `/mnt/session/outputs/facts.jsonl` exists; every line is one JSON object with `kind` of `node`, `edge` or `note`.
- Every node and edge has `source`, `page`, a non-empty `quote`, `tier` and `confidence`, and `source` is the file name of a document in `/mnt/session/uploads/corpus/` without its extension.
- Every node `label` and edge `type` appears in `/mnt/session/uploads/schema/reference.md`, and every edge joins labels the reference allows.
- Every edge's `from` and `to` ids appear as node ids in `facts.jsonl` or in `/mnt/session/uploads/entities.jsonl`.
- Amounts are integers in rupees and dates are `YYYY-MM-DD`.
- `/mnt/session/outputs/report.md` has one row for every file in `/mnt/session/uploads/corpus/`, marked covered or not covered, with a reason for each one not covered.
- Each covered document was checked by a Fact verifier, and no record it rejected appears in `facts.jsonl`.
- `/mnt/session/outputs/review.jsonl` exists and holds every match the Entity resolver marked `unsure`.
- No two organisations were merged without a matching registration number, tax id or tender id, and no two people were merged.
