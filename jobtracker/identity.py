"""Pure, conservative identity helpers for normalized job postings."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from jobtracker.models import JobPosting

_TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "gh_src",
    "lever-source",
    "ref",
    "referrer",
    "source",
}
_PERCENT_ESCAPE = re.compile(r"%[0-9a-fA-F]{2}")
_SPACE = re.compile(r"\s+")


def canonicalize_url(url: str) -> str | None:
    """Return a stable HTTP(S) URL, or ``None`` for an unusable URL.

    Host/scheme casing, default ports, trailing slashes, fragments, query order,
    and common tracking parameters are normalized. Unknown query parameters are
    retained because they may identify a real posting.
    """
    raw = (url or "").strip()
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError:
        return None
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None

    try:
        host = parsed.hostname.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return None
    if ":" in host:  # IPv6 literals need brackets in a netloc.
        host = f"[{host}]"
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = host if port is None or default_port else f"{host}:{port}"

    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"
    path = _PERCENT_ESCAPE.sub(lambda match: match.group(0).upper(), path)

    query_items = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.casefold()
        if lowered.startswith("utm_") or lowered in _TRACKING_PARAMETERS:
            continue
        query_items.append((key, value))
    query_items.sort(key=lambda item: (item[0].casefold(), item[0], item[1]))
    query = urlencode(query_items, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def conservative_fingerprint(job: JobPosting) -> str | None:
    """Hash exact normalized company/title/location fields.

    All three fields are required and location remains part of the fingerprint.
    This intentionally avoids fuzzy matching, which could merge different roles
    or offices.
    """
    parts = [
        _normalize_fingerprint_part(job.get("company", "")),
        _normalize_fingerprint_part(job.get("title", "")),
        _normalize_fingerprint_part(job.get("location", "")),
    ]
    if not all(parts):
        return None
    payload = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_canonical_job_key(job: JobPosting) -> str | None:
    """Build a canonical key only when a normalized apply URL is available.

    A company/title/location fingerprint is weaker evidence and must be consumed
    separately as a review hint, never as an automatic-merge key.
    """
    if canonical_url := canonicalize_url(job.get("url", "")):
        return f"url:{canonical_url}"
    return None


def _normalize_fingerprint_part(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").casefold()
    return _SPACE.sub(" ", normalized).strip()
