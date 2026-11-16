-- SPEC-005/R7: a record of every agent run.
CREATE SCHEMA IF NOT EXISTS agentkit;

CREATE TABLE agentkit.runs (
    run_id          text PRIMARY KEY,
    kind            text NOT NULL,                 -- intake, audit, citizen
    session_id      text,
    agents          jsonb NOT NULL,                -- {name: "agent_id@version"}
    inputs          text[] NOT NULL,               -- archive sha256
    outputs         jsonb NOT NULL DEFAULT '{}',   -- {filename: sha256}
    status          text NOT NULL CHECK (status IN ('running', 'complete', 'incomplete', 'failed')),
    status_detail   text,
    cost_usd        numeric(12, 4),
    duration_s      integer,
    threads         jsonb NOT NULL DEFAULT '[]',   -- [{agent, thread_id}]
    load_report_key text,
    started_at      timestamptz NOT NULL,
    finished_at     timestamptz
);
