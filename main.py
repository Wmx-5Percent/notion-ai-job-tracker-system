"""Smoke test entry point: create ONE test job in Notion.

Default target is the SANDBOX database. Pass --prod for the real tracker.

    python main.py           # -> sandbox
    python main.py --prod    # -> production (real tracker)
"""

import argparse

from jobtracker.config import get_notion_client, resolve_database
from jobtracker.notion import create_job_page


def build_test_job() -> dict:
    return {
        "title": "[TEST] Machine Learning Engineer Intern",
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a test job in Notion.")
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Write to the REAL tracker. Default is the sandbox.",
    )
    args = parser.parse_args()

    notion = get_notion_client()
    database_id, label = resolve_database(use_prod=args.prod)

    print(f"=== Target database: {label} ===")
    print(f"    {database_id}")

    page = create_job_page(notion, database_id, build_test_job())
    print("\nCreated test job page:")
    print("  ", page.get("url"))


if __name__ == "__main__":
    main()
