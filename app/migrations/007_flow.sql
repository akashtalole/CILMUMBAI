-- SPEC-009: workflow decisions and step results. LangGraph's checkpoint tables are created in this schema too.
CREATE SCHEMA IF NOT EXISTS flow;

CREATE TABLE flow.decisions (
    id         bigserial PRIMARY KEY,
    thread_id  text NOT NULL,
    gate       text NOT NULL,
    decision   text NOT NULL,
    reason     text NOT NULL CHECK (length(reason) > 0),
    account_id text NOT NULL,
    decided_at timestamptz NOT NULL DEFAULT now()
);

-- Results of steps with side effects, so a step repeated after a restart returns its first result (R7).
CREATE TABLE flow.steps (
    thread_id   text NOT NULL,
    step        text NOT NULL,
    result      jsonb NOT NULL,
    finished_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (thread_id, step)
);
