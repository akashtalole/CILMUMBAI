"""Build the Claude client: Claude Platform on AWS when configured (ADR 0002), the Claude API otherwise."""

from __future__ import annotations

import os
from typing import Any


def make_client() -> Any:
    import anthropic

    if os.environ.get("ANTHROPIC_AWS_WORKSPACE_ID"):
        return anthropic.AnthropicAWS()
    return anthropic.Anthropic()
