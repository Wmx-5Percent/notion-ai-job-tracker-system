"""Entry point: collect Job Postings from every configured Source into Notion.

    python main.py --dry-run       # sandbox: print what WOULD be created (no writes)
    python main.py --limit 5       # sandbox: create at most 5 new rows
    python main.py                 # sandbox: create all new matching rows
    python main.py --prod          # production (real tracker)

This file is wiring only: resolve the Notion target, build the Source registry,
run the collect pipeline, and render live progress. Discovery lives in the
Collectors; the fetch -> filter -> dedup -> write flow lives in jobtracker.pipeline.
"""

import argparse
import sys
import time

from jobtracker import pipeline
from jobtracker.collectors.registry import build_registry
from jobtracker.config import get_data_source_id, get_notion_client, resolve_database
from jobtracker.models import JobPosting
from jobtracker.notion import create_job_page, existing_keys


class _Reporter:
    """Live CLI progress.

    On a TTY: one status line refreshes in place (which Source / company / posting
    is being scanned, plus running scanned & kept counts); each kept posting is
    printed as a permanent line above it; a summary box is printed at the end.
    Off a TTY (redirected / CI): the refreshing line is suppressed so logs stay
    clean — only the kept lines and the final summary are printed.
    """

    _SYM = {"kept": "+", "dup": "=", "skip": "-"}

    def __init__(self, label: str, dry_run: bool) -> None:
        self._label = label
        self._dry = dry_run
        self._tty = sys.stdout.isatty()
        self._company: str | None = None
        self._last = 0.0
        self._width = 0

    def _clear(self) -> None:
        if self._width:
            sys.stdout.write("\r" + " " * self._width + "\r")
            self._width = 0

    def scanning(
        self, source: str, company: str, scanned: int, kept: int, title: str, outcome: str
    ) -> None:
        if not self._tty:
            return
        now = time.monotonic()
        if company == self._company and now - self._last < 0.08:
            return  # throttle to ~12 fps within a single company
        self._company, self._last = company, now
        spin = "|/-\\"[scanned % 4]
        sym = self._SYM.get(outcome, " ")
        line = f"  {spin} [{source}] {company}  scanned={scanned} kept={kept}  {sym} {title}"[:118]
        self._clear()
        sys.stdout.write(line)
        sys.stdout.flush()
        self._width = len(line)

    def kept(self, job: JobPosting) -> None:
        self._clear()
        print(
            f"  + [{job.get('track', ''):6}] {job['source']}:{job['company']}: "
            f"{job['title']}  ({job['location']})"
        )

    def done(self, result: pipeline.CollectResult) -> None:
        self._clear()
        verb = "Would write" if self._dry else "Wrote"
        bar = "=" * 64
        print(
            f"\n{bar}\n"
            f"  {verb} {result.created} matching role(s) to {self._label}\n"
            f"  scanned {result.scanned} postings  ·  dup-skipped {result.dup}"
            f"  ·  filtered-out {result.filtered}\n"
            f"{bar}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect jobs into Notion.")
    parser.add_argument(
        "--prod", action="store_true", help="Write to the REAL tracker (default: sandbox)."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Do not write; print what would be created."
    )
    parser.add_argument("--limit", type=int, default=None, help="Max new rows to create.")
    args = parser.parse_args()

    notion = get_notion_client()
    database_id, label = resolve_database(use_prod=args.prod)
    data_source_id = get_data_source_id(notion, database_id)
    mode = "DRY RUN" if args.dry_run else "WRITE"
    print(f"=== Target: {label} | {mode} ===")

    seen = existing_keys(notion, data_source_id)
    print(f"Existing (Source, External Job ID) keys: {len(seen)}\n")

    reporter = _Reporter(label, args.dry_run)

    def sink(job: JobPosting) -> None:
        reporter.kept(job)
        if not args.dry_run:
            create_job_page(notion, data_source_id, job)

    result = pipeline.collect(
        build_registry(), seen, sink, limit=args.limit, on_scan=reporter.scanning
    )
    reporter.done(result)


if __name__ == "__main__":
    main()
