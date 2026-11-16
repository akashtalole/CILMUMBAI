# Process

## 1. The workflow

```
  idea or need
      │
      ▼
 1 SPECIFY   write spec.md from the template: problem, stories, requirements, acceptance criteria
      │
      ▼
 2 CLARIFY   list open questions; answer them or mark them as assumptions with an owner
      │
      ▼
 3 REVIEW    a second engineer and the domain or legal owner review → status Ready
      │
      ▼
 4 PLAN      design notes in the spec: interfaces, data contracts, choices, risks
      │
      ▼
 5 TASKS     break into task cards, each ≤ 1 day, each verifying named requirements
      │
      ▼
 6 TEST      write the tests for the acceptance criteria first; they fail
      │
      ▼
 7 BUILD     implement task by task (people or Claude Code), smallest change that passes
      │
      ▼
 8 VERIFY    CI: unit, contract, integration, constitution checks, evaluation gate
      │
      ▼
 9 DEMO      show the acceptance criteria working to the spec's owner
      │
      ▼
10 RELEASE   merge, deploy to staging, promote → status Done; update the index
```

A spec moves through these statuses: **Draft → Ready → In progress → Done**, or **Superseded** when replaced. Only Ready specs may be built.

## 2. Writing requirements

Requirements use the EARS patterns so each one is testable:

| Pattern | Form | Example |
|---|---|---|
| Ubiquitous | The system shall … | The loader shall record the extractor version on every fact. |
| Event | When …, the system shall … | When a record's quote is not found on its page, the loader shall write it to the held file. |
| State | While …, the system shall … | While a workflow is paused for review, the system shall not publish its outputs. |
| Unwanted | If …, then the system shall … | If the caller has no tier, then the API shall treat the caller as public. |
| Optional | Where …, the system shall … | Where a page has no text layer, the loader shall mark the fact `scan_unchecked`. |

Each requirement has an id (`R1`, `R2`, …) unique within its spec. Across the project it is written `SPEC-003/R4`.

Acceptance criteria use **Given / When / Then**, have ids (`AC1`, …), and name the requirements they verify. Each becomes at least one automated test, named after it (`test_spec003_ac2_…`).

## 3. Definitions

### Definition of ready (spec)

- Problem, stories and scope are written; out-of-scope is explicit.
- Every requirement is testable and has at least one acceptance criterion.
- Constitution articles touched are listed with how each is upheld.
- Interfaces and data contracts are concrete enough to write a contract test.
- Dependencies are Done or have a stub contract.
- Open questions are answered or recorded as assumptions with an owner.
- Reviewed by a second engineer, and by the lawyer if C5 or C6 is touched, or the language reviewer if C10 is touched.

### Definition of done (spec)

- All acceptance criteria pass as automated tests in CI.
- Constitution checks pass; any manual check is recorded in the pull request.
- Evaluation gate passes where the spec changes behaviour (C11).
- Documentation updated: the spec's status, the index, and any user-facing text in all three languages.
- Demonstrated to the spec's owner.
- No open task cards.

## 4. Traceability

```
Constitution article ─► Spec requirement (SPEC-nnn/Rn) ─► Acceptance criterion (ACn)
                                   │                               │
                                   ▼                               ▼
                             Task card (Tn) ──► Pull request ──► Test (test_specnnn_acn_*)
```

- Commit messages and pull request titles start with the task id: `SPEC-003/T4: quote check for text-layer pages`.
- A CI job lists every acceptance criterion in Ready or In-progress specs and fails if one has no test with its name once the spec is marked Done.
- The index shows, per spec, how many acceptance criteria have passing tests.

## 5. Building with Claude Code

Claude Code works well from specs because the spec carries the context a fresh session would otherwise lack. The rules:

1. **One task card per session.** Give it the spec file and the task id. It reads the spec, the constitution and the files the card names.
2. **Tests first.** It writes or updates the tests for the acceptance criteria the card verifies, runs them to see them fail, then implements.
3. **Stay inside the card.** If the card turns out wrong or the spec is ambiguous, it stops and proposes a spec change instead of improvising.
4. **No new components** without an ADR (C12).
5. **A person reviews every pull request.** For C5, C6 or C7 changes, the named reviewer must approve.

A starting instruction for the implementation repository's `CLAUDE.md`:

```markdown
This repository is built from specs in aamcha-hishob-specs/.
- Read 00-constitution.md before any change. Never break an article.
- Work on one task card at a time. Read its spec in full first.
- Write or update tests named after the acceptance criteria before code.
- If the spec is unclear or wrong, stop and propose a change to the spec.
- Do not add services, stores or frameworks without an ADR.
- Commit messages start with the task id, e.g. SPEC-003/T4.
```

Agent prompts and rubrics are specified the same way: the spec states what the agent must and must not do, and the evaluation sets in SPEC-012 are its acceptance tests.

## 6. Branching, review and CI

| Step | Rule |
|---|---|
| Branch | One branch per task card or small group of cards in one spec |
| Pull request | Links the spec and task ids; lists the acceptance criteria now passing |
| Review | One engineer always; lawyer for C5/C6; language reviewer for C10; data owner for ontology changes |
| CI on pull request | Lint and types; unit tests; contract tests; constitution checks; docs build; evaluation gate for behaviour changes |
| Merge | Squash; status of the spec updated in the same PR when it changes |
| Deploy | Main deploys to staging; promotion to production is a manual approval after the evaluation report |

## 7. Changing a spec

- Small clarifications that do not change behaviour: edit, note in the spec's change log.
- Behaviour changes: a pull request to the spec, reviewed like code, before the code changes.
- A spec that is replaced is marked **Superseded by SPEC-nnn** and kept.
- Constitution changes follow the rule in [00-constitution.md](00-constitution.md).

## 8. Cadence

| When | What |
|---|---|
| Daily, during a milestone | Pick task cards; push; review |
| Weekly | Spec review: move Drafts to Ready for the next milestone; check the index |
| End of milestone | Demo against exit criteria in [03-milestones.md](03-milestones.md); retro; update the plan |
