# SPEC-004: Place spine

| | |
|---|---|
| Status | In progress: AC1 to AC5 pass; AC6 (field test by someone who knows the ward) and K/West's real roads are pending |
| Milestone | M0 |
| Owner role | Data engineer |
| Depends on | SPEC-002, SPEC-003 |
| ADRs | 0006, 0015 |
| Personas served | Sunita, Imran, Lata, Assistant Engineer |

## 1. Problem and outcome

Almost every question starts with a place: a road, a lane, a ward. Tenders name roads in free text, in two scripts, with local aliases. Without a spine of places, nothing joins.

When done, the demo ward's administrative and electoral boundaries and named roads are loaded as facts with geometry, with aliases in Marathi and English, and two functions work: find a place by name, and find what is at a point.

## 2. User stories

- As a resident, I want to name my road the way I say it, so that the platform finds it.
- As the intake desk, I want road names in tenders matched to road ids, so that works land on the map.
- As an engineer in the ward, I want a pin to resolve to the right road and ward.

## 3. Requirements

| Id | Requirement |
|---|---|
| R1 | The system shall hold administrative wards, electoral wards and named road segments for the demo ward as ledger facts with geometry. |
| R2 | Each road shall carry its OpenStreetMap way ids, an English name, a Marathi name where known, and aliases. |
| R3 | `find_place(text)` shall return candidate places ranked by match quality, matching across scripts by transliteration. |
| R4 | `at_point(lat, lon)` shall return the nearest road segment within 50 metres, its administrative ward and electoral ward, and the distance. |
| R5 | If no road lies within 50 metres, then `at_point` shall return the wards only and state that no road was found. |
| R6 | When a reviewer confirms an alias, the system shall add it as a fact with tier `derived` and the reviewer's decision as source. |

## 4. Acceptance criteria

| Id | Given | When | Then | Verifies |
|---|---|---|---|---|
| AC1 | The spine is loaded | Ward and road counts are queried | They match the source files | R1 |
| AC2 | A road known as "S.V. Road" with Marathi name "एस. व्ही. रोड" | `find_place("SV road")` and `find_place("एस व्ही रोड")` are called | Both return that road first | R2, R3 |
| AC3 | A point 10 m from a road | `at_point` is called | It returns that road, the right wards and a distance under 15 m | R4 |
| AC4 | A point in a park 200 m from any road | `at_point` is called | It returns the wards and `road: null` with a reason | R5 |
| AC5 | A reviewer confirms "Station Road" as an alias of a segment | The decision is saved | `find_place("Station Road")` returns that segment | R6 |
| AC6 | Twenty test points chosen by someone who knows the ward | `at_point` is called for each | At least 19 return the road and ward they expect | R4 |

## 5. Interfaces and data contracts

```python
def find_place(text: str, kinds: set[str] | None = None, limit: int = 10) -> list[PlaceMatch]: ...
def at_point(lat: float, lon: float) -> PointResult: ...
```

PostGIS tables in schema `geo`, populated from the ledger: `admin_wards`, `electoral_wards`, `road_segments`, `aliases`.

## 6. Non-functional requirements

- `at_point` under 50 ms; `find_place` under 100 ms.
- Geometry in WGS 84; distances computed in a metric projection.

## 7. Constitution

| Article | How this spec upholds it |
|---|---|
| C1 | Places are ledger facts with sources (boundary files, OpenStreetMap extract with date) |
| C10 | Marathi names and cross-script matching tested |

## 8. Out of scope

Plots and survey numbers (SPEC-027). Other wards beyond the demo ward (M2).

## 9. Design notes

- Names are matched on a normalised form (lower case, punctuation removed, runs of single letters joined, so "S. V. Road" and "SV road" agree) and on a Latin key made by transliterating Devanagari, so "अंधेरी" also matches "Andheri". Trigram similarity in Postgres ranks the candidates.
- Record the OpenStreetMap extract date as the source's fetched time and licence as ODbL.

### Decisions made while building (16 Nov 2026)

- **Sources.** Administrative wards: DataMeet's `Municipal_Spatial_Data/Mumbai/BMC_Wards.geojson` (24 wards; licence not stated in the files reached, to confirm). Roads: an OpenStreetMap export in Overpass JSON. Electoral wards: no reachable source yet; any GeoJSON with a ward number imports.
- **Files are archived first.** Each source file goes into the archive (SPEC-001); its places become ledger facts citing it, with the feature's name as the quote, and pass the loader's checks (SPEC-003). The geo tables are built from the ledger and can be rebuilt.
- **Tier.** Community-digitised boundaries and OpenStreetMap are `reported`, not `official`.
- **Ontology 0.2.0.** Adds `name_mr` on every node, an `Alias` node and an `ALIAS_OF` relationship, so a reviewer's confirmed alias is a fact like any other (R6).
- **What could not be fetched here.** The build environment's connections to Overpass and Geofabrik are refused, so K/West's roads are not loaded yet. `app/src/hishob/place/README.md` gives the export query to run in a browser.

## 10. Tasks

| Id | Task | Size | Depends on | Verifies | State |
|---|---|---|---|---|---|
| T1 | Import ward boundaries as facts | S | SPEC-003/T6 | AC1 | Done (real: 24 wards) |
| T2 | Import road segments from an OpenStreetMap extract | M | T1 | AC1 | Done (fixture; real roads pending) |
| T3 | Geo tables built from the ledger | S | T2 | AC1 | Done |
| T4 | `find_place` with transliteration | M | T3 | AC2 | Done |
| T5 | `at_point` | S | T3 | AC3, AC4 | Done |
| T6 | Alias confirmation path | S | T4 | AC5 | Done |
| T7 | Field test with twenty points | S | T5 | AC6 | Pending: needs a person |

## 11. Open questions

| Question | Owner | Assumption until answered |
|---|---|---|
| Source and licence for electoral ward boundaries | Data engineer | OpenCity file, licence to confirm |

## Change log

| Date | Change |
|---|---|
| 16 Nov 2026 | Implemented in `app/src/hishob/place/` with migration `005_geo.sql`; tests in `app/tests/integration/test_spec004_place.py`. Ontology 0.2.0 adds `name_mr`, `Alias` and `ALIAS_OF`. Ward lookups include points on a boundary (a point exactly between two wards still gets one). Loading guide: `app/src/hishob/place/README.md`. |
| 16 Nov 2026 | Real data: DataMeet's 24 administrative wards loaded, all quotes matched. The file writes "K/W" as `K\/W`; the importer now quotes names exactly as the file spells them. Seven known places resolved to the right ward (Juhu beach K/W, MIDC Andheri East K/E, Gateway of India A, Bandra Bandstand H/W, Borivali station R/C, Kurla L, Juhu–Vile Parle West K/W). |
