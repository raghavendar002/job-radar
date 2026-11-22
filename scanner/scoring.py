"""Deterministic fit score (0-100) for one job against your profile."""
import re

from . import config
from .util import age_days

_SKILLS = [(re.compile(p, re.I), w, p) for p, w in config.SKILLS.items()]
_DOMAIN = [(re.compile(p, re.I), w, p) for p, w in config.DOMAIN.items()]
_REQ = re.compile(config.TITLE_REQUIRE, re.I)
_EXC = re.compile(config.TITLE_EXCLUDE, re.I)
_WEAK = re.compile(config.TITLE_WEAK, re.I)
_STRONG = re.compile(config.TITLE_STRONG, re.I)
_SENIOR = re.compile(r"\b(senior|sr\.?|sde[- ]?(iii|3)|level 3|l5|engineer iii)\b", re.I)
_MID = re.compile(r"\b(sde[- ]?(ii|2)|engineer (ii|2)|software engineer 2|mts|member of technical staff|l4|associate)\b", re.I)

_EXP = [
    re.compile(r"(\d{1,2})\s*\+?\s*(?:-|–|to)\s*(\d{1,2})\s*\+?\s*(?:years|yrs)", re.I),
    re.compile(r"(\d{1,2})\s*\+\s*(?:years|yrs)", re.I),
    re.compile(r"(?:minimum|at least|min\.?|over)\s*(?:of\s*)?(\d{1,2})\s*(?:years|yrs)", re.I),
    re.compile(r"(\d{1,2})\s*(?:years|yrs)(?:'|’)?\s*(?:of\s*)?(?:\w+\s){0,4}experience", re.I),
]

_PRETTY = {
    r"\bjava\b": "Java", r"\bscala\b": "Scala", r"\bkotlin\b": "Kotlin", r"\bspring( boot)?\b": "Spring",
    r"\bkafka\b": "Kafka", r"\bredis\b": "Redis", r"\bmysql\b|\bpostgres(ql)?\b|\bsql\b": "SQL",
    r"\bmicro-?services?\b": "Microservices", r"\bdistributed (systems?|services?)\b": "Distributed",
    r"\bgrpc\b": "gRPC", r"\bhibernate\b|\bjpa\b": "Hibernate", r"\bjvm\b": "JVM", r"\bmongo(db)?\b": "Mongo",
    r"\bidempoten": "Idempotency", r"\bevent[- ]driven\b": "Event-driven",
    r"\bpayments?\b": "Payments", r"\bfintech\b": "Fintech", r"\bledger\b": "Ledger",
    r"\bsettlements?\b": "Settlements", r"\breconciliation\b": "Reconciliation", r"\bpayouts?\b": "Payouts",
    r"\bbilling\b": "Billing", r"\baccounting\b": "Accounting", r"\bbanking\b|\bbank\b": "Banking",
    r"\bmerchant\b": "Merchant", r"\btreasury\b": "Treasury",
}


def title_ok(title: str) -> bool:
    return bool(title) and bool(_REQ.search(title)) and not _EXC.search(title)


def min_years(text: str) -> int | None:
    best = None
    for rx in _EXP:
        for m in rx.finditer(text):
            ctx = text[max(0, m.start() - 80): m.end() + 80].lower()
            if "experience" not in ctx and "exp" not in ctx:
                continue
            try:
                n = int(m.group(1))
            except (TypeError, ValueError):
                continue
            if 0 < n <= 20:
                best = n if best is None else min(best, n)
    return best


def score(job: dict, desc: str, *, tier: int | None, partition: str) -> dict:
    title = job["title"]
    text = f"{title}\n{desc}"
    pts = 20  # passed the title gate
    why = []

    if _STRONG.search(title):
        pts += 12
    if _MID.search(title):
        pts += 4
    if _WEAK.search(title) and not re.search(r"\b(java|scala|kotlin|jvm)\b", title, re.I):
        pts -= 12
    if _SENIOR.search(title):
        pts -= 2  # often 5+ yrs; still worth a look

    matched = []
    s = 0
    for rx, w, p in _SKILLS:
        if rx.search(text):
            s += w
            matched.append(_PRETTY.get(p, p))
    pts += min(s, config.SKILL_CAP)
    if not re.search(r"\b(java|scala|kotlin|jvm|spring)\b", text, re.I):
        pts -= 8  # no JVM at all

    d = 0
    for rx, w, p in _DOMAIN:
        if rx.search(text):
            d += w
            matched.append(_PRETTY.get(p, p))
    pts += min(d, config.DOMAIN_CAP)

    yrs = min_years(desc)
    if yrs is not None:
        if yrs <= 4:
            pts += 8
        elif yrs == 5:
            pts += 2
        elif yrs == 6:
            pts -= 10
            why.append("asks 6+ yrs")
        else:
            pts -= 25
            why.append(f"asks {yrs}+ yrs")

    if tier == 1:
        pts += 10
    elif tier == 2:
        pts += 5

    age = age_days(job.get("posted_at"))
    if age is not None:
        if age <= 3:
            pts += 5
        elif age > 45:
            pts -= 8

    company = (job.get("company") or "").lower()
    if any(x in company for x in config.COMPANY_DEPRIORITIZE):
        pts -= 15
        why.append("IT services")

    if partition == "abroad":
        pts += config.TARGET_COUNTRIES.get(job.get("place"), 0)
        sp = job.get("sponsorship")
        if sp == "confirmed":
            pts += 10
        elif sp == "likely":
            pts += 5
        else:
            pts -= 12
        if job.get("language"):
            pts -= 30
            why.append(f"needs {job['language']}")

    return {
        "score": max(0, min(100, int(round(pts)))),
        "skills": list(dict.fromkeys(matched))[:10],
        "min_years": yrs,
        "flags": why,
    }
