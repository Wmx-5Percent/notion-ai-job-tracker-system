"""High-recall filtering + rough Track classification for Job Postings (ADR-0004).

Hard constraints: a job must be an internship AND in the US or Remote.
Role match: if the title hits any target-track keyword, keep it and assign a
Track. High recall on purpose — noise is triaged away later with `Skip`.
"""

import re

_INTERN = re.compile(r"\b(intern|interns|internship|co-?op)\b", re.I)

# Degree ineligibility: PhD-only roles (user is an incoming MS student). Kept if
# the title also welcomes Master's / MS.
_PHD = re.compile(r"\bph\.?\s?d\b|\bdoctoral\b|\bdoctorate\b", re.I)
_MASTERS = re.compile(r"master|\bmsc?\b", re.I)

# Off-cycle seasons: user needs Summer only (intl student, ~1 year before CPT/OPT).
# Summer or season-unspecified titles are kept; explicit fall/spring/winter dropped.
_OFFCYCLE = re.compile(
    r"\b(fall|autumn|winter)\b|\bspring\s+(?:\d{4}|intern|co-?op|semester|quarter|term)",
    re.I,
)

# US / Remote signals in a location string.
_US_TEXT = re.compile(r"united states|u\.?s\.?a?\.?\b|\bus\b|remote", re.I)
_US_STATES = (
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO "
    "MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC"
).split()
_US_STATE = re.compile(r",\s*(?:" + "|".join(_US_STATES) + r")\b")

# Full US state names (some boards write "California" instead of "CA").
_US_STATE_NAMES = (
    "Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|"
    "Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|"
    "Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|"
    "New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|"
    "Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|"
    "Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming|"
    "District of Columbia"
)
_US_STATE_NAME = re.compile(r"\b(?:" + _US_STATE_NAMES + r")\b", re.I)

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


def is_phd_only(title: str) -> bool:
    """PhD-targeted role that does not also welcome Master's students."""
    t = title or ""
    return bool(_PHD.search(t)) and not _MASTERS.search(t)


def is_offcycle(title: str) -> bool:
    """Explicit non-summer season in the title (fall / spring / winter)."""
    return bool(_OFFCYCLE.search(title or ""))


def is_us_or_remote(location: str) -> bool:
    loc = location or ""
    return bool(_US_TEXT.search(loc) or _US_STATE.search(loc) or _US_STATE_NAME.search(loc))


def classify_track(title: str) -> str | None:
    title = title or ""
    for name, rx in _TRACKS:
        if rx.search(title):
            return name
    return None


def match(job: dict) -> str | None:
    """Return the Track if the job passes every filter, else None.

    Hard constraints: internship, not PhD-only, not an off-cycle (non-summer)
    season, and US/Remote.
    """
    title = job.get("title", "")
    if not is_internship(title):
        return None
    if is_phd_only(title):
        return None
    if is_offcycle(title):
        return None
    if not is_us_or_remote(job.get("location", "")):
        return None
    return classify_track(title)
