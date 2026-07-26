"""Core domain types shared across the pipeline.

``JobPosting`` is the normalized shape every Collector yields and the Sink writes
(see CONTEXT.md). It lives here, rather than inside a collector or the Notion
writer, so producers and consumers share one definition without coupling.
"""

from typing import Literal, NotRequired, TypedDict

JobKind = Literal["Internship", "Co-op", "New Grad", "Early Career", "Other"]
DiscoveryMethod = Literal[
    "api",
    "rss",
    "public_page",
    "websearch",
    "manual_submission",
]


class JobPosting(TypedDict):
    """A normalized Job Posting (see CONTEXT.md).

    ``source`` + ``external_job_id`` is the dedup identity (ADR-0003). ``track``
    and ``status`` are filled by the pipeline, not the Collector.
    """

    source: str
    company: str
    external_job_id: str
    title: str
    location: str
    url: str
    posted_date: str | None
    job_description: str
    track: NotRequired[str]
    status: NotRequired[str]
    job_kind: NotRequired[JobKind | None]
    deadline: NotRequired[str | None]
    canonical_job_key: NotRequired[str | None]
    discovery_method: NotRequired[DiscoveryMethod | None]
    evidence_url: NotRequired[str | None]
    fetched_at: NotRequired[str | None]
