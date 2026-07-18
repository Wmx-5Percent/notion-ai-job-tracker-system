"""Tests for the collect pipeline, using a fake Collector and a fake sink so the
whole fetch -> filter -> dedup -> write flow runs without a network or Notion.

Run directly (no pytest needed):  .venv/bin/python tests/test_pipeline.py
Or with pytest if installed:       .venv/bin/python -m pytest tests/
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobtracker import pipeline


class FakeCollector:
    """A Collector adapter that yields a fixed list of postings (no network)."""

    def __init__(self, source: str, jobs: list[dict]) -> None:
        self.source = source
        self._jobs = jobs

    def fetch_jobs(self):
        return list(self._jobs)


def _job(source, jid, title, location="San Francisco, CA", jd=""):
    return {
        "source": source,
        "company": "acme",
        "external_job_id": jid,
        "title": title,
        "location": location,
        "url": "",
        "posted_date": None,
        "job_description": jd,
    }


def test_filters_dedups_and_writes():
    collectors = [
        FakeCollector(
            "greenhouse",
            [
                _job("greenhouse", "1", "Software Engineer Intern"),           # keep -> SWE
                _job("greenhouse", "2", "Senior Software Engineer"),           # drop (senior)
                _job("greenhouse", "3", "Data Science Intern", "Chicago, IL"), # dup (in seen)
                _job("greenhouse", "4", "Marketing Intern", "New York, NY"),   # drop (off-field)
            ],
        )
    ]
    seen = {("greenhouse", "3")}
    written = []
    result = pipeline.collect(collectors, seen, written.append)

    assert result.created == 1, result
    assert result.dup == 1, result
    assert result.filtered == 2, result
    assert [j["external_job_id"] for j in written] == ["1"]
    assert written[0]["track"] == "SWE"
    assert written[0]["status"] == "New"
    assert ("greenhouse", "1") in seen  # seen updated in place


def test_limit_stops_early():
    collectors = [
        FakeCollector(
            "greenhouse",
            [
                _job("greenhouse", "1", "Software Engineer Intern"),
                _job("greenhouse", "2", "Data Science Intern"),
                _job("greenhouse", "3", "Machine Learning Intern"),
            ],
        )
    ]
    written = []
    result = pipeline.collect(collectors, set(), written.append, limit=2)
    assert result.created == 2, result
    assert len(written) == 2


def test_jd_only_signal_is_caught():
    # Title has no intern word; the JD reveals a student program (the Neuralink case).
    collectors = [
        FakeCollector(
            "greenhouse",
            [
                _job(
                    "greenhouse",
                    "9",
                    "Software Engineer",
                    jd="Currently pursuing a Bachelor degree. Which intern season are you interested in?",
                )
            ],
        )
    ]
    written = []
    result = pipeline.collect(collectors, set(), written.append)
    assert result.created == 1, result
    assert written[0]["track"] == "SWE"


def test_multiple_sources_all_scanned_and_keyed_by_source():
    # Same external id on two Sources -> both kept (identity is source + id, ADR-0003).
    collectors = [
        FakeCollector("greenhouse", [_job("greenhouse", "1", "Data Science Intern")]),
        FakeCollector("ashby", [_job("ashby", "1", "Software Engineer Intern")]),
    ]
    written = []
    result = pipeline.collect(collectors, set(), written.append)
    assert result.created == 2, result
    assert {(j["source"], j["external_job_id"]) for j in written} == {
        ("greenhouse", "1"),
        ("ashby", "1"),
    }


def test_one_failing_source_does_not_stop_the_rest():
    class BoomCollector:
        source = "boom"

        def fetch_jobs(self):
            raise RuntimeError("network down")

    collectors = [
        BoomCollector(),
        FakeCollector("greenhouse", [_job("greenhouse", "1", "Data Science Intern")]),
    ]
    written = []
    result = pipeline.collect(collectors, set(), written.append)
    assert result.created == 1, result
    assert written[0]["source"] == "greenhouse"


def _run():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in tests:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\nall {len(tests)} pipeline tests passed")


if __name__ == "__main__":
    _run()
