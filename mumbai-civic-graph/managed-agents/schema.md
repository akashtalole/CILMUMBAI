# Record format for extracted facts

One JSON object per line. Two kinds of record.

## Node

```json
{"kind": "node", "label": "Tender", "id": "tender:2026_MCGM_1303610_1",
 "props": {"ref_no": "…", "estimated_cost": 125000000, "published_on": "2026-08-11"},
 "source_file": "ETH_8000113000_110826.pdf", "page": 3,
 "quote": "exact words from that page", "confidence": 0.9, "tier": "official"}
```

## Edge

```json
{"kind": "edge", "type": "FOR_WORK", "from": "tender:2026_MCGM_1303610_1", "to": "work:…",
 "props": {"valid_from": "2026-08-11"},
 "source_file": "…", "page": 3, "quote": "…", "confidence": 0.8, "tier": "official"}
```

## Rules

- `page` and `quote` are required on every record. The quote is verbatim, in the original script.
- `tier` is `official` for government documents, `reported` for news, `citizen` for resident reports.
- Ids are `<type>:<stable key>`. Use the official number where one exists (Mahatenders tender id, BMC bid number, budget code). Otherwise use a lowercase slug of the name plus the ward.
- Amounts are rupees as integers. Dates are ISO `YYYY-MM-DD`.
- Names: keep `name` as written; add `name_en` when the original is Marathi or Hindi.

## Node labels

`FiscalYear`, `BudgetHead`, `Allocation`, `Tender`, `Corrigendum`, `Bid`, `Award`, `Contract`,
`Payment`, `Penalty`, `Blacklisting`, `Work`, `Milestone`, `DefectLiabilityPeriod`, `Asset`,
`AdminWard`, `ElectoralWard`, `Agency`, `Department`, `Post`, `Person`, `Contractor`, `Company`,
`Director`, `Promise`, `Complaint`, `SourceDocument`

## Edge types

`PARENT_OF`, `UNDER`, `FOR_YEAR`, `FUNDED_BY`, `IMPROVES`, `FOR_WORK`, `ON`, `SUBMITTED`, `OF`,
`TO`, `FROM_AWARD`, `PARTY_TO`, `UNDER_CONTRACT`, `IMPOSED_ON`, `AMENDS`, `RETENDER_OF`,
`HAS_DLP`, `LOCATED_IN`, `WITHIN`, `OWNS`, `PART_OF`, `ISSUED_BY`, `IN`, `COVERS`, `REPORTS_TO`,
`HOLDS`, `REPRESENTS`, `MADE_BY`, `FULFILLED_BY`, `ABOUT`

Anything that fits none of these goes in a record with `"kind": "note"` and a `text` field.
