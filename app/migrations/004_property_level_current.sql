-- SPEC-003/R7 (revised): supersession is per property, and a fact can replace several earlier facts.
ALTER TABLE ledger.facts DROP CONSTRAINT IF EXISTS facts_supersedes_fkey;
ALTER TABLE ledger.facts ALTER COLUMN supersedes TYPE text[]
    USING CASE WHEN supersedes IS NULL THEN '{}'::text[] ELSE ARRAY[supersedes] END;
ALTER TABLE ledger.facts ALTER COLUMN supersedes SET DEFAULT '{}';
ALTER TABLE ledger.facts ALTER COLUMN supersedes SET NOT NULL;

-- The fact currently holding each property of each identity.
CREATE TABLE ledger.current_props (
    identity text NOT NULL,
    key      text NOT NULL,
    fact_id  text NOT NULL REFERENCES ledger.facts (fact_id),
    value    jsonb NOT NULL,
    PRIMARY KEY (identity, key)
);
