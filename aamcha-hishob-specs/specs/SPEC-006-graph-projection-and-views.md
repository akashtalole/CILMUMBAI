# SPEC-006: Graph projection and named views

| | |
|---|---|
| Status | In progress: AC1 to AC5 and AC7 pass on Neo4j 5.26; AC6 needs a Neptune instance |
| Milestone | M1 |
| Owner role | Graph engineer |
| Depends on | SPEC-003, SPEC-004 |
| ADRs | 0004 |
| Personas served | All |

## 1. Problem and outcome

The ledger is the record, but questions need traversal. Applications and agents also need a small set of trusted, tested queries rather than free-form Cypher.

When done, the graph is built from the ledger by a projector that can run incrementally or from empty, behind a repository layer that works on Neo4j and Neptune over Bolt, and five named views answer the common questions.

## 2. User stories

- As the API, I want named views with fixed shapes, so that answers are fast and consistent.
- As a graph engineer, I want to rebuild the graph from nothing, so that I can change engines safely.

## 3. Requirements

| Id | Requirement |
|---|---|
| R1 | The projector shall apply new ledger files to the graph in order, recording the last file applied. |
| R2 | The projector shall be able to drop the graph and rebuild it from the full ledger. |
| R3 | A superseded fact shall not appear as current in the graph; its history shall remain queryable. |
| R4 | Every node and relationship in the graph shall carry fact id, source sha256, page, tier and `quote_check`. |
| R5 | The repository layer shall expose these views: `trace_money(node_id)`, `who_is_responsible(asset_id, issue)`, `work_status(work_id)`, `ward_summary(ward)`, `gaps_for(node_id)`. |
| R6 | All queries shall use only the openCypher subset agreed for Neo4j and Neptune, verified by running the view tests on both. |
| R7 | Where a view finds no data for a hop, it shall return that hop as an explicit gap rather than omit it. |

## 4. Acceptance criteria

| Id | Given | When | Then | Verifies |
|---|---|---|---|---|
| AC1 | A graph built up to ledger file N | File N+1 is projected | Only its facts are applied and the watermark moves to N+1 | R1 |
| AC2 | A populated graph | It is dropped and rebuilt | Node and edge counts and a hash of sorted fact ids match | R2 |
| AC3 | A work whose due date was superseded | `work_status` is called | It returns the current due date and a history with the earlier one | R3 |
| AC4 | Any node returned by any view | Its properties are inspected | Fact id, source, page, tier and `quote_check` are present | R4 |
| AC5 | A road with a tender, award and contractor in the ledger | `trace_money` is called | It returns tender, award, contract and contractor in order, each with sources | R5 |
| AC6 | The view test suite | It runs against Neo4j and against Neptune (or its local emulation if unavailable) | Both pass | R6 |
| AC7 | A work with a tender but no budget head | `trace_money` is called | The budget hop is returned as a gap with the record that would fill it | R7 |

## 5. Interfaces and data contracts

```python
class GraphStore(Protocol):
    def apply(self, ledger_files: Iterable[Path]) -> Watermark: ...
    def rebuild(self, ledger_root: str) -> RebuildReport: ...
    def view(self, name: str, **params) -> ViewResult: ...

@dataclass
class ViewResult:
    rows: list[dict]          # each item carries fact_id, source, page, tier
    gaps: list[Gap]           # {hop, record_needed, holder}
    query_ms: int
```

## 6. Non-functional requirements

- Each named view returns in under 300 ms on the demo ward.
- Rebuilding a ward's graph from its ledger takes under five minutes.

## 7. Constitution

| Article | How this spec upholds it |
|---|---|
| C1 | R4: provenance on every element |
| C9 | R2: rebuild from ledger |
| C12 | Named views instead of free-form queries |

## 8. Out of scope

Text and vector search (SPEC-017). Graph algorithms. HydraDB trial (tracked under ADR 0004, run against this suite).

## 9. Design notes

- Batch writes with `UNWIND`. Avoid vendor procedures. Precompute derived dates in the loader so queries compare plain values.
- Neptune testing: run against a small development instance in the nightly job; if none is available at M1, run on Neo4j only and record the gap.

## 10. Tasks

| Id | Task | Size | Depends on | Verifies | State |
|---|---|---|---|---|---|
| T1 | Repository layer and Bolt connection handling | M | | | Done |
| T2 | Incremental projector with watermark | M | T1, SPEC-003/T1 | AC1, AC4 | Done |
| T3 | Rebuild and comparison report | S | T2 | AC2 | Done |
| T4 | Supersession handling and history | M | T2 | AC3 | Done |
| T5 | `trace_money` with gaps | M | T2 | AC5, AC7 | Done |
| T6 | `who_is_responsible`, `work_status`, `ward_summary`, `gaps_for` | L | T2 | AC4 | Done |
| T7 | Run view suite on Neptune in nightly job | M | T6 | AC6 | Pending: no Neptune instance |

## Change log

| Date | Change |
|---|---|
| 16 Nov 2026 | Implemented in `app/src/hishob/graphstore/` with migration `006_graphstore.sql`; tests in `app/tests/integration/test_spec006_*.py`, run against Neo4j Community 5.26 locally and in CI. |

### Decisions made while building

- **Shape of the graph.** Every node has the label `Node` plus its ontology label, a unique `id`, its current properties and the provenance of the fact that last changed it. Each property's own provenance is stored as `_prov_<property>` (JSON), so a tender's cost and its reference number can cite different documents (SPEC-003/R7).
- **History.** Every fact is also a `Fact` node, linked from its subject by `HAS_FACT` and to the facts it replaced by `SUPERSEDES`. `work_status` reads due-date history from these.
- **What has been applied.** A Postgres table (`graphstore.applied`) records ledger files already in the graph; `apply` takes the rest in load order. `rebuild` empties the graph and applies everything, and the fingerprint (counts and a hash of fact ids) is compared.
- **Labels and relationship types** are checked against the ontology before they are written into a query.
- **Speed on the test graph:** median 4 to 28 ms per view.
- **AC6.** The suite passes on Neo4j. A test checks no vendor procedures (`apoc.`, `gds.`) or subqueries are used. Running it on Neptune waits for an instance (SPEC-030).
