"""Read-only: inspect the filter funnel and show which intern roles get dropped
and why, so we can tune recall.

    python scripts/inspect_filter.py

Nothing is written. Slow (scans every company).
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobtracker import filtering
from jobtracker.collectors import greenhouse
from jobtracker.config import load_companies


def main() -> None:
    total = intern = eligible = us = kept = 0
    dropped_locations: Counter = Counter()
    dropped_phd = 0
    dropped_offcycle = 0
    kept_samples = []

    for token in load_companies().get("greenhouse", []):
        try:
            jobs = greenhouse.fetch_jobs(token)
        except Exception as exc:  # noqa: BLE001
            print(f"[error] {token}: {type(exc).__name__}")
            continue
        for job in jobs:
            total += 1
            title = job["title"]
            if not filtering.is_internship(title):
                continue
            intern += 1
            if filtering.is_phd_only(title):
                dropped_phd += 1
                continue
            if filtering.is_offcycle(title):
                dropped_offcycle += 1
                continue
            eligible += 1
            if filtering.is_us_or_remote(job["location"]):
                us += 1
                track = filtering.classify_track(title)
                if track:
                    kept += 1
                    if len(kept_samples) < 25:
                        kept_samples.append(f"[{track}] {token}: {title} ({job['location']})")
            else:
                dropped_locations[job["location"]] += 1

    print(
        f"total={total} intern={intern} dropped_phd={dropped_phd} "
        f"dropped_offcycle={dropped_offcycle} eligible={eligible} +US={us} kept={kept}"
    )
    print("\n-- top dropped-intern locations (eligible but failed US filter) --")
    for loc, n in dropped_locations.most_common(30):
        print(f"  {n:3}  {loc!r}")
    print("\n-- kept samples --")
    for s in kept_samples:
        print(" ", s)


if __name__ == "__main__":
    main()
