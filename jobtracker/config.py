"""Central config: env loading, Notion client, and sandbox/production selection.

Safety: everything defaults to the SANDBOX database. Only an explicit
use_prod=True (via the --prod CLI flag) targets the real tracker.
"""

import os
import sys
from pathlib import Path
from typing import cast

import yaml
from dotenv import load_dotenv
from notion_client import Client

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

NOTION_VERSION = "2026-03-11"

_TOKEN = os.environ.get("NOTION_TOKEN", "").strip()
_PROD_DB = os.environ.get("NOTION_DATABASE_ID", "").strip()
_SANDBOX_DB = os.environ.get("NOTION_SANDBOX_DATABASE_ID", "").strip()


def get_notion_client() -> Client:
    """Build a Notion client from the token in .env."""
    if not _TOKEN:
        sys.exit("ERROR: NOTION_TOKEN is empty in .env")
    return Client(auth=_TOKEN, notion_version=NOTION_VERSION)


def resolve_database(use_prod: bool = False) -> tuple[str, str]:
    """Return (database_id, label). Defaults to the sandbox database."""
    if use_prod:
        if not _PROD_DB:
            sys.exit("ERROR: NOTION_DATABASE_ID (production) is empty in .env")
        return _PROD_DB, "PRODUCTION"
    if not _SANDBOX_DB:
        sys.exit("ERROR: NOTION_SANDBOX_DATABASE_ID (sandbox) is empty in .env")
    return _SANDBOX_DB, "SANDBOX"


def get_data_source_id(notion: Client, database_id: str) -> str:
    """Resolve the (first) data source id for a database.

    Notion's 2025-09-03+ API queries rows and creates pages against a data
    source, not the database directly. Our tracker has a single data source.
    """
    database = cast(dict, notion.databases.retrieve(database_id))
    sources = database.get("data_sources", [])
    if not sources:
        sys.exit(f"ERROR: database {database_id} has no data sources")
    if len(sources) > 1:
        print(f"WARNING: database has {len(sources)} data sources; using the first.")
    return sources[0]["id"]


def load_companies() -> dict:
    """Load config/companies.yaml -> {source: [board tokens]}."""
    path = _ROOT / "config" / "companies.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
