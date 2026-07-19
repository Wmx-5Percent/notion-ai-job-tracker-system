"""Shared HTTP for Collectors: GET JSON with a few retries, so a transient timeout
or 5xx does not silently drop a whole company for a run (see companies.yaml policy).
"""

import time
from typing import Any

import httpx


def get_json(
    url: str,
    params: dict | None = None,
    *,
    timeout: float = 30.0,
    retries: int = 2,
    backoff: float = 1.5,
) -> Any:
    """GET and parse JSON. Returns None on 404 (board gone).

    Retries on timeout / transport error / 5xx (with linear backoff); a non-404
    4xx fails fast; the last error is raised if every attempt fails.
    """
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = httpx.get(url, params=params, timeout=timeout, follow_redirects=True)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code < 500:
                raise
            last_exc = exc
        if attempt < retries:
            time.sleep(backoff * (attempt + 1))
    assert last_exc is not None
    raise last_exc
