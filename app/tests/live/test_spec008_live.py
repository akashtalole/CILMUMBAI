"""SPEC-008 against the real Claude API. Costs money: runs only with HISHOB_LIVE=1 and a credential."""

from __future__ import annotations

import json
import os

import pytest

from hishob.agentkit.citizen import answer_question
from hishob.agentkit.client import make_client
from hishob.agentkit.provision import apply
from hishob.api.citations import parse_dates
from hishob.place import geo
from tests.integration.test_spec006_graph import EN, HEAD
from tests.integration.test_spec007_api import api  # noqa: F401

pytestmark = [
    pytest.mark.live,
    pytest.mark.integration,
    pytest.mark.graph,
    pytest.mark.skipif(os.environ.get("HISHOB_LIVE") != "1", reason="live tests need HISHOB_LIVE=1"),
]


def test_spec008_live_marathi_question_about_a_pothole(api, conn, make_archive) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    http, config, _ = api
    from hishob.archive import Archive
    from hishob.archive.events import MemorySink
    from hishob.archive.registry import Registry
    from hishob.ledger import Loader

    archive = Archive(Registry(conn), config.sources, config.data, MemorySink())
    road_line = {
        "kind": "node",
        "id": "road:sv",
        "label": "Road",
        "source": EN,
        "page": 1,
        "quote": HEAD,
        "tier": "reported",
        "confidence": 0.9,
        "props": {"name_mr": "एस. व्ही. रोड", "geometry_wkt": "LINESTRING(72.8350 19.1000, 72.8360 19.1300)"},
    }
    assert Loader(conn, archive, config.data).load([road_line], batch_id="live-geo", extractor="test@1").accepted == 1
    geo.build(conn)

    client = make_client()
    for item in apply(client):
        print(item)
    question = (
        "माझे नाव सुनीता पाटील, फोन 9820012345. एस. व्ही. रोडवरील खड्डा कोण दुरुस्त करणार? कंत्राटदाराची जबाबदारी कधीपर्यंत आहे?"
    )
    answer = answer_question(client, http, question, cap_usd=2)
    print(json.dumps(answer.__dict__, ensure_ascii=False, indent=2))

    assert answer.language == "mr"
    assert answer.status == "answered", answer.problems
    assert any(year == 2031 for _, (year, _, _), _ in parse_dates(answer.text))
    assert "सुनीता" not in answer.text and "9820012345" not in answer.text
