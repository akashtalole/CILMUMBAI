# Constitution

Twelve principles that every spec, every change and every agent must uphold. A spec may not override them. Changing one needs the agreement of the product lead, the lawyer and one engineer, and a written reason in [the change log](#change-log).

Each article states how it is checked. If an article cannot be checked automatically, the check is named in the definition of done.

| # | Principle | Checked by |
|---|---|---|
| C1 | **No source, no fact.** Every node and relationship carries a source document, page, verbatim quote, tier and confidence. | Loader rejects records without them (SPEC-003); schema test |
| C2 | **Quotes are verified in code.** A fact whose quote does not appear on its cited page is held, not loaded. Scanned pages without a text layer are loaded only with a visible `scan_unchecked` mark. | Loader quote check and its tests (SPEC-003) |
| C3 | **No answer without citations.** Every amount, date, identifier and proper name in an answer must appear in a cited fact; otherwise the system says the records do not show it. | Citation checker (SPEC-007); question evaluation set (SPEC-012) |
| C4 | **Agents do not write or publish.** No agent has a tool that writes to a store, sends a message to the public, or publishes. Agents produce files; code validates and loads them; people release. | Agent definition lint in CI (SPEC-012); tool inventory review |
| C5 | **Records, not verdicts.** Findings describe what records show. No content states or implies wrongdoing by a named party. Officials appear by post. | Banned-word check; Challenger review; lawyer release (SPEC-011) |
| C6 | **People release what names a party.** Anything that names a contractor, developer, official post or elected representative in a finding passes a human release step. | Workflow gate cannot be bypassed (SPEC-009) |
| C7 | **No private individuals.** The platform stores no names, phone numbers, addresses, faces or number plates of private individuals. Residents' input is redacted before storage and before any model call. | Redaction tests; storage scans (SPEC-008, later SPEC-019) |
| C8 | **Access tiers are enforced in the query layer.** Every read carries a tier; nothing returns data above the caller's tier, whichever path it takes. | Tier tests on every endpoint and tool (SPEC-007) |
| C9 | **The archive and ledger are the record.** Source documents are immutable; facts are append-only; every other store can be dropped and rebuilt. | Rebuild test (SPEC-003, SPEC-006) |
| C10 | **Three languages as equals.** Marathi, Hindi and English are tested separately. A change that improves one and worsens another does not ship. | Evaluation reported by language (SPEC-012) |
| C11 | **Every behaviour change is evaluated.** Changes to prompts, agents, rules, ontology or retrieval pass the evaluation gate before production. | Promotion gate in CI (SPEC-012) |
| C12 | **Simplest thing that meets the spec.** No new service, store or framework without an ADR. Prefer deterministic code to a model call, and a model call to an agent. | Design review; ADR required for new components |

## Applying the constitution in a spec

Each spec has a section **Constitution** that lists the articles it touches and, for each, the requirement or test that upholds it. A reviewer rejects a spec that touches an article without saying how.

## Change log

| Date | Change | Agreed by |
|---|---|---|
| 16 Nov 2026 | First version | Draft, not yet agreed |
