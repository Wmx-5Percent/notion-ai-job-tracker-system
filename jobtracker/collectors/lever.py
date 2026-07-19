"""Lever Collector: fetch every configured company's postings, each WITH its
plain-text description, in one request per company.

    GET https://api.lever.co/v0/postings/<slug>?mode=json  -> [ {posting}, ... ]

Lever returns ``descriptionPlain`` (already plain text) per posting, so the
filter can read the JD without any HTML stripping.
"""

from datetime import datetime, timezone
from typing import Iterator

from jobtracker.collectors._http import get_json
from jobtracker.models import JobPosting

_POSTINGS_URL = "https://api.lever.co/v0/postings/{slug}"


class LeverCollector:
    """Collector adapter for Lever public postings boards.

    Holds the company slugs it is responsible for; a bad or empty board is logged
    and skipped so one dead slug never stops the run.
    """

    source = "lever"

    def __init__(self, slugs: list[str]) -> None:
        self._slugs = slugs

    def fetch_jobs(self) -> Iterator[JobPosting]:
        for slug in self._slugs:
            try:
                yield from fetch_board(slug)
            except Exception as exc:  # noqa: BLE001 - skip a bad board, keep going
                print(f"  [error] lever:{slug}: {exc}")


def fetch_board(slug: str, timeout: float = 30.0) -> list[JobPosting]:
    """Fetch one Lever board's postings WITH descriptions. [] on 404/empty.

    The Lever postings API returns a JSON list; anything else is treated as empty.
    """
    data = get_json(_POSTINGS_URL.format(slug=slug), params={"mode": "json"}, timeout=timeout)
    if not isinstance(data, list):
        return []
    return [_normalize(slug, job) for job in data]


def _normalize(slug: str, job: dict) -> JobPosting:
    """Map a raw Lever posting into our normalized Job Posting dict."""
    cats = job.get("categories") or {}
    created = job.get("createdAt")
    posted = None
    if isinstance(created, (int, float)):
        posted = datetime.fromtimestamp(created / 1000, tz=timezone.utc).date().isoformat()
    return {
        "source": "lever",
        "company": slug,
        "external_job_id": str(job.get("id", "")),
        "title": (job.get("text") or "").strip(),
        "location": (cats.get("location") or "").strip(),
        "url": job.get("hostedUrl") or job.get("applyUrl") or "",
        "posted_date": posted,
        "job_description": (job.get("descriptionPlain") or "").strip(),
    }
