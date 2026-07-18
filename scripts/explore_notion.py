"""One-off helper: validate the Notion token and print the real database schema.

Run:  python explore_notion.py

It does three things:
  1. Confirms NOTION_TOKEN in .env works (calls /users/me).
  2. Lists every database the token can see (title + id).
  3. Prints the exact properties (name + type + options) of the job database
     so we can match the write code to it precisely.

Nothing is written to Notion here. This is read-only.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client

# Load .env from the project root regardless of the current working directory.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

token = os.environ.get("NOTION_TOKEN", "").strip()
if not token:
    print("ERROR: NOTION_TOKEN is empty. Put your PAT in the .env file.")
    sys.exit(1)

# Pin a broadly-supported API version so a simple table behaves predictably.
notion = Client(auth=token, notion_version="2022-06-28")

# 1) Validate the token ----------------------------------------------------
try:
    me = notion.users.me()
    print("Auth OK.")
    print("  token user type:", me.get("type"))
    print("  token user name:", me.get("name"))
except Exception as exc:  # noqa: BLE001 - want the raw message for debugging
    print("AUTH FAILED:", exc)
    print("Check that the PAT in .env is correct and not expired.")
    sys.exit(1)

# 2) List databases the token can access -----------------------------------
print("\n--- Databases this token can see ---")
databases = []
try:
    resp = notion.search(filter={"property": "object", "value": "database"})
    for result in resp.get("results", []):
        title_parts = result.get("title", [])
        title = "".join(p.get("plain_text", "") for p in title_parts) or "(untitled)"
        databases.append((title, result["id"]))
        print(f"- {title}\n    id: {result['id']}")
except Exception as exc:  # noqa: BLE001
    print("SEARCH FAILED:", exc)

if not databases:
    print("No databases found. Make sure your Notion user can see the table.")
    sys.exit(0)

# 3) Pick the target database and print its schema -------------------------
target_id = os.environ.get("NOTION_DATABASE_ID", "").strip()
if not target_id:
    for title, db_id in databases:
        if "job" in title.lower():
            target_id = db_id
            print(f"\n(Auto-selected '{title}' as the job database.)")
            break
    if not target_id:
        target_id = databases[0][1]
        print(f"\n(Defaulting to the first database.)")

print(f"\n--- Schema for database {target_id} ---")
db = notion.databases.retrieve(target_id)
for name, meta in db.get("properties", {}).items():
    ptype = meta.get("type")
    line = f"- {name!r}  ({ptype})"
    options = meta.get(ptype, {})
    if isinstance(options, dict) and "options" in options:
        names = [o["name"] for o in options["options"]]
        line += "  options: [" + ", ".join(names) + "]"
    print(line)

print(f"\nNOTION_DATABASE_ID = {target_id}")
print("\nDone. (Read-only; nothing was created.)")
