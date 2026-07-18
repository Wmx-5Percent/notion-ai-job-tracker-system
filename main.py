"""Step 1 smoke test: create ONE test job in the Notion tracker.

Run:  python main.py

Then open Notion -> Job Application Tracker. A row prefixed with 【TEST】 should
appear; clicking it shows the Job Description inside the page body.
"""

import os
import sys

from dotenv import load_dotenv
from notion_client import Client

from notion_job import create_job_page

load_dotenv()

token = os.environ.get("NOTION_TOKEN", "").strip()
database_id = os.environ.get("NOTION_DATABASE_ID", "").strip()

if not token:
    sys.exit("ERROR: NOTION_TOKEN is empty in .env")
if not database_id:
    sys.exit("ERROR: NOTION_DATABASE_ID is empty in .env")

notion = Client(auth=token, notion_version="2022-06-28")

test_job = {
    "title": "【TEST】Machine Learning Engineer Intern",
    "company": "Example AI",
    "company_type": "Startup",
    "status": "Not started",
    "url": "https://example.com/jobs/123",
    "job_description": (
        "We are looking for a Machine Learning Engineer Intern to join our team.\n\n"
        "Responsibilities\n"
        "- Build and evaluate machine learning models\n"
        "- Work with large, real-world datasets\n\n"
        "Qualifications\n"
        "- Currently pursuing an MS in Computer Science or related field\n"
        "- Experience with Python and PyTorch\n"
    ),
}

page = create_job_page(notion, database_id, test_job)
print("Created test job page:")
print("  ", page.get("url"))
print("\nOpen your Notion 'Job Application Tracker' to see the 【TEST】 row.")
