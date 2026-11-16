-- SPEC-001: document registry
CREATE SCHEMA IF NOT EXISTS registry;

CREATE TABLE registry.documents (
    sha256        text PRIMARY KEY CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    publisher     text NOT NULL CHECK (publisher ~ '^[a-z0-9][a-z0-9-]{1,40}$'),
    media_type    text NOT NULL,
    extension     text NOT NULL,
    size_bytes    bigint NOT NULL CHECK (size_bytes > 0),
    page_count    integer NOT NULL CHECK (page_count >= 0),
    scripts       text[] NOT NULL DEFAULT '{}',
    licence       text NOT NULL CHECK (length(licence) > 0),
    storage_key   text NOT NULL UNIQUE,
    first_seen_at timestamptz NOT NULL
);

CREATE TABLE registry.origins (
    id           bigserial PRIMARY KEY,
    sha256       text NOT NULL REFERENCES registry.documents (sha256),
    origin_kind  text NOT NULL CHECK (origin_kind IN ('url', 'file', 'upload')),
    origin_ref   text NOT NULL,
    fetched_at   timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL,
    account_id   text,
    -- Only uploads carry an account id, and it is an opaque id, never contact details (SPEC-001/R8).
    CHECK ((origin_kind = 'upload') = (account_id IS NOT NULL)),
    UNIQUE (sha256, origin_kind, origin_ref)
);

CREATE TABLE registry.pages (
    sha256         text NOT NULL REFERENCES registry.documents (sha256),
    page           integer NOT NULL CHECK (page >= 1),
    has_text_layer boolean NOT NULL,
    text_key       text,
    CHECK (has_text_layer = (text_key IS NOT NULL)),
    PRIMARY KEY (sha256, page)
);

CREATE TABLE registry.fetch_failures (
    id           bigserial PRIMARY KEY,
    url          text NOT NULL,
    publisher    text NOT NULL,
    reason       text NOT NULL,
    detail       text,
    attempted_at timestamptz NOT NULL
);
