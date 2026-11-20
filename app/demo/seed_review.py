"""Start a W1 run with stub desks that waits at the release gate, for trying the review screen (SPEC-021).

    HISHOB_DATABASE_URL=postgresql://postgres:hishob@localhost:5432/hishob_demo HISHOB_LOCAL_ROOT=var/demo \\
      uv run python demo/seed_review.py [thread-id]

The run has two wards, each with a brief, a case and a held case, all invented. Nothing here calls Claude.
"""

from __future__ import annotations

import sys
import time

from hishob.archive.storage import LocalStore
from hishob.config import Settings
from hishob.workflows.w1 import Engine, publish_outputs


class DemoDesks:
    def __init__(self, data: LocalStore, public: LocalStore) -> None:
        self.data, self.public = data, public

    def intake(self, hashes: list[str], run_id: str) -> dict[str, int | str]:
        return {"run_id": run_id, "accepted": 12, "held": 1}

    def audit(self, ward: str, run_id: str) -> dict[str, object]:
        prefix = f"staging/{run_id}/"
        brief = (
            f"# Ward brief: {ward}\n\nThe graph holds almost nothing for this ward.\n\n"
            "These checks found nothing because the records needed for them are missing from the graph. "
            "That says nothing either way about the works themselves.\n"
        )
        files = {
            "ward-brief.md": brief,
            "cases/case-01-demo.md": f"## What the records show\n\nA demo case for {ward}. Invented.\n",
            "gaps.jsonl": (
                '{"hop": "completion", "record_needed": "Completion certificate", '
                '"holder": "Executive Engineer (Roads)"}\n'
            ),
        }
        keys = []
        for name, text in files.items():
            self.data.put_new(prefix + name, text.encode(), "text/markdown")
            keys.append(prefix + name)
        held = prefix + "held/case-02-demo.md"
        self.data.put_new(held, b"A case the Challenger held. Invented.\n", "text/markdown")
        return {
            "ward": ward,
            "run_id": run_id,
            "files": keys,
            "status": "complete",
            "held": {held: "the Challenger held it"},
        }

    def publish(self, audit: dict[str, object]) -> list[str]:
        return publish_outputs(self.data, self.public, audit)  # type: ignore[arg-type]


def main() -> None:
    settings = Settings.from_env()
    data, public = LocalStore(settings.local_root / "data"), LocalStore(settings.local_root / "public")
    thread = sys.argv[1] if len(sys.argv) > 1 else f"demo-review-{int(time.time())}"
    status = Engine(settings.database_url, DemoDesks(data, public)).start(thread, ["0" * 64], ["K/W", "H/W"])
    print(thread, "waiting at", status.waiting["gate"] if status.waiting else "nothing")


if __name__ == "__main__":
    main()
