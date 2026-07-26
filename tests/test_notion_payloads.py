"""Network-free tests for Notion payload construction."""

import unittest

from jobtracker.notion import (
    _MAX_TEXT_LEN,
    build_job_children,
    build_job_properties,
    create_job_page,
)


def posting(**overrides):
    job = {
        "source": "greenhouse",
        "company": "Acme",
        "external_job_id": "42",
        "title": "Software Engineer Intern",
        "location": "San Francisco, CA",
        "url": "https://jobs.example/42",
        "posted_date": "2026-07-01",
        "job_description": "Build useful software.",
        "track": "SWE",
        "status": "New",
    }
    job.update(overrides)
    return job


class NotionPayloadTests(unittest.TestCase):
    def test_property_mapping_is_pure_and_complete(self):
        job = posting()
        before = dict(job)
        properties = build_job_properties(job)

        self.assertEqual(
            properties["Job Title"]["title"][0]["text"]["content"],
            "Software Engineer Intern",
        )
        self.assertEqual(properties["Application Status"], {"status": {"name": "New"}})
        self.assertEqual(properties["URL"], {"url": "https://jobs.example/42"})
        self.assertEqual(properties["Source"], {"select": {"name": "greenhouse"}})
        self.assertEqual(properties["Posted Date"], {"date": {"start": "2026-07-01"}})
        self.assertEqual(properties["Track"], {"select": {"name": "SWE"}})
        self.assertEqual(job, before)

    def test_optional_empty_properties_are_omitted(self):
        properties = build_job_properties(
            posting(
                company="",
                status="",
                url="",
                posted_date=None,
                track="",
            )
        )
        self.assertNotIn("Company", properties)
        self.assertNotIn("Application Status", properties)
        self.assertNotIn("URL", properties)
        self.assertNotIn("Posted Date", properties)
        self.assertNotIn("Track", properties)

    def test_description_blocks_are_chunked_under_notion_limit(self):
        children = build_job_children(posting(job_description="x" * (_MAX_TEXT_LEN + 1)))
        self.assertEqual(children[0]["type"], "heading_2")
        self.assertEqual(len(children), 3)
        lengths = [
            len(block["paragraph"]["rich_text"][0]["text"]["content"])
            for block in children[1:]
        ]
        self.assertEqual(lengths, [_MAX_TEXT_LEN, 1])

    def test_create_page_only_delegates_payload_to_client(self):
        class Pages:
            def __init__(self):
                self.kwargs = None

            def create(self, **kwargs):
                self.kwargs = kwargs
                return {"id": "page"}

        class Notion:
            pages = Pages()

        notion = Notion()
        result = create_job_page(notion, "data-source", posting())
        self.assertEqual(result, {"id": "page"})
        self.assertEqual(
            notion.pages.kwargs["parent"],
            {"type": "data_source_id", "data_source_id": "data-source"},
        )
        self.assertEqual(notion.pages.kwargs["properties"], build_job_properties(posting()))
        self.assertEqual(notion.pages.kwargs["children"], build_job_children(posting()))


if __name__ == "__main__":
    unittest.main()
