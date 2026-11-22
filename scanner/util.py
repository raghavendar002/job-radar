import html
import re
import threading
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

_local = threading.local()


def session() -> requests.Session:
    """One retrying session per thread."""
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        retry = Retry(total=3, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=frozenset(["GET", "POST"]), respect_retry_after_header=True)
        s.mount("https://", HTTPAdapter(max_retries=retry, pool_maxsize=16))
        s.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
        _local.s = s
    return s


_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f\v]+")


def html_to_text(s: str | None) -> str:
    if not s:
        return ""
    s = html.unescape(s)               # Greenhouse double-escapes
    s = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</div>|</h\d>", "\n", s)
    s = _TAG.sub(" ", s)
    s = html.unescape(s)
    s = _WS.sub(" ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


def norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def to_iso(v) -> str | None:
    """Accepts epoch ms, epoch s, or ISO strings."""
    if v in (None, ""):
        return None
    try:
        if isinstance(v, (int, float)):
            if v > 1e12:
                v = v / 1000
            return datetime.fromtimestamp(v, timezone.utc).replace(microsecond=0).isoformat()
        s = str(v).strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            s += "T00:00:00+00:00"
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except Exception:
        return None


def age_days(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(iso)).total_seconds() / 86400
    except Exception:
        return None


_SAL = re.compile(
    r"(?:(?:US|CA|AU|SG|S)?\$|€|£|₹|\b(?:USD|EUR|GBP|SGD|CAD|AUD|CHF|AED|INR)\s?)"
    r"\s?\d[\d,\.]*\s?[kK]?\s?(?:-|–|—|to)\s?(?:(?:US|CA|AU|SG|S)?\$|€|£|₹|USD|EUR|GBP)?\s?\d[\d,\.]*\s?[kK]?"
    r"(?:\s?(?:USD|EUR|GBP|SGD|CAD|AUD|CHF|AED|INR|LPA))?"
)


def find_salary(text: str) -> str | None:
    m = _SAL.search(text or "")
    if not m:
        return None
    s = m.group(0).strip()
    digits = re.sub(r"\D", "", s)
    return s if len(digits) >= 4 else None
