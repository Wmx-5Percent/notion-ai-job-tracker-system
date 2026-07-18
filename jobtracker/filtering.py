"""High-recall filtering + rough Track classification for Job Postings (ADR-0004).

Hard constraints: a job must be an internship AND in the US or Remote.
Role match: if the title hits any target-track keyword, keep it and assign a
Track. High recall on purpose — noise is triaged away later with `Skip`.
"""

import re

_INTERN = re.compile(r"\b(intern|interns|internship|co-?op)\b", re.I)

# US / Remote signals in a location string.
_US_TEXT = re.compile(r"united states|u\.?s\.?a?\.?\b|\bus\b|remote", re.I)
_US_STATES = (
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO "
    "MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC"
).split()
_US_STATE = re.compile(r",\s*(?:" + "|".join(_US_STATES) + r")\b")

# Track keyword buckets, checked in order (first match wins).
_TRACK_PATTERNS = [
    ("Data", r"data scientist|data analyst|data science|data analytics|business intelligence|analytics"),
    ("MLE", r"machine learning engineer|ml engineer|mlops"),
    ("AI/LLM", r"ai engineer|applied ai|applied scientist|\bllm\b|generative|genai|\bnlp\b|deep learning|artificial intelligence|research engineer|research scientist|machine learning"),
    ("SWE", r"software engineer|software development engineer|\bswe\b"),
]
_TRACKS = [(name, re.compile(pat, re.I)) for name, pat in _TRACK_PATTERNS]


def is_internship(title: str) -> bool:
    return bool(_INTERN.search(title or ""))


def is_us_or_remote(location: str) -> bool:
    loc = location or ""
    return bool(_US_TEXT.search(loc) or _US_STATE.search(loc))


def classify_track(title: str) -> str | None:
    title = title or ""
    for name, rx in _TRACKS:
        if rx.search(title):
            return name
    return None


def match(job: dict) -> str | None:
    """Return the Track if the job passes every filter, else None."""
    if not is_internship(job.get("title", "")):
        return None
    if not is_us_or_remote(job.get("location", "")):
        return None
    return classify_track(job.get("title", ""))
