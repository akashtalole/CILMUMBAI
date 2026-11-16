"""Ask the citizen desk over HTTP (SPEC-020 demo slice, on SPEC-008).

An answer takes up to a minute or two, so a question starts a job and the page polls for it. Each job is one
Managed Agents session, which costs money: questions are limited per client per hour and in how many run at once,
and the endpoint is off unless the server is configured with Claude credentials.

Jobs live in this process's memory for an hour. That is enough for one API process (the demo profile); behind
several, the job store moves to Postgres.
"""

from __future__ import annotations

import secrets
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

AskRun = Callable[..., dict[str, Any]]  # (http, question, *, language, location, token) -> answer as a dict
KEEP_S = 3600


class Refused(Exception):
    pass


@dataclass
class Job:
    id: str
    started: float
    status: str = "running"  # running, done, failed
    answer: dict[str, Any] | None = None
    error: str | None = None
    finished: float | None = None


@dataclass
class AskDesk:
    run: AskRun
    per_hour: int = 10
    max_running: int = 4
    clock: Callable[[], float] = time.monotonic
    jobs: dict[str, Job] = field(default_factory=dict)
    _asked: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def submit(self, client: str, http: Any, question: str, **kwargs: Any) -> Job:
        now = self.clock()
        with self._lock:
            self._expire(now)
            asked = self._asked[client]
            while asked and now - asked[0] >= 3600:
                asked.popleft()
            if len(asked) >= self.per_hour:
                raise Refused(f"at most {self.per_hour} questions an hour")
            if sum(1 for j in self.jobs.values() if j.status == "running") >= self.max_running:
                raise Refused("the desk is busy; try again in a minute")
            asked.append(now)
            job = Job(secrets.token_urlsafe(16), now)
            self.jobs[job.id] = job
        threading.Thread(target=self._work, args=(job, http, question, kwargs), daemon=True).start()
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            self._expire(self.clock())
            return self.jobs.get(job_id)

    def _work(self, job: Job, http: Any, question: str, kwargs: dict[str, Any]) -> None:
        try:
            answer = self.run(http, question, **kwargs)
            job.answer, job.status = answer, "done"
        except Exception as error:  # the page shows a plain message; the detail goes to the log
            job.error, job.status = type(error).__name__, "failed"
        finally:
            job.finished = self.clock()

    def _expire(self, now: float) -> None:
        for job_id in [i for i, j in self.jobs.items() if j.finished is not None and now - j.finished > KEEP_S]:
            del self.jobs[job_id]


def public_answer(answer: Any) -> dict[str, Any]:
    """What the page needs from a citizen desk Answer. `body` is the reply without the sources list the desk
    appends to `text`; the page shows the sources itself, from `sources`."""
    from hishob.agentkit.citizen import SOURCES

    heading = f"\n\n{SOURCES.get(answer.language, SOURCES['en'])}:\n"
    return {
        "text": answer.text,
        "body": answer.text.split(heading)[0] if answer.sources else answer.text,
        "language": answer.language,
        "status": answer.status,
        "sources": answer.sources,
        "draft_letter": answer.draft_letter,
        "gaps": answer.gaps,
        "cited_fact_ids": answer.cited_fact_ids,
    }
