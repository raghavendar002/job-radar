# Job Radar

Finds open backend roles that fit my profile (Java/Scala, Spring, Kafka, fintech/ledger) twice a day, in two lists:

- **South India**: Bengaluru, Chennai, Hyderabad, Kochi, Coimbatore, Thiruvananthapuram and the rest of the south
- **Abroad + visa**: roles where the company states visa/relocation support, or usually sponsors (from a curated company list and the official UK and Netherlands sponsor registers). Roles that say "no sponsorship" or "must already have the right to work" are dropped, and roles that need German, Dutch and similar languages are pushed down.

The list is a phone web app (GitHub Pages) that you add to your iPhone home screen.

## Why the links stay live

The old setup asked an AI to search the web, and search results are often days or weeks old. This one never uses search results:

| Source | How it knows a job is open |
|---|---|
| ~110 company boards (Greenhouse, Lever, Ashby, SmartRecruiters, Workday) | Reads the company's own job system API, which only lists open roles. Every scan rebuilds the list, so a role the company closes is gone by the next scan. |
| LinkedIn (public search, no login) | Opens every job page and drops it if LinkedIn says "No longer accepting applications" or the page is gone. Jobs kept from earlier scans are opened again before they're shown. |

If a company board is down during a scan, its jobs from the last scan are kept for up to 2 days rather than wiped. The status pill in the app shows when the last scan ran and which boards failed.

## Setup (one time, about 15 minutes)

### 1. Push to GitHub
Create an **empty public** repo called `job-radar` on github.com (no README), then from this folder:

```bash
git init -b main
git add .
git commit -m "Job Radar"
git remote add origin https://github.com/<you>/job-radar.git
git push -u origin main
```

(GitHub Pages on a *private* repo needs a paid plan. The repo holds no personal data: no resume, phone number or email.)

### 2. Turn on Pages
Repo → **Settings → Pages** → Source: *Deploy from a branch* → Branch `main`, folder `/docs` → Save.
After a minute the app is at `https://<you>.github.io/job-radar/`.

### 3. Run the first scan
Repo → **Actions** → *scan* → **Run workflow**. It takes about 10–15 minutes and commits `docs/data/jobs.json`.

### 4. Create a token for cron-job.org
github.com → Settings → Developer settings → **Fine-grained tokens** → Generate:
- Repository access: *Only select repositories* → `job-radar`
- Permissions → Repository → **Actions: Read and write** (nothing else)
- Expiry: the longest allowed, with a reminder to renew

### 5. Schedule it on cron-job.org
Create a cron job:
- **URL**: `https://api.github.com/repos/<you>/job-radar/actions/workflows/scan.yml/dispatches`
- **Schedule**: Custom → `0 8,19 * * *`, timezone **Asia/Kolkata** (8 AM and 7 PM)
- **Advanced → Request method**: `POST`
- **Headers**:
  - `Authorization: Bearer <your token>`
  - `Accept: application/vnd.github+json`
  - `X-GitHub-Api-Version: 2022-11-28`
  - `User-Agent: cron-job.org`
- **Request body**: `{"ref":"main"}`
- Save, then click **Test run**. A `204` response means the scan started (check the Actions tab).

Turn on cron-job.org's failure email too. GitHub also emails you if a scan fails.

### 6. Add it to your iPhone
Open the Pages URL in **Safari** → Share → **Add to Home Screen**.

## Using the app
- **Score ring**: fit out of 100 (skills, finance domain, years asked, company tier, freshness; for Abroad also country and visa signal)
- **NEW**: first seen since your last visit
- **☆ / Applied / ✕**: save, mark applied, or hide. These are stored on the phone itself.
- **Abroad filters**: *Visa stated* shows only roles whose text mentions sponsorship or relocation. *Hide US* is on by default because US roles need the H-1B lottery.
- Tap a card for the sponsorship sentence, years asked, and when it was last confirmed open.

## Tuning
Everything is in [`scanner/config.py`](scanner/config.py): skill weights, excluded titles, countries and their preference, blocked companies, LinkedIn searches, and the company boards list. To add a company, find its board token in the careers-page URL:
- `boards.greenhouse.io/<token>` → `GREENHOUSE`
- `jobs.lever.co/<token>` → `LEVER`
- `jobs.ashbyhq.com/<token>` → `ASHBY`
- `jobs.smartrecruiters.com/<token>` → `SMARTRECRUITERS`
- `<tenant>.wd5.myworkdayjobs.com/<site>` → `WORKDAY`

Run locally:

```bash
pip install -r requirements.txt
python -m scanner              # full scan
python -m scanner --no-linkedin
python -m http.server 8765 --directory docs
```
