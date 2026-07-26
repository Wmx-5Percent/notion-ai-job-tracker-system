"""Contracts preventing discovery hints from becoming complete postings."""

import unittest

from jobtracker.validation import (
    EvidenceKind,
    ValidationStatus,
    fallback_unavailable,
    validate_posting,
)


def complete_posting():
    return {
        "source": "public-web",
        "company": "Acme",
        "external_job_id": "candidate-1",
        "title": "Software Engineer Intern",
        "location": "Remote, US",
        "url": "https://jobs.example/1",
        "posted_date": None,
        "job_description": "A complete fetched job description.",
    }


class UntrustedPostingTests(unittest.TestCase):
    def test_websearch_snippet_is_candidate_only_even_if_fields_look_complete(self):
        result = validate_posting(
            complete_posting(),
            EvidenceKind.WEBSEARCH_SNIPPET,
        )
        self.assertEqual(result.status, ValidationStatus.CANDIDATE_ONLY)
        self.assertFalse(result.can_import)

    def test_json_ld_cannot_import_without_detail_verification(self):
        unverified = validate_posting(
            complete_posting(),
            EvidenceKind.FETCHED_JSON_LD,
        )
        verified = validate_posting(
            complete_posting(),
            EvidenceKind.FETCHED_JSON_LD,
            detail_verified=True,
        )
        self.assertEqual(unverified.status, ValidationStatus.NEEDS_REVIEW)
        self.assertFalse(unverified.can_import)
        self.assertTrue(verified.can_import)

    def test_untrusted_submission_cannot_self_assert_completeness(self):
        result = validate_posting(
            complete_posting(),
            EvidenceKind.UNTRUSTED_SUBMISSION,
        )
        self.assertEqual(result.status, ValidationStatus.NEEDS_REVIEW)

    def test_verified_detail_still_requires_minimum_fields(self):
        incomplete = complete_posting()
        incomplete["job_description"] = ""
        incomplete["url"] = "javascript:alert(1)"
        result = validate_posting(
            incomplete,
            EvidenceKind.FETCHED_HTML,
            detail_verified=True,
        )
        self.assertEqual(result.status, ValidationStatus.NEEDS_REVIEW)
        self.assertIn("missing_job_description", result.reasons)
        self.assertIn("missing_url", result.reasons)

    def test_fallback_unavailable_is_explicit_and_not_importable(self):
        result = fallback_unavailable("tool missing")
        self.assertEqual(result.status, ValidationStatus.NEEDS_REVIEW)
        self.assertEqual(result.reasons, ("fallback_unavailable:tool missing",))
        self.assertFalse(result.can_import)


if __name__ == "__main__":
    unittest.main()
