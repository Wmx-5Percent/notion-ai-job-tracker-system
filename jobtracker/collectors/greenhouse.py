"""Greenhouse Collector: fetch every configured board's jobs, each WITH its full
description, in one request per board (?content=true).

    GET .../boards/<token>/jobs?content=true   -> all of a board's jobs, WITH JDs

`content=true` returns every job's JD in a single call, so the filter can read
the JD (not just the title) and still catch student roles whose only intern
signal lives in the description.
"""

import html
import re
from typing import Iterator

import httpx

from jobtracker.models import JobPosting

_JOBS_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


class GreenhouseCollector:
    """Collector adapter for Greenhouse public boards.

    Holds the board tokens it is responsible for; a bad or empty board is logged
    and skipped so one dead token never stops the run.
    """

    source = "greenhouse"

    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens

    def fetch_jobs(self) -> Iterator[JobPosting]:
        for token in self._tokens:
            try:
                yield from fetch_board(token)
            except Exception as exc:  # noqa: BLE001 - skip a bad board, keep going
                print(f"  [error] greenhouse:{token}: {exc}")


def fetch_board(token: str, timeout: float = 60.0) -> list[JobPosting]:
    """Fetch one board's jobs WITH descriptions (?content=true).

    Returns [] if the token is invalid (404) or has no jobs. Raises on other
    HTTP/network errors so the caller can decide how to handle them.
    """
    resp = httpx.get(
        _JOBS_URL.format(token=token), params={"content": "true"}, timeout=timeout
    )
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return [_normalize(token, job) for job in resp.json().get("jobs", [])]


def _normalize(token: str, job: dict) -> JobPosting:
    """Map a raw Greenhouse job into our normalized Job Posting dict."""
    location = job.get("location") or {}
    updated = job.get("updated_at") or ""
    return {
        "source": "greenhouse",
        "company": token,
        "external_job_id": str(job.get("id", "")),
        "title": (job.get("title") or "").strip(),
        "location": (location.get("name") or "").strip(),
        "url": job.get("absolute_url") or "",
        "posted_date": updated[:10] or None,  # YYYY-MM-DD
        "job_description": _html_to_text(job.get("content") or ""),
    }


def _html_to_text(content: str) -> str:
    """Greenhouse `content` is HTML-entity-encoded HTML. Decode, then strip tags."""
    if not content:
        return ""
    text = html.unescape(content)
    text = re.sub(r"<\s*(br|/p|/div|/li|/h[1-6]|/tr)\s*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
