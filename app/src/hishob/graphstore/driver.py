"""Connect to the graph over Bolt. Works for Neo4j and for Neptune's openCypher Bolt endpoint."""

from __future__ import annotations

from typing import Any

from hishob.config import Settings


def make_driver(settings: Settings) -> Any:
    from neo4j import GraphDatabase

    # Server notices such as "this label is not in the database" are expected while data is partial.
    return GraphDatabase.driver(
        settings.graph_uri,
        auth=(settings.graph_user, settings.graph_password),
        notifications_min_severity="OFF",
    )
