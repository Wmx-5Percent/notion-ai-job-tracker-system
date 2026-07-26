"""Runtime checks for the backward-compatible TypedDict contract."""

import unittest

from jobtracker.models import JobPosting


class JobPostingContractTests(unittest.TestCase):
    def test_new_canonical_fields_are_explicitly_optional(self):
        expected = {
            "job_kind",
            "deadline",
            "canonical_job_key",
            "discovery_method",
            "evidence_url",
            "fetched_at",
        }
        self.assertTrue(expected.issubset(JobPosting.__optional_keys__))

    def test_existing_collector_fields_remain_required(self):
        expected = {
            "source",
            "company",
            "external_job_id",
            "title",
            "location",
            "url",
            "posted_date",
            "job_description",
        }
        self.assertTrue(expected.issubset(JobPosting.__required_keys__))


if __name__ == "__main__":
    unittest.main()
