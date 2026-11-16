-- SPEC-006: which ledger files the graph has applied. The graph itself can be dropped and rebuilt.
CREATE SCHEMA IF NOT EXISTS graphstore;

CREATE TABLE graphstore.applied (
    file_key   text PRIMARY KEY,
    facts      integer NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
);
