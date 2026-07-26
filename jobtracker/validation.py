"""Validation contracts for posting data obtained from untrusted sources."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from jobtracker.identity import canonicalize_url
from jobtracker.models import JobPosting


class EvidenceKind(str, Enum):
    OFFICIAL_API = "official_api"
    FETCHED_JSON_LD = "fetched_json_ld"
    FETCHED_HTML = "fetched_html"
    WEBSEARCH_SNIPPET = "websearch_snippet"
    UNTRUSTED_SUBMISSION = "untrusted_submission"


class ValidationStatus(str, Enum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    CANDIDATE_ONLY = "candidate_only"


@dataclass(frozen=True)
class PostingValidation:
    """A non-throwing decision suitable for future inbox/fallback workflows."""

    status: ValidationStatus
    reasons: tuple[str, ...] = ()

    @property
    def can_import(self) -> bool:
        return self.status is ValidationStatus.READY


def validate_posting(
    job: JobPosting,
    evidence_kind: EvidenceKind,
    *,
    detail_verified: bool = False,
) -> PostingValidation:
    """Validate a candidate without treating untrusted text as instructions.

    Search snippets are discovery hints only. JSON-LD and arbitrary submissions
    require an explicit detail-verification step before their fields may form a
    complete posting.
    """
    if evidence_kind is EvidenceKind.WEBSEARCH_SNIPPET:
        return PostingValidation(
            ValidationStatus.CANDIDATE_ONLY,
            ("websearch_snippet_requires_detail_fetch",),
        )
    if evidence_kind in {
        EvidenceKind.FETCHED_JSON_LD,
        EvidenceKind.UNTRUSTED_SUBMISSION,
    } and not detail_verified:
        return PostingValidation(
            ValidationStatus.NEEDS_REVIEW,
            ("untrusted_detail_not_verified",),
        )

    missing = _missing_minimum_fields(job)
    if missing:
        return PostingValidation(
            ValidationStatus.NEEDS_REVIEW,
            tuple(f"missing_{field}" for field in missing),
        )
    return PostingValidation(ValidationStatus.READY)


def fallback_unavailable(reason: str = "") -> PostingValidation:
    """Represent unavailable WebSearch/WebFetch explicitly, never as a posting."""
    suffix = f":{reason.strip()}" if reason.strip() else ""
    return PostingValidation(
        ValidationStatus.NEEDS_REVIEW,
        (f"fallback_unavailable{suffix}",),
    )


def _missing_minimum_fields(job: JobPosting) -> list[str]:
    missing = []
    for field in ("title", "company", "location", "job_description"):
        value = job.get(field, "")
        if not isinstance(value, str) or not value.strip():
            missing.append(field)
    if canonicalize_url(job.get("url", "")) is None:
        missing.append("url")
    return missing
