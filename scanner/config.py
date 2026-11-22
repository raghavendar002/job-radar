"""
Everything you'd want to tweak lives here: your profile, where you want to work,
and which company career boards get scanned.

Company boards are read straight from each company's applicant-tracking system
(Greenhouse / Lever / Ashby / SmartRecruiters / Workday). Those APIs only return
jobs that are OPEN right now, which is why links from them don't go dead.
"""

# --------------------------------------------------------------------------
# Profile: what a good match looks like
# --------------------------------------------------------------------------
YEARS_EXPERIENCE = 3.5

# Skill keyword -> points (regex, matched case-insensitively against title+description)
SKILLS = {
    r"\bjava\b": 10,
    r"\bscala\b": 8,
    r"\bkotlin\b": 4,
    r"\bspring( boot)?\b": 8,
    r"\bkafka\b": 6,
    r"\bredis\b": 3,
    r"\bmysql\b|\bpostgres(ql)?\b|\bsql\b": 3,
    r"\bmicro-?services?\b": 4,
    r"\bdistributed (systems?|services?)\b": 4,
    r"\bgrpc\b": 2,
    r"\bhibernate\b|\bjpa\b": 2,
    r"\bjvm\b": 3,
    r"\bmongo(db)?\b": 1,
    r"\bidempoten": 3,
    r"\bevent[- ]driven\b": 2,
}
SKILL_CAP = 35

# Domain keywords (your finance-engineering edge)
DOMAIN = {
    r"\bpayments?\b": 5,
    r"\bfintech\b": 4,
    r"\bledger\b": 6,
    r"\bsettlements?\b": 5,
    r"\breconciliation\b": 6,
    r"\bpayouts?\b": 4,
    r"\bbilling\b": 3,
    r"\baccounting\b": 4,
    r"\bbanking\b|\bbank\b": 2,
    r"\bmerchant\b": 2,
    r"\btreasury\b": 3,
}
DOMAIN_CAP = 15

# Titles must look like a backend/software role...
TITLE_REQUIRE = r"\b(engineer|developer|sde|swe|programmer|technical staff|mts)\b"
# ...and must not be one of these
TITLE_EXCLUDE = (
    r"front[- ]?end|\bios\b|android|mobile|\bui\b|\bux\b|designer|\bqa\b|quality|\btest|sdet|"
    r"scientist|machine learning|\bml\b|research|manager|director|head of|\bvp\b|vice president|"
    r"principal|\bstaff\b|distinguished|architect|\bintern|trainee|graduate|new grad|apprentice|"
    r"\bsales|\bsupport engineer|solutions? engineer|customer success|field engineer|embedded|firmware|hardware|\bgpu\b|asic|"
    r"fpga|silicon|verification|network engineer|security engineer|site reliability|\bsre\b|"
    r"devops|data engineer|analytics|analyst|consultant|recruit|technical writer|salesforce developer|"
    r"\bsap\b|mainframe|cobol|forward deployed|\bfde\b|instructor|clearance|services engineer|"
    r"ansible|linux engineer"
)
# Titles that are still OK but a weaker fit
TITLE_WEAK = r"\.net|\bc#|\bphp\b|\bruby\b|\bnode|react|python developer|\bgolang\b|\bgo\b|full[- ]?stack|\blead\b|\bc\+\+"
TITLE_STRONG = r"back[- ]?end|\bjava\b|\bscala\b|\bkotlin\b|platform|server|payments?|ledger|fintech|distributed"

MIN_SCORE = 40           # jobs below this are not shown at all
MAX_PER_PARTITION = 250  # keep the list phone-sized

# --------------------------------------------------------------------------
# Where
# --------------------------------------------------------------------------
INCLUDE_REMOTE_INDIA = False   # True = also show "Remote, India" roles in the India tab

# Abroad: countries considered, with a small preference bonus (easier visa / better fit)
TARGET_COUNTRIES = {
    "Germany": 6, "Netherlands": 6, "Ireland": 5, "United Kingdom": 5, "Singapore": 5,
    "United Arab Emirates": 4, "Luxembourg": 4, "Switzerland": 4, "Sweden": 4, "Denmark": 3,
    "Japan": 3, "Australia": 3, "Poland": 1, "Spain": 2, "Portugal": 2,
    "France": 2, "Austria": 3, "Finland": 2, "Norway": 2, "Belgium": 2, "Estonia": 2,
    "Lithuania": 1, "Thailand": 1, "Malaysia": 1, "Hong Kong": 2, "Saudi Arabia": 2,
    "Qatar": 2, "New Zealand": 2,
    "Canada": -4,           # hiring from abroad needs LMIA / Global Talent Stream: rarer
    "United States": -15,   # needs the H-1B lottery: shown, but ranked lower
}
MAX_PER_COUNTRY = 45  # stops one country (usually the US) from flooding the Abroad tab

# Companies you never want to see (case-insensitive substring of company name)
COMPANY_BLOCKLIST = [
    "crossover", "turing", "mercor", "alignerr", "dataannotation", "outlier", "jobs via",
    "recruit", "staffing", "talent", "hiring", "consult", "manpower", "jobgether", "jobot",
    "dice", "remotehunter", "hirist", "instahyre",
]
# Big IT-services firms: shown, but pushed down
COMPANY_DEPRIORITIZE = [
    "tata consultancy", "tcs", "infosys", "wipro", "cognizant", "hcl", "tech mahindra",
    "capgemini", "accenture", "ltimindtree", "mphasis", "hexaware", "virtusa", "coforge",
    "persistent", "birlasoft", "zensar", "mindtree", "ust global", "ibm", "dxc", "ntt data",
    "cgi", "synechron", "quest global", "sopra steria", "atos", "globallogic", "epam", "luxoft",
]

# --------------------------------------------------------------------------
# LinkedIn public job search (no login; links are re-checked every run)
# --------------------------------------------------------------------------
LINKEDIN_ENABLED = True
LINKEDIN_INDIA_KEYWORDS = ["java backend developer", "backend engineer java", "scala developer", "software engineer payments"]
LINKEDIN_INDIA_LOCATIONS = [
    "Bengaluru, Karnataka, India", "Chennai, Tamil Nadu, India", "Hyderabad, Telangana, India",
    "Kochi, Kerala, India", "Coimbatore, Tamil Nadu, India", "Thiruvananthapuram, Kerala, India",
]
LINKEDIN_ABROAD_KEYWORDS = ["java backend engineer", "scala engineer", "backend engineer visa sponsorship"]
LINKEDIN_ABROAD_LOCATIONS = [
    "Germany", "Netherlands", "Ireland", "United Kingdom", "Singapore", "United Arab Emirates",
    "Sweden", "Japan", "Canada", "Australia", "Luxembourg", "Switzerland",
]
LINKEDIN_PAGES = 2               # 10 results per page
LINKEDIN_MAX_DETAIL_FETCHES = 220  # cap on per-job page checks per run (be polite)
LINKEDIN_MAX_AGE_DAYS = 30

# --------------------------------------------------------------------------
# Company career boards
#   tier 1 = top-paying / strong brand, 2 = good, 3 = ok
#   sponsor = company is known to sponsor visas / relocate engineers
# --------------------------------------------------------------------------
def _c(token, name, tier=2, sponsor=True):
    return {"token": token, "name": name, "tier": tier, "sponsor": sponsor}

GREENHOUSE = [
    _c("stripe", "Stripe", 1), _c("airbnb", "Airbnb", 1), _c("coinbase", "Coinbase", 1),
    _c("databricks", "Databricks", 1), _c("robinhood", "Robinhood", 1), _c("brex", "Brex", 1),
    _c("twilio", "Twilio", 2), _c("datadog", "Datadog", 1), _c("cloudflare", "Cloudflare", 1),
    _c("mongodb", "MongoDB", 1), _c("okta", "Okta", 2), _c("dropbox", "Dropbox", 1),
    _c("figma", "Figma", 1), _c("discord", "Discord", 1), _c("reddit", "Reddit", 1),
    _c("pinterest", "Pinterest", 1), _c("lyft", "Lyft", 1), _c("instacart", "Instacart", 1),
    _c("doordashusa", "DoorDash", 1), _c("affirm", "Affirm", 1), _c("chime", "Chime", 1),
    _c("sofi", "SoFi", 2), _c("adyen", "Adyen", 1), _c("n26", "N26", 2), _c("wise", "Wise", 1),
    _c("monzo", "Monzo", 1), _c("gocardless", "GoCardless", 2), _c("sumup", "SumUp", 2),
    _c("rubrik", "Rubrik", 1), _c("toast", "Toast", 2), _c("intercom", "Intercom", 1),
    _c("anthropic", "Anthropic", 1), _c("razorpaysoftwareprivatelimited", "Razorpay", 1),
    _c("groww", "Groww", 1), _c("inmobi", "InMobi", 2), _c("hellofresh", "HelloFresh", 2),
    _c("solarisbank", "Solaris", 2), _c("raisin", "Raisin", 2), _c("celonis", "Celonis", 1),
    _c("contentful", "Contentful", 2), _c("bitpanda", "Bitpanda", 2), _c("tide", "Tide", 2),
    _c("coupang", "Coupang", 1), _c("agoda", "Agoda", 2), _c("trivago", "trivago", 2),
    _c("flix", "Flix", 2), _c("cockroachlabs", "Cockroach Labs", 1), _c("samsara", "Samsara", 1),
    _c("asana", "Asana", 1), _c("squarespace", "Squarespace", 2), _c("roblox", "Roblox", 1),
    _c("duolingo", "Duolingo", 1),
]

LEVER = [
    _c("palantir", "Palantir", 1), _c("spotify", "Spotify", 1), _c("cred", "CRED", 1),
    _c("meesho", "Meesho", 1), _c("zeta", "Zeta", 2), _c("paytm", "Paytm", 2),
    _c("mindtickle", "Mindtickle", 2), _c("wealthfront", "Wealthfront", 1), _c("nium", "Nium", 2),
    _c("fampay", "FamPay", 2), _c("outreach", "Outreach", 2),
]

ASHBY = [
    _c("ramp", "Ramp", 1), _c("notion", "Notion", 1), _c("linear", "Linear", 1),
    _c("openai", "OpenAI", 1), _c("plaid", "Plaid", 1), _c("wealthsimple", "Wealthsimple", 2),
    _c("modal", "Modal", 1), _c("clickhouse", "ClickHouse", 1), _c("sentry", "Sentry", 2),
    _c("docker", "Docker", 2), _c("replit", "Replit", 1), _c("cursor", "Cursor", 1),
    _c("perplexity", "Perplexity", 1), _c("synthesia", "Synthesia", 2), _c("n8n", "n8n", 2),
    _c("pennylane", "Pennylane", 2), _c("alan", "Alan", 2), _c("doctolib", "Doctolib", 2),
    _c("ledger", "Ledger", 2),
]

SMARTRECRUITERS = [
    _c("DeliveryHero", "Delivery Hero", 2), _c("Freshworks", "Freshworks", 2),
    _c("Swiggy", "Swiggy", 1), _c("ServiceNow", "ServiceNow", 1), _c("Grab", "Grab", 1),
]

# Workday: host = <tenant>.<wdN>.myworkdayjobs.com, site = career-site path
def _w(tenant, wd, site, name, tier=2, sponsor=True):
    return {"token": tenant, "wd": wd, "site": site, "name": name, "tier": tier, "sponsor": sponsor}

WORKDAY = [
    _w("nvidia", "wd5", "NVIDIAExternalCareerSite", "NVIDIA", 1),
    _w("paypal", "wd1", "jobs", "PayPal", 1),
    _w("mastercard", "wd1", "CorporateCareers", "Mastercard", 1),
    _w("adobe", "wd5", "external_experienced", "Adobe", 1),
    _w("salesforce", "wd12", "External_Career_Site", "Salesforce", 1),
    _w("capitalone", "wd12", "Capital_One", "Capital One", 1),
    _w("ms", "wd5", "External", "Morgan Stanley", 1),
    _w("workday", "wd5", "Workday", "Workday", 1),
    _w("intel", "wd1", "External", "Intel", 2),
    _w("target", "wd5", "targetcareers", "Target", 2),
    _w("wf", "wd1", "WellsFargoJobs", "Wells Fargo", 2),
    _w("citi", "wd5", "2", "Citi", 2),
    _w("thomsonreuters", "wd5", "External_Career_Site", "Thomson Reuters", 2),
    _w("motorolasolutions", "wd5", "Careers", "Motorola Solutions", 2),
    _w("db", "wd3", "DBWebsite", "Deutsche Bank", 2),
    _w("lseg", "wd3", "Careers", "LSEG", 2),
    _w("nasdaq", "wd1", "Global_External_Site", "Nasdaq", 2),
    _w("blackrock", "wd1", "BlackRock_Professional", "BlackRock", 1),
    _w("ing", "wd3", "ICSGBLCOR", "ING", 2),
    _w("statestreet", "wd1", "Global", "State Street", 3),
    _w("fiserv", "wd5", "EXT", "Fiserv", 3),
    _w("equifax", "wd5", "External", "Equifax", 3),
    _w("broadridge", "wd5", "Careers", "Broadridge", 3),
    _w("philips", "wd3", "jobs-and-careers", "Philips", 3),
]
WORKDAY_QUERIES = ["java", "backend", "scala", "kotlin", "payments engineer"]
WORKDAY_MAX_PAGES = 5            # 20 per page, per query
DETAIL_FETCH_CAP_PER_COMPANY = 60
