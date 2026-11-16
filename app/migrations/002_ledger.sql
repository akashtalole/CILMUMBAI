-- SPEC-003: index of the facts ledger. Derived from the ledger files on S3 and rebuildable from them.
CREATE SCHEMA IF NOT EXISTS ledger;

CREATE TABLE ledger.batches (
    batch_id         text PRIMARY KEY CHECK (batch_id ~ '^[A-Za-z0-9_-]{3,80}$'),
    extractor        text NOT NULL,
    ontology_version text NOT NULL,
    loaded_at        timestamptz NOT NULL,
    accepted         integer NOT NULL,
    held             integer NOT NULL,
    report_key       text NOT NULL
);

CREATE TABLE ledger.facts (
    fact_id    text PRIMARY KEY,
    identity   text NOT NULL,
    kind       text NOT NULL CHECK (kind IN ('node', 'edge')),
    name       text NOT NULL,          -- node label or edge type
    node_id    text,
    from_id    text,
    to_id      text,
    source     text NOT NULL,
    page       integer NOT NULL,
    batch_id   text NOT NULL REFERENCES ledger.batches (batch_id),
    file_key   text NOT NULL,
    supersedes text REFERENCES ledger.facts (fact_id),
    loaded_at  timestamptz NOT NULL
);
CREATE INDEX facts_identity ON ledger.facts (identity);

-- The fact currently in force for each identity.
CREATE TABLE ledger.current (
    identity text PRIMARY KEY,
    fact_id  text NOT NULL REFERENCES ledger.facts (fact_id),
    label    text,                     -- for nodes
    node_id  text
);
CREATE INDEX current_node ON ledger.current (node_id);
