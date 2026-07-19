"""The Source registry: map each configured company to its Collector.

Companies are declared in config/companies.yaml as {name, ats, id} rows. This
groups them by ``ats`` and builds one Collector per ATS via the factory below.
Adding a Source = build the adapter + add one line to ``_FACTORIES``; ``main`` and
the pipeline never name a Source.
"""

from collections import defaultdict

from jobtracker.collectors.ashby import AshbyCollector
from jobtracker.collectors.base import Collector
from jobtracker.collectors.greenhouse import GreenhouseCollector
from jobtracker.collectors.lever import LeverCollector
from jobtracker.collectors.workday import WorkdayCollector
from jobtracker.config import load_companies

# ats name -> Collector adapter. Each adapter takes the list of `id`s for its ATS.
_FACTORIES = {
    "greenhouse": GreenhouseCollector,
    "ashby": AshbyCollector,
    "lever": LeverCollector,
    "workday": WorkdayCollector,
    # "official": OfficialCollector,  # structured id: {url, ...} (web crawler)
}


def build_registry() -> list[Collector]:
    """Group the company registry by ATS and build one Collector per ATS."""
    ids_by_ats: dict[str, list] = defaultdict(list)
    for row in load_companies():
        ats, cid = row.get("ats"), row.get("id")
        if ats and cid is not None:
            ids_by_ats[ats].append(cid)
    collectors: list[Collector] = []
    for ats, ids in ids_by_ats.items():
        factory = _FACTORIES.get(ats)
        if factory is None:
            print(f"  [skip] no collector for ats={ats!r} ({len(ids)} companies)")
            continue
        collectors.append(factory(ids))
    return collectors
