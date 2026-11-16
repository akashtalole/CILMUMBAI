# Aamcha Hishob: spec-driven development plan

How to build the final solution, [Aamcha Hishob](../mumbai-civic-platform/README.md), one specification at a time.

## Why spec-driven

Most of this platform will be written with AI coding agents, and most of its risk is in getting a fact, a citation or a permission wrong. Both are reasons to write down, before any code, exactly what each part must do and how we will know it does it. In this plan:

- **The spec is the source of truth.** Code, tests and agent prompts are derived from it. When they disagree, the spec is fixed first, then the code.
- **Every requirement is testable.** Requirements are written so that a test can pass or fail against them, and every acceptance criterion maps to a test.
- **Principles are enforced, not hoped for.** A short constitution lists what may never be broken (no fact without a source, no agent writes to the graph, and so on). Every spec names the articles it touches and how it upholds them.
- **Small, ordered slices.** Each spec is a vertical piece that can be built, tested and demonstrated on its own, in dependency order.

## Files

| File | Contents |
|---|---|
| [00-constitution.md](00-constitution.md) | Twelve non-negotiable principles, each with how it is checked |
| [01-process.md](01-process.md) | The workflow from idea to release, definitions of ready and done, how Claude Code and reviewers take part, change control |
| [02-spec-index.md](02-spec-index.md) | Every spec, its milestone, dependencies and status; the dependency graph; target code layout |
| [03-milestones.md](03-milestones.md) | What each milestone delivers, its exit criteria and the demo that proves it |
| [specs/](specs/) | The specifications. The first thirteen are written in full. |
| [templates/](templates/) | The spec template and the task card used in every spec |

## The first thirteen specs

These deliver the foundations and the hackathon slice. Later specs are listed in the index with a one-line scope and are written when their milestone approaches.

| Spec | Title | Milestone |
|---|---|---|
| [SPEC-001](specs/SPEC-001-document-archive.md) | Document archive and registry | M0 |
| [SPEC-002](specs/SPEC-002-ontology-and-schema.md) | Ontology, shapes and generated schema | M0 |
| [SPEC-003](specs/SPEC-003-facts-ledger-and-loader.md) | Facts ledger and loader | M0 |
| [SPEC-004](specs/SPEC-004-place-spine.md) | Place spine | M0 |
| [SPEC-005](specs/SPEC-005-intake-desk.md) | Intake desk | M0 |
| [SPEC-006](specs/SPEC-006-graph-projection-and-views.md) | Graph projection and named views | M1 |
| [SPEC-007](specs/SPEC-007-query-api.md) | Query API, access tiers and citation check | M1 |
| [SPEC-008](specs/SPEC-008-citizen-desk.md) | Citizen desk | M1 |
| [SPEC-009](specs/SPEC-009-workflow-engine.md) | Workflow engine and human gates | M1 |
| [SPEC-010](specs/SPEC-010-street-alerts.md) | Street alerts | M1 |
| [SPEC-011](specs/SPEC-011-audit-desk-and-release.md) | Audit desk and release | M1 |
| [SPEC-012](specs/SPEC-012-evaluation-and-promotion-gate.md) | Evaluation harness and promotion gate | M1 |
| [SPEC-013](specs/SPEC-013-aws-lean-infrastructure.md) | AWS infrastructure, lean profile | M2 |

## How this relates to the other folders

| Folder | Role |
|---|---|
| [../mumbai-civic-platform/](../mumbai-civic-platform/) | What to build and why: the product, data, ontology, layers and personas |
| [../mumbai-civic-platform/architecture/](../mumbai-civic-platform/architecture/) | How it is hosted and the decisions behind it. Specs cite these ADRs. |
| [../mumbai-civic-graph/managed-agents/](../mumbai-civic-graph/managed-agents/) | Starter code. Specs 005, 008, 009 and 011 turn it into tested components. |
| This folder | The order of work, the contract for each piece, and how each is verified |

## Status

All specs are **Draft**. None has been reviewed by a second person, and no implementation exists beyond the starter code. The first step in [01-process.md](01-process.md) is to review SPEC-001 to SPEC-005 together and move them to **Ready**.
