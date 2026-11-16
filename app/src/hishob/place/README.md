# Place spine: loading real data

The importers read standard files. Each file is archived first, and every ward or road becomes a checked fact citing it (SPEC-004).

## Administrative wards (loaded and checked)

DataMeet publishes BMC's 24 administrative ward boundaries. Its licence was not stated in the files reachable on 16 Nov 2026: confirm before republishing anything derived from it. The file may predate later ward changes.

```sh
curl -L -o BMC_Wards.geojson https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/master/Mumbai/BMC_Wards.geojson
uv run hishob place import-wards BMC_Wards.geojson --kind admin --name-property name \
  --publisher datameet --licence "DataMeet Municipal_Spatial_Data; licence to confirm" --batch datameet-wards-1
uv run hishob place at 19.0988 72.8267     # Juhu beach -> K/W
```

## Roads for K/West

The build environment could not reach Overpass or Geofabrik, so K/West's roads are not loaded yet. From any browser:

1. Open <https://overpass-turbo.eu/>.
2. Paste this query and press **Run**. The box is K/West's extent from the ward file.

   ```
   [out:json][timeout:90];
   way["highway"~"^(trunk|primary|secondary|tertiary|unclassified|residential|living_street|trunk_link|primary_link|secondary_link|tertiary_link)$"]["name"](19.0799,72.7804,19.1565,72.85);
   out tags geom;
   ```

3. **Export → raw OSM data**, save as `kw-roads.json`.
4. Import it:

   ```sh
   uv run hishob place import-roads kw-roads.json --batch osm-kw-roads-1
   uv run hishob place find "SV road"
   uv run hishob place at 19.1197 72.8464
   ```

OpenStreetMap data is © OpenStreetMap contributors, under the Open Database Licence (ODbL 1.0). Record the export date: it is the source's fetch time.

## Electoral wards

No reachable source yet. Any GeoJSON with one feature per electoral ward and a property holding its number imports:

```sh
uv run hishob place import-wards electoral.geojson --kind electoral --name-property <property> \
  --publisher <who> --licence <licence> --batch electoral-1
```

## Field test (SPEC-004/AC6)

Ask someone who knows K/West to pick twenty points (a junction, a lane, a building) and say which road and ward each is on. Run `hishob place at` for each and record the answers in the spec. At least 19 must match.
