"""
Company applicant-tracking-system feeds. Each returns only currently-open postings.

list_jobs(company) -> list of raw dicts:
  ext_id, title, company, locations[list], remote(bool), url, posted_at(iso|None),
  desc(str|None), salary(str|None)
detail(company, raw) -> fills desc / locations / url for feeds whose list view is thin.
"""
import threading
import time

import requests

from ..util import UA, deadline_passed, html_to_text, session, to_iso, find_salary
from .. import config


# ------------------------------- Greenhouse -------------------------------
class Greenhouse:
    name = "greenhouse"

    def list_jobs(self, c):
        r = session().get(f"https://boards-api.greenhouse.io/v1/boards/{c['token']}/jobs",
                          params={"content": "true"}, timeout=60)
        r.raise_for_status()
        out = []
        for j in r.json().get("jobs", []):
            locs = [(j.get("location") or {}).get("name") or ""]
            for o in j.get("offices") or []:
                if o.get("location"):
                    locs.append(o["location"])
                elif o.get("name"):
                    locs.append(o["name"])
            desc = html_to_text(j.get("content"))
            out.append({
                "ext_id": str(j["id"]), "title": j.get("title", ""), "company": c["name"],
                "locations": [l for l in locs if l], "remote": False,
                "url": j.get("absolute_url"),
                "posted_at": to_iso(j.get("first_published") or j.get("updated_at")),
                "desc": desc, "salary": find_salary(desc),
            })
        return out

    def detail(self, c, raw):
        return raw


# --------------------------------- Lever ----------------------------------
class Lever:
    name = "lever"

    def list_jobs(self, c):
        r = session().get(f"https://api.lever.co/v0/postings/{c['token']}", params={"mode": "json"}, timeout=60)
        r.raise_for_status()
        out = []
        for j in r.json():
            cat = j.get("categories") or {}
            locs = [cat.get("location") or ""] + list(cat.get("allLocations") or [])
            parts = [j.get("descriptionPlain") or "", j.get("additionalPlain") or ""]
            for lst in j.get("lists") or []:
                parts.append(lst.get("text", ""))
                parts.append(html_to_text(lst.get("content")))
            desc = "\n".join(p for p in parts if p)
            sal = None
            sr = j.get("salaryRange") or {}
            if sr.get("min") and sr.get("max"):
                sal = f"{sr.get('currency', '')} {sr['min']:,}–{sr['max']:,}".strip()
            out.append({
                "ext_id": j["id"], "title": j.get("text", ""), "company": c["name"],
                "locations": [l for l in locs if l],
                "remote": (j.get("workplaceType") == "remote"),
                "url": j.get("hostedUrl"), "posted_at": to_iso(j.get("createdAt")),
                "desc": desc, "salary": sal or find_salary(desc),
            })
        return out

    def detail(self, c, raw):
        return raw


# --------------------------------- Ashby ----------------------------------
class Ashby:
    name = "ashby"

    def list_jobs(self, c):
        r = session().get(f"https://api.ashbyhq.com/posting-api/job-board/{c['token']}",
                          params={"includeCompensation": "true"}, timeout=60)
        r.raise_for_status()
        out = []
        for j in r.json().get("jobs", []):
            if j.get("isListed") is False:
                continue
            locs = [j.get("location") or ""]
            for sl in j.get("secondaryLocations") or []:
                locs.append(sl.get("location") or "")
            addr = ((j.get("address") or {}).get("postalAddress") or {})
            if addr.get("addressCountry"):
                locs.append(", ".join(x for x in (addr.get("addressLocality"), addr.get("addressCountry")) if x))
            desc = j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml"))
            comp = (j.get("compensation") or {}).get("compensationTierSummary") or None
            out.append({
                "ext_id": j.get("id"), "title": j.get("title", ""), "company": c["name"],
                "locations": [l for l in locs if l], "remote": bool(j.get("isRemote")),
                "url": j.get("jobUrl"), "posted_at": to_iso(j.get("publishedAt")),
                "desc": desc, "salary": comp or find_salary(desc),
            })
        return out

    def detail(self, c, raw):
        return raw


# ----------------------------- SmartRecruiters ----------------------------
class SmartRecruiters:
    name = "smartrecruiters"

    def list_jobs(self, c):
        out, seen = [], set()
        s = session()
        for q in ("java", "backend", "software engineer", "scala"):
            offset = 0
            while offset < 400:
                r = s.get(f"https://api.smartrecruiters.com/v1/companies/{c['token']}/postings",
                          params={"q": q, "limit": 100, "offset": offset}, timeout=60)
                r.raise_for_status()
                d = r.json()
                for j in d.get("content", []):
                    if j["id"] in seen:
                        continue
                    seen.add(j["id"])
                    loc = j.get("location") or {}
                    full = loc.get("fullLocation") or ", ".join(
                        x for x in (loc.get("city"), loc.get("region"), loc.get("country")) if x)
                    out.append({
                        "ext_id": j["id"], "title": j.get("name", ""), "company": c["name"],
                        "locations": [full], "remote": bool(loc.get("remote")),
                        "url": f"https://jobs.smartrecruiters.com/{c['token']}/{j['id']}",
                        "posted_at": to_iso(j.get("releasedDate")), "desc": None, "salary": None,
                        "_ref": j.get("ref"),
                    })
                offset += 100
                if offset >= d.get("totalFound", 0):
                    break
        return out

    def detail(self, c, raw):
        r = session().get(raw.pop("_ref", None) or
                          f"https://api.smartrecruiters.com/v1/companies/{c['token']}/postings/{raw['ext_id']}",
                          timeout=40)
        r.raise_for_status()
        d = r.json()
        secs = ((d.get("jobAd") or {}).get("sections") or {})
        desc = "\n".join(html_to_text((secs.get(k) or {}).get("text"))
                         for k in ("companyDescription", "jobDescription", "qualifications", "additionalInformation"))
        raw["desc"] = desc
        raw["salary"] = find_salary(desc)
        if d.get("postingUrl"):
            raw["url"] = d["postingUrl"]
        if d.get("active") is False:
            raw["closed"] = True
        return raw


# -------------------------------- Workday ---------------------------------
class Workday:
    name = "workday"

    def _base(self, c):
        return f"https://{c['token']}.{c['wd']}.myworkdayjobs.com"

    def list_jobs(self, c):
        s = session()
        base = self._base(c)
        api = f"{base}/wday/cxs/{c['token']}/{c['site']}/jobs"
        out, seen = [], set()
        for q in config.WORKDAY_QUERIES:
            for page in range(config.WORKDAY_MAX_PAGES):
                r = _wd_call("POST", api, json={"appliedFacets": {}, "limit": 20, "offset": page * 20, "searchText": q},
                             headers={"Accept": "application/json", "Content-Type": "application/json"})
                posts = r.json().get("jobPostings", [])
                for j in posts:
                    path = j.get("externalPath")
                    if not path or path in seen:
                        continue
                    seen.add(path)
                    out.append({
                        "ext_id": path.rsplit("_", 1)[-1], "title": j.get("title", ""), "company": c["name"],
                        "locations": [j.get("locationsText") or ""], "remote": False,
                        "url": f"{base}/en-US/{c['site']}{path}",
                        "posted_at": _wd_posted(j.get("postedOn")), "desc": None, "salary": None,
                        "_path": path,
                    })
                if len(posts) < 20:
                    break
        return out

    def detail(self, c, raw):
        path = raw.pop("_path")
        r = _wd_call("GET", f"{self._base(c)}/wday/cxs/{c['token']}/{c['site']}{path}",
                     headers={"Accept": "application/json"})
        info = r.json().get("jobPostingInfo") or {}
        locs = [info.get("location") or ""] + list(info.get("additionalLocations") or [])
        if (info.get("country") or {}).get("descriptor"):
            locs.append(info["country"]["descriptor"])
        raw["locations"] = [l for l in locs if l] or raw["locations"]
        raw["desc"] = html_to_text(info.get("jobDescription"))
        raw["salary"] = find_salary(raw["desc"])
        raw["posted_at"] = to_iso(info.get("startDate")) or raw["posted_at"]
        if info.get("externalUrl"):
            raw["url"] = info["externalUrl"]
        if info.get("canApply") is False:
            raw["closed"] = True
        return raw


_wd_lock = threading.Lock()
_wd_last = [0.0]
_wd_session = requests.Session()
_wd_session.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})


class WorkdayBlocked(Exception):
    pass


_wd_429_streak = [0]


def _wd_call(method, url, **kw):
    """Workday rate-limits per IP across all its tenants, and often blocks cloud (GitHub) IPs
    outright. One request at a time, paced; after a few 429s in a row Workday is switched off
    for the rest of the scan so it can never hold up publishing."""
    with _wd_lock:
        if _wd_429_streak[0] >= config.WORKDAY_BREAKER_429S:
            raise WorkdayBlocked("Workday is rate-limiting this machine; skipped for this scan")
        if deadline_passed(config.WORKDAY_BUDGET_MIN):
            raise WorkdayBlocked("Workday time budget used up for this scan")
        wait = config.WORKDAY_MIN_INTERVAL_S - (time.monotonic() - _wd_last[0])
        if wait > 0:
            time.sleep(wait)
        try:
            r = _wd_session.request(method, url, timeout=30, **kw)
        finally:
            _wd_last[0] = time.monotonic()
        if r.status_code == 429:
            _wd_429_streak[0] += 1
            time.sleep(5)
        else:
            _wd_429_streak[0] = 0
    r.raise_for_status()
    return r


def _wd_posted(s):
    """'Posted Today' / 'Posted Yesterday' / 'Posted 3 Days Ago' / 'Posted 30+ Days Ago'"""
    import re
    from datetime import datetime, timedelta, timezone
    if not s:
        return None
    s = s.lower()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    if "today" in s:
        d = 0
    elif "yesterday" in s:
        d = 1
    else:
        m = re.search(r"(\d+)", s)
        if not m:
            return None
        d = int(m.group(1))
    return (now - timedelta(days=d)).isoformat()


FEEDS = {
    "greenhouse": (Greenhouse(), config.GREENHOUSE),
    "lever": (Lever(), config.LEVER),
    "ashby": (Ashby(), config.ASHBY),
    "smartrecruiters": (SmartRecruiters(), config.SMARTRECRUITERS),
    "workday": (Workday(), config.WORKDAY),
}
