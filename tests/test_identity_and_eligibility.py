"""Pure contract tests for shared identity and eligibility boundaries."""

import unittest

from jobtracker import filtering
from jobtracker.identity import (
    build_canonical_job_key,
    canonicalize_url,
    conservative_fingerprint,
)


def posting(**overrides):
    job = {
        "source": "greenhouse",
        "company": "Acme",
        "external_job_id": "123",
        "title": "Software Engineer Intern",
        "location": "Remote, US",
        "url": "https://jobs.example.com/apply/123",
        "posted_date": None,
        "job_description": "",
    }
    job.update(overrides)
    return job


class UrlIdentityTests(unittest.TestCase):
    def test_url_query_and_tracking_parameters_are_normalized(self):
        first = (
            "HTTPS://Jobs.Example.COM:443/apply/123/"
            "?utm_source=mail&team=core&gh_src=abc&lang=en#description"
        )
        second = "https://jobs.example.com/apply/123?lang=en&team=core"
        self.assertEqual(canonicalize_url(first), second)

    def test_unknown_query_parameters_are_preserved(self):
        self.assertNotEqual(
            canonicalize_url("https://jobs.example/apply?id=1"),
            canonicalize_url("https://jobs.example/apply?id=2"),
        )

    def test_invalid_or_credentialed_urls_are_rejected(self):
        self.assertIsNone(canonicalize_url("javascript:alert(1)"))
        self.assertIsNone(canonicalize_url("https://user:secret@example.com/job"))

    def test_same_verified_official_url_has_same_key_across_sources(self):
        greenhouse = posting(
            source="greenhouse",
            url="https://jobs.example.com/apply/123?utm_campaign=summer",
        )
        discovered_elsewhere = posting(
            source="aggregator",
            external_job_id="different",
            url="https://JOBS.example.com:443/apply/123/#top",
        )
        self.assertEqual(
            build_canonical_job_key(greenhouse, official_url_verified=True),
            build_canonical_job_key(discovered_elsewhere, official_url_verified=True),
        )

    def test_unverified_official_aggregator_and_search_urls_never_form_keys(self):
        urls = [
            "https://jobs.example.com/apply/123",
            "https://www.indeed.com/viewjob?jk=abc123",
            "https://www.google.com/url?q=https%3A%2F%2Fjobs.example.com%2Fapply%2F123",
        ]
        for url in urls:
            with self.subTest(url=url):
                job = posting(source="aggregator", url=url)
                self.assertIsNotNone(canonicalize_url(url))
                self.assertIsNone(build_canonical_job_key(job))

    def test_fingerprint_does_not_merge_different_role_or_location(self):
        base = posting(url="")
        other_role = posting(url="", title="Data Science Intern")
        other_location = posting(url="", location="Austin, TX")
        self.assertNotEqual(conservative_fingerprint(base), conservative_fingerprint(other_role))
        self.assertNotEqual(conservative_fingerprint(base), conservative_fingerprint(other_location))

    def test_fingerprint_is_review_hint_not_canonical_key(self):
        job = posting(url="")
        self.assertIsNotNone(conservative_fingerprint(job))
        self.assertIsNone(build_canonical_job_key(job))

    def test_incomplete_fingerprint_is_not_guessed(self):
        self.assertIsNone(conservative_fingerprint(posting(url="", location="")))
        self.assertIsNone(build_canonical_job_key(posting(url="", company="")))


class EligibilityBoundaryTests(unittest.TestCase):
    def test_shared_pool_accepts_cs_internship_and_new_grad(self):
        internship = filtering.shared_eligibility(posting())
        new_grad = filtering.shared_eligibility(
            posting(title="New Grad Software Engineer", location="New York, NY")
        )
        self.assertTrue(internship.eligible)
        self.assertEqual(internship.job_kind, "Internship")
        self.assertTrue(new_grad.eligible)
        self.assertEqual(new_grad.job_kind, "New Grad")

    def test_shared_pool_accepts_qualifying_remote_role(self):
        result = filtering.shared_eligibility(
            posting(title="Data Science Co-op", location="Remote")
        )
        self.assertTrue(result.eligible)
        self.assertEqual(result.job_kind, "Co-op")

    def test_shared_pool_rejects_non_us_and_non_cs_noise(self):
        non_us = filtering.shared_eligibility(posting(location="Remote - Germany"))
        marketing = filtering.shared_eligibility(posting(title="Marketing Intern"))
        self.assertFalse(non_us.eligible)
        self.assertFalse(marketing.eligible)

    def test_personal_degree_and_season_rules_do_not_pollute_shared_pool(self):
        job = posting(title="Fall PhD Software Engineer Intern")
        shared_before = filtering.shared_eligibility(job)
        personal = filtering.personal_eligibility(
            job,
            filtering.PersonalCriteria(allow_offcycle=False, phd_eligible=False),
        )
        shared_after = filtering.shared_eligibility(job)

        self.assertTrue(shared_before.eligible)
        self.assertFalse(personal.eligible)
        self.assertEqual(
            set(personal.reasons),
            {"offcycle_for_candidate", "degree_requirement_not_met"},
        )
        self.assertEqual(shared_before, shared_after)


if __name__ == "__main__":
    unittest.main()
