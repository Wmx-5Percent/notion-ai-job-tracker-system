"""The Source registry: the one place that lists every Collector.

Adding a Source (a new ATS like Ashby / Lever, or later a web-crawler Collector)
= write one adapter that satisfies ``Collector`` and add one line here. Nothing
else: ``main`` and the pipeline never name a Source.
"""

from jobtracker.collectors.base import Collector
from jobtracker.collectors.greenhouse import GreenhouseCollector
from jobtracker.config import load_companies


def build_registry() -> list[Collector]:
    """Build every configured Collector. One line per Source."""
    cfg = load_companies()
    return [
        GreenhouseCollector(cfg.get("greenhouse", [])),
        # AshbyCollector(cfg.get("ashby", [])),     # <- add a Source in one line
        # LeverCollector(cfg.get("lever", [])),
        # CrawlerCollector(cfg.get("crawl", [])),   # future: official-site scraping
    ]
