-- SPEC-010: saved areas and the alerts queued for them.
-- account.* is the account store: the only place anything about a subscriber is kept (constitution C7).
CREATE SCHEMA IF NOT EXISTS account;
CREATE SCHEMA IF NOT EXISTS alerts;

CREATE TABLE account.subscriptions (
    id         bigserial PRIMARY KEY,
    account_id text NOT NULL,
    kind       text NOT NULL CHECK (kind IN ('point', 'roads')),
    geom       geometry(Point, 4326),
    radius_m   integer CHECK (radius_m BETWEEN 100 AND 1000),
    road_ids   text[] NOT NULL DEFAULT '{}',
    language   text NOT NULL CHECK (language IN ('mr', 'hi', 'en')),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((kind = 'point' AND geom IS NOT NULL AND radius_m IS NOT NULL)
        OR (kind = 'roads' AND cardinality(road_ids) BETWEEN 1 AND 20))
);
CREATE INDEX subscriptions_account ON account.subscriptions (account_id);
CREATE INDEX subscriptions_geom ON account.subscriptions USING gist (geom);

-- One row per subscriber per event. event_key makes "never twice" a constraint (R5).
CREATE TABLE alerts.outbox (
    id              bigserial PRIMARY KEY,
    subscription_id bigint NOT NULL REFERENCES account.subscriptions (id) ON DELETE CASCADE,
    event_key       text NOT NULL UNIQUE,
    payload         jsonb NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    sent_at         timestamptz
);
CREATE INDEX outbox_subscription ON alerts.outbox (subscription_id, created_at DESC);
