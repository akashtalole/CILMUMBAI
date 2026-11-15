# ADR 0015: Static site on S3 and CloudFront; MapLibre with PMTiles

**Status:** Accepted · 15 November 2026

## Options

| Concern | Option | For | Against |
|---|---|---|---|
| Hosting | **Static build on S3 behind CloudFront** | Cheapest, fastest, survives api outages with cached pages | Build pipeline is ours |
| | Amplify Hosting | Convenient previews | Less control; another service |
| | Server-rendered app on Fargate | Dynamic pages | Cost and a new failure point |
| Maps | **MapLibre with OpenStreetMap data as PMTiles on S3** | Open; no per-request fee; Marathi labels possible; works offline for demos | We build tiles |
| | Amazon Location Service | Managed tiles, geocoding, routing | Per-request cost; less control over local names |

## Decision

A static web application on S3 and CloudFront. Ward pages, briefs and scheme cards are pre-rendered at each release so they load without the api. Maps use MapLibre with PMTiles built from OpenStreetMap and stored on S3. Geocoding of local names uses our own glossary and road index first.

## Consequences

- Most public traffic is served from the edge and costs little.
- Phone-first design; pages must work on slow connections.
