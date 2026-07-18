"""Central config: env loading, Notion client, and sandbox/production selection.

Safety: everything defaults to the SANDBOX database. Only an explicit
use_prod=True (via the --prod CLI flag) targets the real tracker.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

NOTION_VERSION = "2022-06-28"

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
