"""Entry point: collect Job Postings from every configured Source into Notion.

    python main.py --dry-run       # sandbox: print what WOULD be created (no writes)
    python main.py --limit 5       # sandbox: create at most 5 new rows
    python main.py                 # sandbox: create all new matching rows
    python main.py --prod          # production (real tracker)

This file is wiring only: resolve the Notion target, build the Source registry,
and run the collect pipeline. Discovery lives in the Collectors; the fetch ->
filter -> dedup -> write flow lives in jobtracker.pipeline.
"""

import argparse

from jobtracker import pipeline
from jobtracker.collectors.registry import build_registry
from jobtracker.config import get_data_source_id, get_notion_client, resolve_database
from jobtracker.models import JobPosting
from jobtracker.notion import create_job_page, existing_keys


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

    def sink(job: JobPosting) -> None:
        print(
            f"  + [{job.get('track', ''):6}] {job['source']}:{job['company']}: "
            f"{job['title']}  ({job['location']})"
        )
        if not args.dry_run:
            create_job_page(notion, data_source_id, job)

    result = pipeline.collect(build_registry(), seen, sink, limit=args.limit)
    if args.limit and result.created >= args.limit:
        print("  (reached --limit)")

    verb = "would create" if args.dry_run else "created"
    print(
        f"\n{verb}: {result.created} | dup-skipped: {result.dup} | "
        f"filtered-out: {result.filtered}"
    )


if __name__ == "__main__":
    main()
