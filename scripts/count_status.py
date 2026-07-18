"""Read-only: count rows by Application Status in a Notion database.

    python scripts/count_status.py            # sandbox (default)
    python scripts/count_status.py --prod     # real tracker

Nothing is written. Used to check the status distribution before schema changes.
"""

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobtracker.config import get_data_source_id, get_notion_client, resolve_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Count rows by Application Status.")
    parser.add_argument(
        "--prod", action="store_true", help="Count the real tracker (default: sandbox)."
    )
    args = parser.parse_args()

    notion = get_notion_client()
    database_id, label = resolve_database(use_prod=args.prod)
    data_source_id = get_data_source_id(notion, database_id)
    print(f"=== Counting Application Status in: {label} ===")
    print(f"    {data_source_id}\n")

    counts: Counter = Counter()
    total = 0
    cursor = None
    while True:
        kwargs = {"data_source_id": data_source_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = cast(dict, notion.data_sources.query(**kwargs))
        for page in resp["results"]:
            total += 1
            status = page["properties"].get("Application Status", {}).get("status")
            counts[status["name"] if status else "(empty)"] += 1
        if resp.get("has_more"):
            cursor = resp["next_cursor"]
        else:
            break

    print(f"Total rows: {total}")
    for name, n in counts.most_common():
        print(f"  {n:>4}  {name}")


if __name__ == "__main__":
    main()
