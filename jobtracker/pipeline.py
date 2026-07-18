"""The collect pipeline: turn Collectors into new Notion rows.

``collect`` is the deep module the architecture review calls out: fetch -> filter
-> dedup -> write, with the two side-effecting edges injected — ``collectors``
(the Source seam) and ``sink`` (the write seam). Feed fakes for both and the
whole flow is testable without a network or Notion.
"""

from dataclasses import dataclass
from typing import Callable, Iterable

from jobtracker import filtering
from jobtracker.collectors.base import Collector
from jobtracker.models import JobPosting

# The write seam: prod writes to Notion, tests capture into a list.
Sink = Callable[[JobPosting], None]


@dataclass
class CollectResult:
    created: int
    dup: int
    filtered: int


def collect(
    collectors: Iterable[Collector],
    seen: set[tuple[str, str]],
    sink: Sink,
    *,
    limit: int | None = None,
) -> CollectResult:
    """Fetch from each Collector, keep eligible + new postings, hand them to sink.

    ``seen`` is the set of existing ``(source, external_job_id)`` keys; it is
    updated in place so a run never inserts the same posting twice (ADR-0003).
    ``sink`` performs the write side effect. One Source failing does not stop the
    rest. Returns the run counts.
    """
    created = dup = filtered = 0
    for collector in collectors:
        try:
            jobs: Iterable[JobPosting] = collector.fetch_jobs()
        except Exception as exc:  # noqa: BLE001 - one Source must not stop the rest
            print(f"  [error] source {getattr(collector, 'source', '?')}: {exc}")
            continue
        for job in jobs:
            track = filtering.match(job)
            if not track:
                filtered += 1
                continue
            key = (job["source"], job["external_job_id"])
            if key in seen:
                dup += 1
                continue
            seen.add(key)
            job["track"] = track
            job["status"] = "New"
            sink(job)
            created += 1
            if limit is not None and created >= limit:
                return CollectResult(created, dup, filtered)
    return CollectResult(created, dup, filtered)
