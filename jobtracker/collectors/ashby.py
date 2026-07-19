"""Ashby Collector: fetch every configured job board's postings, each WITH its
plain-text description, in one request per board.

    GET https://api.ashbyhq.com/posting-api/job-board/<slug>  -> all postings + JD

Ashby's public posting API returns ``descriptionPlain`` (already plain text) per
job, so the filter can read the JD without any HTML stripping.
"""

from typing import Iterator

from jobtracker.collectors._http import get_json
from jobtracker.models import JobPosting

_BOARD_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


class AshbyCollector:
    """Collector adapter for Ashby public job boards.

    Holds the board slugs it is responsible for; a bad or empty board is logged
    and skipped so one dead slug never stops the run.
    """

    source = "ashby"

    def __init__(self, slugs: list[str]) -> None:
        self._slugs = slugs

    def fetch_jobs(self) -> Iterator[JobPosting]:
        for slug in self._slugs:
            try:
                yield from fetch_board(slug)
            except Exception as exc:  # noqa: BLE001 - skip a bad board, keep going
                print(f"  [error] ashby:{slug}: {exc}")


def fetch_board(slug: str, timeout: float = 30.0) -> list[JobPosting]:
    """Fetch one Ashby board's postings WITH descriptions. [] on 404/empty.

    Retries transient failures (see _http.get_json).
    """
    data = get_json(
        _BOARD_URL.format(slug=slug), params={"includeCompensation": "true"}, timeout=timeout
    )
    if data is None:
        return []
    return [_normalize(slug, job) for job in data.get("jobs", [])]


def _normalize(slug: str, job: dict) -> JobPosting:
    """Map a raw Ashby posting into our normalized Job Posting dict."""
    published = job.get("publishedAt") or ""
    return {
        "source": "ashby",
        "company": slug,
        "external_job_id": str(job.get("id", "")),
        "title": (job.get("title") or "").strip(),
        "location": (job.get("location") or "").strip(),
        "url": job.get("jobUrl") or job.get("applyUrl") or "",
        "posted_date": published[:10] or None,  # YYYY-MM-DD
        "job_description": (job.get("descriptionPlain") or "").strip(),
    }
