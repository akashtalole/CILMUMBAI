-- SPEC-004: place spine. Built from the ledger by `hishob place build`; can be dropped and rebuilt.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE SCHEMA IF NOT EXISTS geo;

CREATE TABLE geo.admin_wards (
    node_id text PRIMARY KEY,
    code    text NOT NULL,
    name    text,
    geom    geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX admin_wards_geom ON geo.admin_wards USING gist (geom);

CREATE TABLE geo.electoral_wards (
    node_id text PRIMARY KEY,
    number  integer,
    name    text,
    geom    geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX electoral_wards_geom ON geo.electoral_wards USING gist (geom);

CREATE TABLE geo.road_segments (
    node_id    text PRIMARY KEY,
    name       text,
    name_mr    text,
    osm_way_id text,
    geom       geometry(LineString, 4326) NOT NULL
);
CREATE INDEX road_segments_geom ON geo.road_segments USING gist (geom);

-- Every name a place is known by: its own names and confirmed aliases, in normalised and Latin-key forms.
CREATE TABLE geo.aliases (
    node_id text NOT NULL,
    kind    text NOT NULL,          -- AdminWard, ElectoralWard, Road
    alias   text NOT NULL,
    norm    text NOT NULL,
    key     text NOT NULL,
    origin  text NOT NULL,          -- name, name_mr, name_en, code, alias
    PRIMARY KEY (node_id, alias)
);
CREATE INDEX aliases_norm_trgm ON geo.aliases USING gin (norm gin_trgm_ops);
CREATE INDEX aliases_key_trgm ON geo.aliases USING gin (key gin_trgm_ops);
