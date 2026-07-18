"""Collector entry point: fetch Greenhouse jobs, filter, dedup, write New rows.

    python main.py --dry-run       # sandbox: print what WOULD be created (no writes)
    python main.py --limit 5       # sandbox: create at most 5 new rows
    python main.py                 # sandbox: create all new matching rows
    python main.py --prod          # production (real tracker)
"""

import argparse

from jobtracker import filtering
from jobtracker.collectors import greenhouse
from jobtracker.config import (
    get_data_source_id,
    get_notion_client,
    load_companies,
    resolve_database,
)
from jobtracker.notion import create_job_page, existing_keys


def _summary(created: int, dup: int, filtered: int, errors: int, dry_run: bool) -> None:
    verb = "would create" if dry_run else "created"
    print(
        f"\n{verb}: {created} | dup-skipped: {dup} | "
        f"filtered-out: {filtered} | company-errors: {errors}"
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

    created = dup = filtered = errors = 0
    for token in load_companies().get("greenhouse", []):
        try:
            jobs = greenhouse.fetch_jobs(token)
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"  [error] {token}: {exc}")
            errors += 1
            continue
        for job in jobs:
            track = filtering.match(job)
            if not track:
                filtered += 1
                continue
            key = (job["source"], job["external_job_id"])
            if key in seen:
                dup += 1
                continue
            seen.add(key)
            job["track"] = track
            job["status"] = "New"
            print(f"  + [{track:6}] {token}: {job['title']}  ({job['location']})")
            if not args.dry_run:
                create_job_page(notion, data_source_id, job)
            created += 1
            if args.limit and created >= args.limit:
                print("  (reached --limit)")
                _summary(created, dup, filtered, errors, args.dry_run)
                return

    _summary(created, dup, filtered, errors, args.dry_run)


if __name__ == "__main__":
    main()
