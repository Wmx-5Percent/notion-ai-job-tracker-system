"""Read-only: print a data source's properties (name, type, and select/status options).

    python scripts/show_schema.py            # sandbox (default)
    python scripts/show_schema.py --prod     # production

Use it to verify a Notion schema migration was applied correctly.
"""

import argparse
import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobtracker.config import get_data_source_id, get_notion_client, resolve_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Show a Notion data source schema.")
    parser.add_argument("--prod", action="store_true", help="Production (default: sandbox).")
    args = parser.parse_args()

    notion = get_notion_client()
    database_id, label = resolve_database(use_prod=args.prod)
    data_source_id = get_data_source_id(notion, database_id)
    ds = cast(dict, notion.data_sources.retrieve(data_source_id))

    print(f"=== {label} data source {data_source_id} ===")
    for name, meta in ds.get("properties", {}).items():
        ptype = meta.get("type")
        line = f"- {name!r} ({ptype})"
        opts = meta.get(ptype, {})
        if isinstance(opts, dict) and "options" in opts:
            line += "  options: [" + ", ".join(o["name"] for o in opts["options"]) + "]"
        print(line)


if __name__ == "__main__":
    main()
