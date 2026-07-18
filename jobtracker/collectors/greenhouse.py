"""Greenhouse collector: list a company's public board jobs, and (separately)
fetch a single job's full description.

    GET .../boards/<token>/jobs         -> list WITHOUT descriptions (fast)
    GET .../boards/<token>/jobs/<id>    -> one job WITH its description

We list first (cheap), filter, then fetch descriptions only for kept jobs.
"""

import html
import re

import httpx

_JOBS_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
_JOB_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}"


def fetch_jobs(token: str, timeout: float = 20.0) -> list[dict]:
    """List all jobs for one board token WITHOUT descriptions (fast).

    Returns [] if the token is invalid (404) or has no jobs. Raises on other
    HTTP/network errors so the caller can decide how to handle them.
    """
    resp = httpx.get(_JOBS_URL.format(token=token), timeout=timeout)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    jobs = resp.json().get("jobs", [])
    return [_normalize(token, job) for job in jobs]


def fetch_description(token: str, job_id: str, timeout: float = 20.0) -> str:
    """Fetch one job's full description as plain text (call only for kept jobs)."""
    resp = httpx.get(_JOB_URL.format(token=token, job_id=job_id), timeout=timeout)
    resp.raise_for_status()
    return _html_to_text(resp.json().get("content") or "")


def _normalize(token: str, job: dict) -> dict:
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
        "job_description": "",  # filled later via fetch_description for kept jobs
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
