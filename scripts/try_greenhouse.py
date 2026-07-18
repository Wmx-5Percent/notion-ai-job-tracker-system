"""Read-only: fetch every company in config/companies.yaml via Greenhouse and
print a validation summary (which tokens work, job counts, a sample title).

    python scripts/try_greenhouse.py

Nothing is written to Notion.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobtracker.collectors import greenhouse
from jobtracker.config import load_companies


def main() -> None:
    tokens = load_companies().get("greenhouse", [])
    print(f"Greenhouse tokens to check: {len(tokens)}\n")

    valid, invalid, total = [], [], 0
    for token in tokens:
        try:
            jobs = greenhouse.fetch_jobs(token)
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"  [error] {token}: {exc}")
            invalid.append(token)
            continue
        if not jobs:
            print(f"  [skip]  {token}: no jobs / invalid token")
            invalid.append(token)
            continue
        valid.append(token)
        total += len(jobs)
        print(f"  [ok]    {token}: {len(jobs)} jobs (e.g. {jobs[0]['title']!r})")

    print(f"\nValid: {len(valid)} | Invalid/empty: {len(invalid)} | Total jobs: {total}")


if __name__ == "__main__":
    main()
