"""Which tier may see a fact (SPEC-007/R4). Decided from the node's label and its trust tier.

- Residents' own reports (trust tier `citizen`) are seen individually by researchers and above; the public
  sees them only in aggregate (platform design, access tiers).
- Company, director and bid records support the contractor network view, which is for researchers first.
- Documents uploaded by residents are seen only by reviewers (constitution C7).
"""

from __future__ import annotations

from typing import Any

from hishob.api.tiers import RANK

BY_LABEL = {"Company": "researcher", "Director": "researcher", "Bid": "researcher"}
BY_TRUST = {"citizen": "researcher"}
CONTRIBUTOR_PUBLISHER = "contributor"


def required_tier(label: str | None, trust: str | None) -> str:
    needed = [BY_LABEL.get(label or "", "public"), BY_TRUST.get(trust or "", "public")]
    return max(needed, key=lambda t: RANK[t])


def node_tier(node: dict[str, Any]) -> str:
    return required_tier(node.get("label"), node.get("tier"))


def source_tier(publisher: str) -> str:
    return "reviewer" if publisher == CONTRIBUTOR_PUBLISHER else "public"
