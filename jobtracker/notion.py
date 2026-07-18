"""Core write path: create one job row in the Notion 'Job Application Tracker'.

Given a normalized `job` dict, create a database row and write the full job
description into the page body (so the table stays clean and the full JD lives
one click away, inside the page).

This is reused by every collector later (Greenhouse / Lever / Ashby / ...).
"""

# Notion allows at most 2000 characters per rich_text object; stay under it.
_MAX_TEXT_LEN = 1900


def _rich_text(content: str) -> list:
    return [{"type": "text", "text": {"content": content}}]


def _paragraph_block(content: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": _rich_text(content)},
    }


def _heading_block(content: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": _rich_text(content)},
    }


def _jd_to_blocks(job_description: str) -> list:
    """Turn a raw job description into a heading + paragraph blocks.

    Splits on blank lines into paragraphs, and chunks any paragraph that would
    exceed Notion's per-text length limit.
    """
    blocks = [_heading_block("Job Description")]
    paragraphs = [p.strip() for p in job_description.split("\n\n") if p.strip()]
    for para in paragraphs:
        for start in range(0, len(para), _MAX_TEXT_LEN):
            blocks.append(_paragraph_block(para[start : start + _MAX_TEXT_LEN]))
    return blocks


def create_job_page(notion, data_source_id: str, job: dict) -> dict:
    """Create one job row. `job` supports keys: title (required), company,
    company_type, status, url, job_description."""
    properties = {
        "Job Title": {"title": _rich_text(job["title"])},
    }
    if job.get("company"):
        properties["Company"] = {"rich_text": _rich_text(job["company"])}
    if job.get("company_type"):
        properties["Company Type"] = {"rich_text": _rich_text(job["company_type"])}
    if job.get("status"):
        properties["Application Status"] = {"status": {"name": job["status"]}}
    if job.get("url"):
        properties["URL"] = {"url": job["url"]}

    children = _jd_to_blocks(job["job_description"]) if job.get("job_description") else []

    return notion.pages.create(
        parent={"type": "data_source_id", "data_source_id": data_source_id},
        properties=properties,
        children=children,
    )
