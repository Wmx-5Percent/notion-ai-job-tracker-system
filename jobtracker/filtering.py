"""High-recall filtering + rough Track classification for Job Postings (ADR-0004).

Goal: catch every plausible US (or Remote) internship / student / early-career
role in our target fields, and drop clear full-time, senior, or off-field noise.
Recall first; leftover noise is triaged with `Skip` in Notion.

The recall gate reads the title (broad intern/student words) and the JD (only
strict phrases like "currently pursuing a degree" / "which intern season"), so a
role whose signal lives only in the JD is still caught, without a full-time JD
that merely mentions "interns" in passing leaking in. Rejects read the title only.
"""

import re

# Strong internship signal (title): intern / internship / co-op.
_INTERN = re.compile(r"\b(interns?|internship|co-?op|coop)\b", re.I)

# Broad early-career gate: strong intern signals + student / early-career words.
# Matched against title + JD, so JD-only student roles are still caught.
_EARLY_CAREER = re.compile(
    r"\b(interns?|internship|co-?op|coop)\b"
    r"|\bstudent\b|\buniversity\b|\bcampus\b"
    r"|\bapprentice(ship)?\b|\btrainee\b"
    r"|\bsummer\s+(analyst|associate|scholar)\b"
    r"|\bworking\s+student\b|\bstudent\s+worker\b"
    r"|\bearly[-\s]?career\b"
    r"|\b(ai|ml|research|data|software)\s+resident\b|\bresidency\b"
    r"|\bindustrial\s+placement\b|\bplacement\s+year\b",
    re.I,
)

# JD-only eligibility signals: the title lacks an intern/student word but the
# description reveals a student program (the Neuralink "which season?" case).
# Kept deliberately narrow: generic phrases ("enrolled in", "graduation date",
# "summer 2027", "10 weeks") also appear in full-time JDs and cause false keeps.
_ELIGIBILITY = re.compile(
    r"currently\s+pursuing\s+(a|an|your)?\s*(bachelor|master|b\.?s\.?|m\.?s\.?|undergraduate|graduate\s+degree)"
    r"|rising\s+(sophomore|junior|senior)"
    r"|return(ing)?\s+to\s+(school|campus|university)"
    r"|intern(ship)?\s+(season|cohort)"
    r"|(which|what)\s+(intern(ship)?\s+)?season",
    re.I,
)

# Full-time / seniority markers (title only): not a Summer-2027 internship.
_SENIOR = re.compile(
    r"\bsenior\b|\bsr\.?\b|\bstaff\b|\bprincipal\b|\blead\b|\bmanager\b|\bdirector\b"
    r"|\bvp\b|\bvice\s+president\b|\bhead\s+of\b|\bdistinguished\b|\bfellow\b"
    r"|\bnew\s+(college\s+)?grad(uate)?\b|\brecent\s+(college\s+)?graduate\b",
    re.I,
)

# "Graduate <role>" (e.g. "Graduate Software Engineer, 2027 start") is a new-grad
# full-time program, not an internship. Reject bare "graduate" unless the title
# also carries an intern / student / research word.
_GRADUATE = re.compile(r"\bgraduate\b", re.I)
_STUDENTISH = re.compile(r"\b(interns?|internship|co-?op|coop|student|research|ph\.?d)\b", re.I)

# Off-field role functions (title only). Only rejects when NO target-track
# keyword is present, so "Data Analyst Intern, Finance" (a Data role) survives.
_OFF_FIELD = re.compile(
    r"\brecruit(er|ing|ment)?\b|\bsales\b|\baccount\s+(executive|development|manager)\b"
    r"|\b(business|sales)\s+development\b|\b(sdr|bdr)\b|\brepresentative\b"
    r"|\bmarketing\b|\bhuman\s+resources\b|\bhr\b|\bpeople\s+operations\b|\btalent\b"
    r"|\bfinance\b|\bfinancial\b|\baccounting\b|\blegal\b|\bcounsel\b|\bparalegal\b"
    r"|\bcommunications\b|\bpublic\s+relations\b|\bsupply\s+chain\b|\bprocurement\b"
    r"|\bcustomer\s+success\b|\bclinical\b|\bphysician\b|\bnurse\b|\bmechanical\b"
    r"|\belectrical\b|\bhardware\b|\bfirmware\b",
    re.I,
)

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

# US / Remote signals in a location string. "remote" alone is treated as US only
# when no non-US locale is named (see is_us_or_remote), so "Remote - Germany" is
# not mistaken for a US role.
_US_TEXT = re.compile(r"united states|u\.?s\.?a?\.?\b|\bus\b", re.I)
_REMOTE = re.compile(r"\bremote\b", re.I)
_NON_US = re.compile(
    r"\b("
    r"netherlands|germany|deutschland|united\s+kingdom|england|scotland|ireland|"
    r"france|spain|portugal|italy|poland|sweden|norway|denmark|finland|switzerland|"
    r"austria|belgium|luxembourg|czechia|romania|hungary|greece|"
    r"canada|brazil|argentina|colombia|chile|"
    r"india|china|japan|korea|singapore|australia|new\s+zealand|"
    r"israel|turkey|uae|dubai|egypt|nigeria|kenya|south\s+africa|"
    r"benelux|dach|emea|apac|latam|europe|asia|uk|eu"
    r")\b",
    re.I,
)
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
    """Strong internship signal in the title (intern / co-op)."""
    return bool(_INTERN.search(title or ""))


def has_early_career_signal(title: str, jd: str = "") -> bool:
    """Early-career signal: a broad word in the TITLE, or a strict intern-specific
    phrase in the title / JD.

    Broad words (intern / student / university / campus) are matched on the TITLE
    only; a full-time JD that mentions "interns" or "universities" in passing must
    not qualify. The JD counts only via the strict _ELIGIBILITY phrases (e.g.
    "currently pursuing a degree", "which intern season").
    """
    title = title or ""
    return bool(
        _EARLY_CAREER.search(title)
        or _ELIGIBILITY.search(title)
        or _ELIGIBILITY.search(jd or "")
    )


def is_senior_or_fulltime(title: str) -> bool:
    """Seniority / full-time markers that rule out a Summer-2027 internship.

    Also rejects new-grad "graduate" programs (e.g. "Graduate Software Engineer,
    2027 start") unless the title also carries an intern / student word.
    """
    t = title or ""
    if _SENIOR.search(t):
        return True
    return bool(_GRADUATE.search(t) and not _STUDENTISH.search(t))


def is_off_field(title: str) -> bool:
    """A clearly non-technical role function (sales / HR / finance / ...)."""
    return bool(_OFF_FIELD.search(title or ""))


def is_phd_only(title: str) -> bool:
    """PhD-targeted role that does not also welcome Master's students."""
    t = title or ""
    return bool(_PHD.search(t)) and not _MASTERS.search(t)


def is_offcycle(title: str) -> bool:
    """Explicit non-summer season in the title (fall / spring / winter)."""
    return bool(_OFFCYCLE.search(title or ""))


def is_us_or_remote(location: str) -> bool:
    """US location, or remote that is not tied to a non-US locale.

    A US state / "United States" / "US" always qualifies (so a multi-location
    posting that includes a US site is kept). Bare "remote" qualifies only when
    no non-US country/region is named (so "Remote - Germany" is dropped).
    """
    loc = location or ""
    if _US_TEXT.search(loc) or _US_STATE.search(loc) or _US_STATE_NAME.search(loc):
        return True
    return bool(_REMOTE.search(loc) and not _NON_US.search(loc))


def classify_track(title: str) -> str | None:
    title = title or ""
    for name, rx in _TRACKS:
        if rx.search(title):
            return name
    return None


def match(job: dict) -> str | None:
    """Return a Track if the job is a plausible US Summer-2027 early-career role
    in our fields, else None.

    High recall: the early-career gate reads title + job description, and an
    in-field role we cannot classify is kept as `Other` for manual triage.
    Rejects (senior / off-field / PhD-only / off-cycle) read the title only.
    """
    title = job.get("title", "")
    jd = job.get("job_description", "") or ""

    if not is_us_or_remote(job.get("location", "")):
        return None
    if is_senior_or_fulltime(title):
        return None
    if is_phd_only(title):
        return None
    if is_offcycle(title):
        return None
    track = classify_track(title)
    if track is None and is_off_field(title):
        return None
    if not has_early_career_signal(title, jd):
        return None
    return track or "Other"
