"""Shared eligibility, personal eligibility, and Track classification.

Shared eligibility catches plausible US (or Remote) CS internship / new-grad
roles. Personal degree and season restrictions are evaluated separately so one
candidate's constraints can never remove a posting from the shared pool.

The recall gate reads the title (broad intern/student words) and the JD (only
strict phrases like "currently pursuing a degree" / "which intern season"), so a
role whose signal lives only in the JD is still caught, without a full-time JD
that merely mentions "interns" in passing leaking in. Rejects read the title only.
"""

import re
from dataclasses import dataclass

from jobtracker.models import JobKind, JobPosting

# Strong internship signal (title): intern / internship / co-op.
_INTERN = re.compile(r"\b(interns?|internship|co-?op|coop)\b", re.I)

# Broad title gate: strong intern signals + student / early-career words.
_EARLY_CAREER = re.compile(
    r"\b(interns?|internship|co-?op|coop)\b"
    r"|\bstudent\b|\buniversity\b|\bcampus\b"
    r"|\bapprentice(ship)?\b|\btrainee\b"
    r"|\bsummer\s+(analyst|associate|scholar)\b"
    r"|\bworking\s+student\b|\bstudent\s+worker\b"
    r"|\bearly[-\s]?career\b"
    r"|\bentry[-\s]?level\b|\bnew\s+(college\s+)?grad(uate)?\b"
    r"|\brecent\s+(college\s+)?graduate\b|\bgraduate\s+(program|programme|role)\b"
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

# Seniority markers (title only).
_SENIOR = re.compile(
    r"\bsenior\b|\bsr\.?\b|\bstaff\b|\bprincipal\b|\blead\b|\bmanager\b|\bdirector\b"
    r"|\bvp\b|\bvice\s+president\b|\bhead\s+of\b|\bdistinguished\b|\bfellow\b",
    re.I,
)

_NEW_GRAD = re.compile(
    r"\bnew\s+(college\s+)?grad(uate)?\b|\brecent\s+(college\s+)?graduate\b"
    r"|\bgraduate\s+(software|data|machine|research|security|systems|engineer|developer|"
    r"scientist|analyst|program|programme|role)\b",
    re.I,
)
_EARLY_CAREER_KIND = re.compile(
    r"\bearly[-\s]?career\b|\bentry[-\s]?level\b|\buniversity\s+(graduate|hire)\b"
    r"|\bcampus\s+hire\b|\bapprentice(ship)?\b|\btrainee\b|\bresiden(cy|t)\b"
    r"|\bstudent\s+(worker|program|role)\b",
    re.I,
)

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

# Non-US ISO 3166-1 alpha-3 country codes. Workday writes locations like
# "Quebec, CAN - Remote" / "London, GBR" / "Bengaluru, IND", which the full-name
# _NON_US list above misses. Matched case-sensitively (uppercase) so it never
# hits English words like "can" or "are"; "USA" is the US and is excluded.
_NON_US_ISO3 = re.compile(
    r"\b(?:CAN|GBR|DEU|FRA|ESP|ITA|NLD|IRL|CHE|SWE|NOR|DNK|FIN|POL|PRT|AUT|BEL|"
    r"CZE|ROU|HUN|GRC|IND|CHN|JPN|KOR|SGP|AUS|NZL|ISR|TUR|ARE|EGY|BRA|MEX|ARG|"
    r"COL|CHL|ZAF|PHL|MYS|THA|VNM|IDN|TWN|HKG)\b"
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
    ("Security", r"security engineer|cybersecurity|information security|application security"),
    ("Systems", r"systems engineer|distributed systems|site reliability|\bsre\b|infrastructure engineer"),
    ("SWE", r"software engineer|software development engineer|\bswe\b"),
]
_TRACKS = [(name, re.compile(pat, re.I)) for name, pat in _TRACK_PATTERNS]


@dataclass(frozen=True)
class EligibilityResult:
    """A pure eligibility decision with stable, machine-readable reasons."""

    eligible: bool
    reasons: tuple[str, ...] = ()
    track: str | None = None
    job_kind: JobKind | None = None


@dataclass(frozen=True)
class PersonalCriteria:
    """Candidate-only restrictions; defaults do not narrow the shared pool."""

    allowed_job_kinds: frozenset[JobKind] | None = None
    allow_offcycle: bool = True
    phd_eligible: bool = True


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
    """Backward-compatible name for seniority markers."""
    return bool(_SENIOR.search(title or ""))


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
    return bool(
        _REMOTE.search(loc)
        and not _NON_US.search(loc)
        and not _NON_US_ISO3.search(loc)
    )


def classify_track(title: str) -> str | None:
    title = title or ""
    for name, rx in _TRACKS:
        if rx.search(title):
            return name
    return None


def classify_job_kind(title: str, jd: str = "") -> JobKind | None:
    """Classify an explicit early-career kind without inferring from seniority."""
    title = title or ""
    if re.search(r"\b(co-?op|coop)\b", title, re.I):
        return "Co-op"
    if _INTERN.search(title):
        return "Internship"
    if _NEW_GRAD.search(title):
        return "New Grad"
    if _EARLY_CAREER_KIND.search(title):
        return "Early Career"
    if _ELIGIBILITY.search(title) or _ELIGIBILITY.search(jd or ""):
        return "Internship"
    if _EARLY_CAREER.search(title):
        return "Early Career"
    return None


def shared_eligibility(job: JobPosting) -> EligibilityResult:
    """Evaluate only team-wide US/Remote CS early-career pool requirements.

    Season, degree, visa, and candidate preferences deliberately do not appear
    here. Unclassified but not clearly off-field roles are retained as ``Other``
    for high-recall manual triage.
    """
    title = job.get("title", "")
    jd = job.get("job_description", "") or ""

    if not is_us_or_remote(job.get("location", "")):
        return EligibilityResult(False, ("outside_shared_geography",))
    if is_senior_or_fulltime(title):
        return EligibilityResult(False, ("senior_role",))
    job_kind = job.get("job_kind") or classify_job_kind(title, jd)
    if job_kind is None:
        return EligibilityResult(False, ("not_early_career",))
    track = classify_track(title)
    if track is None and is_off_field(title):
        return EligibilityResult(False, ("outside_cs_scope",), job_kind=job_kind)
    return EligibilityResult(True, track=track or "Other", job_kind=job_kind)


def personal_eligibility(
    job: JobPosting,
    criteria: PersonalCriteria,
) -> EligibilityResult:
    """Apply one candidate's restrictions without changing shared eligibility."""
    shared = shared_eligibility(job)
    if not shared.eligible:
        return shared

    reasons: list[str] = []
    if criteria.allowed_job_kinds is not None and shared.job_kind not in criteria.allowed_job_kinds:
        reasons.append("job_kind_not_allowed")
    if not criteria.allow_offcycle and is_offcycle(job.get("title", "")):
        reasons.append("offcycle_for_candidate")
    if not criteria.phd_eligible and is_phd_only(job.get("title", "")):
        reasons.append("degree_requirement_not_met")
    return EligibilityResult(
        not reasons,
        tuple(reasons),
        track=shared.track,
        job_kind=shared.job_kind,
    )


def match(job: JobPosting) -> str | None:
    """Backward-compatible pipeline adapter returning only the shared Track."""
    result = shared_eligibility(job)
    return result.track if result.eligible else None
