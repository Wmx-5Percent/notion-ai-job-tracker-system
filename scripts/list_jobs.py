"""Read-only: list rows in a data source with their key fields (for verification).

    python scripts/list_jobs.py            # sandbox (default)
    python scripts/list_jobs.py --prod

Shows the first 100 rows. Nothing is written.
"""

import argparse
import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobtracker.config import get_data_source_id, get_notion_client, resolve_database


def _select(prop: dict | None) -> str:
    sel = (prop or {}).get("select")
    return sel["name"] if sel else ""


def _rich(prop: dict | None) -> str:
    return "".join(t.get("plain_text", "") for t in (prop or {}).get("rich_text", []))


def _title(prop: dict | None) -> str:
    return "".join(t.get("plain_text", "") for t in (prop or {}).get("title", []))


def _status(prop: dict | None) -> str:
    st = (prop or {}).get("status")
    return st["name"] if st else ""


def _date(prop: dict | None) -> str:
    d = (prop or {}).get("date")
    return d["start"] if d else ""


def main() -> None:
    parser = argparse.ArgumentParser(description="List Notion rows with key fields.")
    parser.add_argument("--prod", action="store_true", help="Production (default: sandbox).")
    args = parser.parse_args()

    notion = get_notion_client()
    database_id, label = resolve_database(use_prod=args.prod)
    data_source_id = get_data_source_id(notion, database_id)
    resp = cast(dict, notion.data_sources.query(data_source_id=data_source_id, page_size=100))

    print(f"=== {label}: {len(resp['results'])} rows ===")
    for page in resp["results"]:
        p = page["properties"]
        print(f"- [{_status(p.get('Application Status')):9}] {_select(p.get('Track')):7} {_title(p.get('Job Title'))}")
        print(f"    source={_select(p.get('Source'))}  id={_rich(p.get('External Job ID'))}  loc={_rich(p.get('Location'))}  posted={_date(p.get('Posted Date'))}  url_set={'URL' in p and bool(p['URL'].get('url'))}")


if __name__ == "__main__":
    main()
