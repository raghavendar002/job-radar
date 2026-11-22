"""
LinkedIn public (logged-out) job search. Every job is opened individually and
dropped if LinkedIn says it's closed, so stale links don't reach the app.
"""
import html
import random
import re
import time

from .. import config
from ..util import html_to_text, session, to_iso, find_salary

SEARCH = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{id}"

_CARD = re.compile(r'data-entity-urn="urn:li:jobPosting:(\d+)"(.*?)(?=data-entity-urn="urn:li:jobPosting:|\Z)', re.S)
_TITLE = re.compile(r'base-search-card__title[^>]*>\s*(.*?)\s*</h3>', re.S)
_COMP = re.compile(r'base-search-card__subtitle[^>]*>.*?(?:<a[^>]*>)?\s*(.*?)\s*(?:</a>|</h4>)', re.S)
_LOC = re.compile(r'job-search-card__location[^>]*>\s*(.*?)\s*</span>', re.S)
_DATE = re.compile(r'<time[^>]*datetime="([\d-]+)"')
_DESC = re.compile(r'show-more-less-html__markup[^>]*>(.*?)</div>', re.S)
_CLOSED = re.compile(r"No longer accepting applications|closed-job|This job is no longer available", re.I)


def _clean(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


class LinkedIn:
    name = "linkedin"

    def __init__(self):
        self.requests = 0
        self.blocked = False

    def _get(self, url, **kw):
        if self.blocked:
            return None
        time.sleep(random.uniform(1.2, 2.4))
        self.requests += 1
        try:
            r = session().get(url, timeout=30, **kw)
        except Exception:
            return None
        if r.status_code in (429, 999):
            self.blocked = True  # back off for the rest of this run
            return None
        return r

    def search(self, keywords, location, partition):
        out = []
        for page in range(config.LINKEDIN_PAGES):
            params = {"keywords": keywords, "location": location, "f_TPR": "r604800",
                      "f_E": "2,3,4", "start": page * 10}
            r = self._get(SEARCH, params=params)
            if r is None or r.status_code != 200 or not r.text.strip():
                break
            cards = _CARD.findall(r.text)
            for jid, body in cards:
                t, c, l, d = _TITLE.search(body), _COMP.search(body), _LOC.search(body), _DATE.search(body)
                out.append({
                    "ext_id": jid, "title": _clean(t.group(1)) if t else "",
                    "company": _clean(c.group(1)) if c else "",
                    "locations": [_clean(l.group(1)) if l else location], "remote": False,
                    "url": f"https://www.linkedin.com/jobs/view/{jid}/",
                    "posted_at": to_iso(d.group(1)) if d else None,
                    "desc": None, "salary": None, "_hint": partition,
                })
            if len(cards) < 10:
                break
        return out

    def detail(self, raw):
        """Fill description; mark closed/missing. Returns False if the job is gone."""
        r = self._get(DETAIL.format(id=raw["ext_id"]))
        if r is None:
            return None  # unknown (blocked / network)
        if r.status_code in (404, 410):
            return False
        if r.status_code != 200:
            return None
        if _CLOSED.search(r.text):
            return False
        m = _DESC.search(r.text)
        raw["desc"] = html_to_text(m.group(1)) if m else ""
        raw["salary"] = find_salary(raw["desc"])
        return True

    def all_searches(self):
        jobs, seen = [], set()
        plan = [(k, l, "india") for l in config.LINKEDIN_INDIA_LOCATIONS for k in config.LINKEDIN_INDIA_KEYWORDS]
        plan += [(k, l, "abroad") for l in config.LINKEDIN_ABROAD_LOCATIONS for k in config.LINKEDIN_ABROAD_KEYWORDS]
        for k, l, p in plan:
            if self.blocked:
                break
            for j in self.search(k, l, p):
                if j["ext_id"] not in seen:
                    seen.add(j["ext_id"])
                    jobs.append(j)
        return jobs
