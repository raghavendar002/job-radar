"""
Run one scan:  python -m scanner [--no-linkedin] [--only greenhouse,lever,...]

Writes docs/data/jobs.json and docs/data/status.json, which the phone app reads.
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import config, geo, visa
from .scoring import score, title_ok
from .sources.ats import FEEDS
from .sources.linkedin import LinkedIn
from .util import age_days, norm, now_iso

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"

_KNOWN = {norm(c["name"]): c for _, cs in FEEDS.values() for c in cs}


def blocked(company: str) -> bool:
    c = (company or "").lower()
    return any(b in c for b in config.COMPANY_BLOCKLIST)


def build(raw, src, c, registers):
    """raw (with desc) -> final job dict, or None if it doesn't qualify."""
    if raw.get("closed"):
        return None
    part, place = geo.classify_many(raw["locations"], remote_flag=raw.get("remote", False))
    if part is None:
        return None
    desc = raw.get("desc") or ""
    job = {
        "id": f"{src}:{c['token'] if c else 'li'}:{raw['ext_id']}",
        "src": src,
        "company": raw["company"],
        "title": raw["title"].strip(),
        "location": " · ".join(dict.fromkeys(l.strip() for l in raw["locations"] if l.strip()))[:120],
        "place": place,
        "partition": part,
        "url": raw["url"],
        "posted_at": raw.get("posted_at"),
        "salary": raw.get("salary"),
        "tier": c.get("tier") if c else None,
    }
    if part == "abroad":
        sp = visa.sponsorship(desc)
        if sp == "no":
            return None
        if sp == "yes":
            job["sponsorship"] = "confirmed"
            job["visa_note"] = visa.evidence(desc)
        elif (c and c.get("sponsor")) or registers.known(raw["company"], place):
            job["sponsorship"] = "likely"
        else:
            job["sponsorship"] = "unknown"
        job["language"] = visa.language_required(desc)
    s = score(job, desc, tier=job["tier"], partition=part)
    job.update(s)
    if job["score"] < config.MIN_SCORE:
        return None
    return job


def scan_company(feed, c, registers):
    raws = feed.list_jobs(c)
    out, details = [], 0
    for raw in raws:
        if not title_ok(raw["title"]) or blocked(raw["company"]):
            continue
        if raw.get("desc") is None:
            part, _ = geo.classify_many(raw["locations"], remote_flag=raw.get("remote", False))
            vague = any("location" in (l or "").lower() for l in raw["locations"])
            if part is None and not vague:
                continue
            if details >= config.DETAIL_FETCH_CAP_PER_COMPANY:
                continue
            details += 1
            try:
                feed.detail(c, raw)
            except Exception:
                continue
        job = build(raw, feed.name, c, registers)
        if job:
            out.append(job)
    return len(raws), out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-linkedin", action="store_true")
    ap.add_argument("--only", default="", help="comma list of feeds: greenhouse,lever,ashby,smartrecruiters,workday")
    args = ap.parse_args(argv)

    t0 = time.time()
    DATA.mkdir(parents=True, exist_ok=True)
    prev = {}
    try:
        old = json.loads((DATA / "jobs.json").read_text(encoding="utf-8"))
        for j in old.get("india", []) + old.get("abroad", []):
            prev[j["id"]] = j
    except Exception:
        pass

    registers = visa.Registers()
    status = {"sources": {}, "linkedin": {}}
    jobs: dict[str, dict] = {}
    failed_keys = set()

    only = {x for x in args.only.split(",") if x}
    tasks = [(feed, c) for key, (feed, cs) in FEEDS.items() if not only or key in only for c in cs]

    with ThreadPoolExecutor(10) as ex:
        reg_future = ex.submit(registers.load)
        futs = {ex.submit(scan_company, feed, c, registers): (feed, c) for feed, c in tasks}
        for f in as_completed(futs):
            feed, c = futs[f]
            key = f"{feed.name}:{c['token']}"
            try:
                listed, found = f.result()
                status["sources"][key] = {"company": c["name"], "ok": True, "listed": listed, "matched": len(found)}
                for j in found:
                    jobs[j["id"]] = j
            except Exception as e:
                failed_keys.add(key)
                status["sources"][key] = {"company": c["name"], "ok": False, "error": f"{e.__class__.__name__}: {str(e)[:120]}"}
                print(f"[warn] {key} failed: {e}", file=sys.stderr)
        reg_future.result()
    status["registers"] = registers.status

    # A company board that errored this run keeps yesterday's jobs (outage != closed), for up to 2 days.
    carried = set()
    for j in prev.values():
        key = ":".join(j["id"].split(":")[:2])
        if key in failed_keys and (age_days(j.get("last_seen")) or 99) < 2:
            jobs[j["id"]] = j
            carried.add(j["id"])

    if config.LINKEDIN_ENABLED and not args.no_linkedin:
        status["linkedin"] = run_linkedin(jobs, prev, registers)
    elif not only:
        # LinkedIn skipped this run: keep recently verified LinkedIn jobs as they were.
        for pid, pj in prev.items():
            if pid.startswith("linkedin:") and (age_days(pj.get("last_verified")) or 99) < 1.5:
                jobs[pid] = pj
                carried.add(pid)

    # ---- merge timestamps, rank, write ----
    now = now_iso()
    out = {"india": [], "abroad": []}
    for jid, j in jobs.items():
        j["first_seen"] = (prev.get(jid) or {}).get("first_seen") or now
        if jid not in carried:
            j["last_seen"] = now
        out[j["partition"]].append(j)
    for k in out:
        out[k].sort(key=lambda j: (j["score"], j.get("posted_at") or ""), reverse=True)
        if k == "abroad":
            per = {}
            kept = []
            for j in out[k]:
                per[j["place"]] = per.get(j["place"], 0) + 1
                if per[j["place"]] <= config.MAX_PER_COUNTRY:
                    kept.append(j)
            out[k] = kept
        out[k] = out[k][: config.MAX_PER_PARTITION]

    payload = {"generated_at": now, "india": out["india"], "abroad": out["abroad"]}
    (DATA / "jobs.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    ok = sum(1 for s in status["sources"].values() if s["ok"])
    status.update({
        "generated_at": now, "duration_s": round(time.time() - t0),
        "counts": {k: len(v) for k, v in out.items()},
        "new": {k: sum(1 for j in v if j["first_seen"] == now) for k, v in out.items()},
        "boards_ok": ok, "boards_total": len(status["sources"]),
    })
    (DATA / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"done in {status['duration_s']}s  india={len(out['india'])} abroad={len(out['abroad'])}  "
          f"boards {ok}/{len(status['sources'])}  linkedin={status.get('linkedin')}")


def run_linkedin(jobs, prev, registers):
    li = LinkedIn()
    ats_keys = {(norm(j["company"]), norm(j["title"])) for j in jobs.values()}
    stats = {"found": 0, "checked": 0, "closed": 0, "kept": 0, "rechecked_old": 0}
    budget = config.LINKEDIN_MAX_DETAIL_FETCHES
    seen_ids = set()

    cands = li.all_searches()
    stats["found"] = len(cands)
    for raw in cands:
        seen_ids.add(raw["ext_id"])
        if budget <= 0 or li.blocked:
            break
        if not title_ok(raw["title"]) or blocked(raw["company"]):
            continue
        if (norm(raw["company"]), norm(raw["title"])) in ats_keys:
            continue
        if (age_days(raw.get("posted_at")) or 0) > config.LINKEDIN_MAX_AGE_DAYS:
            continue
        part, _ = geo.classify_many(raw["locations"])
        if part is None:
            continue
        pid = f"linkedin:li:{raw['ext_id']}"
        if pid in prev and (age_days(prev[pid].get("last_verified")) or 99) < 0.4:
            jobs[pid] = prev[pid]  # verified within ~10h, skip refetch
            stats["kept"] += 1
            continue
        budget -= 1
        stats["checked"] += 1
        ok = li.detail(raw)
        if ok is False:
            stats["closed"] += 1
            continue
        if ok is None:
            continue
        c = _KNOWN.get(norm(raw["company"]))
        job = build(raw, "linkedin", c, registers)
        if job:
            job["id"] = pid
            job["last_verified"] = now_iso()
            jobs[pid] = job
            stats["kept"] += 1

    # Re-verify LinkedIn jobs from earlier runs that didn't show up in today's searches.
    for pid, pj in prev.items():
        if not pid.startswith("linkedin:") or pid in jobs:
            continue
        if (age_days(pj.get("posted_at")) or 0) > config.LINKEDIN_MAX_AGE_DAYS:
            continue
        if budget > 0 and not li.blocked:
            budget -= 1
            stats["rechecked_old"] += 1
            raw = {"ext_id": pid.split(":")[-1]}
            ok = li.detail(raw)
            if ok is True:
                pj["last_verified"] = now_iso()
                jobs[pid] = pj
            elif ok is False:
                stats["closed"] += 1
        elif (age_days(pj.get("last_verified")) or 99) < 1.5:
            jobs[pid] = pj  # couldn't check this run; still fresh enough
    stats["requests"] = li.requests
    stats["blocked"] = li.blocked
    return stats


if __name__ == "__main__":
    main()
