"""Load the synthetic demo world into empty local stores, for trying the web app (SPEC-020 demo slice).

    createdb hishob_demo && psql -d hishob_demo -c 'CREATE EXTENSION postgis' -c 'CREATE EXTENSION pg_trgm'
    HISHOB_DATABASE_URL=postgresql://postgres:hishob@localhost:5432/hishob_demo HISHOB_LOCAL_ROOT=var/demo \\
      uv run python demo/seed.py

Everything here is invented test data, marked as such inside each document: the S. V. Road scenario from the
SPEC-006 tests (tender, award, contractor, defect liability period, responsible posts, a payment), on the fixture
road and ward shapes. It is for exercising the interface, never for real answers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))  # the scenario lives with the tests

from hishob import db  # noqa: E402
from hishob.cli import build_archive  # noqa: E402
from hishob.config import Settings  # noqa: E402
from hishob.graphstore import GraphStore  # noqa: E402
from hishob.graphstore.driver import make_driver  # noqa: E402
from hishob.ledger import Loader  # noqa: E402
from hishob.place import geo  # noqa: E402
from hishob.place.importer import import_roads, import_wards  # noqa: E402
from tests.conftest import FIXTURES  # noqa: E402
from tests.integration.test_spec006_graph import SCENARIO  # noqa: E402

ROAD = "road:osm-1001"  # the fixture's S. V. Road segment, standing in for the scenario's road:sv
LICENCE = "synthetic test fixture, invented for the demo"


def remap(record: dict) -> dict:
    out = json.loads(json.dumps(record).replace('"road:sv"', f'"{ROAD}"'))
    if out.get("id") == ROAD:
        out["id"] = "road:sv-scenario"  # the scenario's own road node is replaced by the fixture road
    return out


def main() -> None:
    settings = Settings.from_env()
    conn = db.connect(settings.database_url)
    db.migrate(conn)
    if conn.execute("SELECT count(*) FROM ledger.facts").fetchone()[0]:
        sys.exit("the ledger is not empty: seed only an empty demo database")
    archive = build_archive(settings)
    for name in ("tender-en.pdf", "award-notice.pdf"):
        archive.add_file(FIXTURES / name, publisher="bmc", licence=LICENCE)
    loader = Loader(conn, archive, archive.data)
    import_wards(archive, loader, FIXTURES / "wards-fixture.geojson", kind="admin", name_property="name",
                 publisher="demo", licence=LICENCE, batch_id="demo-wards")
    import_roads(archive, loader, FIXTURES / "roads-fixture.json", publisher="demo", licence=LICENCE,
                 batch_id="demo-roads")
    records = [remap(r) for r in SCENARIO if not (r.get("id") == "road:sv")]
    report = loader.load(records, batch_id="demo-scenario", extractor="demo-seed@1")
    print(f"scenario: {report.accepted} facts loaded, {report.held_total} held")
    geo.build(conn)
    driver = make_driver(settings)
    try:
        print(GraphStore(driver, conn, archive.data, settings.graph_database).rebuild())
    finally:
        driver.close()


if __name__ == "__main__":
    main()
