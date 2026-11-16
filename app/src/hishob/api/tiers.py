"""Access tiers and how a request gets one (SPEC-007/R2, R3; constitution C8).

Until sign-in is wired to Cognito (SPEC-013), tiers come from signed development tokens:
`<tier>.<account>.<signature>`, HMAC-SHA256 with HISHOB_TOKEN_SECRET. Anything else is public.
"""

from __future__ import annotations

import hashlib
import hmac
import re

TIERS = ["public", "contributor", "researcher", "official", "reviewer"]
RANK = {tier: i for i, tier in enumerate(TIERS)}
_ACCOUNT = re.compile(r"^[A-Za-z0-9_-]{3,64}$")


def allows(caller: str, required: str) -> bool:
    return RANK[caller] >= RANK[required]


def sign(tier: str, account: str, secret: str) -> str:
    if tier not in RANK or not _ACCOUNT.match(account):
        raise ValueError("bad tier or account")
    mac = hmac.new(secret.encode(), f"{tier}.{account}".encode(), hashlib.sha256).hexdigest()
    return f"{tier}.{account}.{mac}"


def resolve(authorization: str | None, secret: str | None) -> tuple[str, str | None]:
    """Return (tier, account). No credential, a bad one, or no secret configured: public (R3)."""
    if not authorization or not secret or not authorization.startswith("Bearer "):
        return "public", None
    parts = authorization.removeprefix("Bearer ").strip().split(".")
    if len(parts) != 3:
        return "public", None
    tier, account, mac = parts
    if tier not in RANK or not _ACCOUNT.match(account):
        return "public", None
    expected = hmac.new(secret.encode(), f"{tier}.{account}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, expected):
        return "public", None
    return tier, account
