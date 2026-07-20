"""Workday Collector: query each configured company's Workday CXS API for intern
postings and yield them.

Workday is unlike Greenhouse/Ashby/Lever:
  * POST + pagination (no single-request board);
  * ``searchText`` is fuzzy (it matches almost the whole board, not just interns),
    so instead we read the board's ``facets`` and apply the intern facet
    (e.g. workerSubType "Intern") to narrow SERVER-SIDE to real intern roles;
  * the listing has NO job description (a per-job GET would be needed), so we
    yield title-only postings (``job_description=""``) — the filter runs on the
    title and the Notion row links out;
  * config is a mapping {host, tenant, site} because Workday tenants/sites vary,
    e.g. {host: nvidia.wd5, tenant: nvidia, site: NVIDIAExternalCareerSite}.
"""

import re
from typing import Iterator

import httpx

from jobtracker.models import JobPosting

_CXS = "https://{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
_PAGE = 20
_MAX_PAGES = 25  # cap ~500 postings/company (the intern facet keeps results small)
_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

# Facet value descriptors that mark an intern / early-career role. Workday facet
# ids are tenant-specific, but these human-readable labels are stable, so we match
# on them to find which facet to apply per board.
_INTERN_FACET = re.compile(
    r"intern|trainee|apprentic|co-?op|\bstudent\b|early care|universit|campus|placement",
    re.I,
)


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


def _post_jobs(base: str, applied_facets: dict, search: str, offset: int, timeout: float):
    """POST one page of the CXS jobs search; return the JSON dict (None on 404)."""
    resp = httpx.post(
        f"{base}/jobs",
        json={"appliedFacets": applied_facets, "limit": _PAGE, "offset": offset, "searchText": search},
        headers=_HEADERS,
        timeout=timeout,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json() or {}


def _pick_intern_facet(facets: list[dict]):
    """From a CXS ``facets`` list, return (facetParameter, [value ids]) that best
    isolates intern / early-career roles, or None if the board has no such facet.

    Facet value ids are tenant-specific, so we match the human-readable value
    descriptors (e.g. "Intern - Regular", "Co-op/Intern", "Interns"). When more
    than one facet dimension carries intern values, prefer the one covering the
    most postings, tie-breaking toward the employment-type facets.
    """
    by_param: dict[str, dict] = {}
    for facet in facets or []:
        param = facet.get("facetParameter")
        if not param:
            continue
        for value in facet.get("values") or []:
            if value.get("id") and _INTERN_FACET.search(value.get("descriptor") or ""):
                slot = by_param.setdefault(param, {"ids": [], "count": 0})
                slot["ids"].append(value["id"])
                slot["count"] += value.get("count") or 0
    if not by_param:
        return None
    best = max(
        by_param,
        key=lambda p: (by_param[p]["count"], p in ("workerSubType", "timeType"), p == "jobFamilyGroup"),
    )
    return best, by_param[best]["ids"]


def fetch_board(cfg: dict, timeout: float = 30.0) -> Iterator[JobPosting]:
    """Yield a company's intern postings (title-only) via Workday's CXS API.

    Read the board's facets and apply the intern facet server-side; if the board
    exposes no intern facet, fall back to the fuzzy ``searchText=intern``.
    """
    base = _CXS.format(host=cfg["host"], tenant=cfg["tenant"], site=cfg["site"])
    probe = _post_jobs(base, {}, "", 0, timeout)
    if probe is None:
        return
    facet = _pick_intern_facet(probe.get("facets") or [])
    applied = {facet[0]: facet[1]} if facet else {}
    search = "" if facet else "intern"  # facet is precise; else fall back to fuzzy search

    offset = 0
    for _ in range(_MAX_PAGES):
        data = _post_jobs(base, applied, search, offset, timeout)
        if data is None:
            return
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
