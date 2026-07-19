"""Workday Collector: query each configured company's Workday CXS API for intern
postings and yield them.

Workday is unlike Greenhouse/Ashby/Lever:
  * POST + pagination (no single-request board);
  * server-side ``searchText`` narrows to intern roles cheaply;
  * the listing has NO job description (a per-job GET would be needed), so v1
    yields title-only postings (``job_description=""``) — the filter runs on the
    title (searchText already selected intern roles) and the Notion row links out;
  * config is a mapping {host, tenant, site} because Workday tenants/sites vary,
    e.g. {host: nvidia.wd5, tenant: nvidia, site: NVIDIAExternalCareerSite}.
"""

from typing import Iterator

import httpx

from jobtracker.models import JobPosting

_CXS = "https://{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
_PAGE = 20
_MAX_PAGES = 10  # cap ~200 intern results per company (avoid runaway on huge tenants)
_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


class WorkdayCollector:
    """Collector adapter for company Workday CXS job boards."""

    source = "workday"

    def __init__(self, configs: list[dict]) -> None:
        self._configs = configs

    def fetch_jobs(self) -> Iterator[JobPosting]:
        for cfg in self._configs:
            try:
                yield from fetch_board(cfg)
            except Exception as exc:  # noqa: BLE001 - skip a bad board, keep going
                print(f"  [error] workday:{cfg.get('tenant', cfg)}: {exc}")


def fetch_board(cfg: dict, timeout: float = 30.0) -> Iterator[JobPosting]:
    """Yield a company's intern postings (title-only) via Workday's CXS search."""
    base = _CXS.format(host=cfg["host"], tenant=cfg["tenant"], site=cfg["site"])
    offset = 0
    for _ in range(_MAX_PAGES):
        resp = httpx.post(
            f"{base}/jobs",
            json={"appliedFacets": {}, "limit": _PAGE, "offset": offset, "searchText": "intern"},
            headers=_HEADERS,
            timeout=timeout,
        )
        if resp.status_code == 404:
            return
        resp.raise_for_status()
        data = resp.json() or {}
        postings = data.get("jobPostings") or []
        if not postings:
            return
        for p in postings:
            yield _normalize(cfg, base, p)
        offset += _PAGE
        if offset >= (data.get("total") or 0):
            return


def _normalize(cfg: dict, base: str, p: dict) -> JobPosting:
    """Map a raw Workday posting into our normalized Job Posting dict (no JD in v1)."""
    path = p.get("externalPath") or ""
    return {
        "source": "workday",
        "company": cfg.get("tenant", ""),
        "external_job_id": path,
        "title": (p.get("title") or "").strip(),
        "location": (p.get("locationsText") or "").strip(),
        "url": f"https://{cfg['host']}.myworkdayjobs.com/{cfg['site']}{path}",
        "posted_date": None,
        "job_description": "",
    }
