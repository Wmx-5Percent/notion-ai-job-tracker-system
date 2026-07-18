"""The Collector seam: one interface every Source implements.

A Collector discovers Job Postings from a single Source (a Greenhouse/Ashby/Lever
board today, an official-site web crawler later). The collect pipeline talks only
to this interface, so it never names a specific Source.

Adding a Source = write one adapter with this shape + register it in
`jobtracker.collectors.registry.build_registry` (one line). See ADR-0004.
"""

from typing import Iterable, Protocol

from jobtracker.models import JobPosting


class Collector(Protocol):
    """Discovers Job Postings from one Source.

    Keep the interface tiny: a ``source`` name (written to Notion, e.g.
    "greenhouse") and one method that yields normalized, self-contained postings
    with the JD already attached when the Source can provide it cheaply.
    """

    source: str

    def fetch_jobs(self) -> Iterable[JobPosting]:
        ...
