"""Visa-sponsorship and language signals for jobs outside India."""
import csv
import io
import re

from .util import norm, session

NEG = re.compile(
    r"(not|unable to|cannot|can't|can not|won't|will not|do not|don't|does not|doesn't|are not able to)\s+"
    r"(currently\s+)?(be able to\s+)?(sponsor\w*|(offer|provide|support)\w*\s+(any\s+)?(visa|work permit|immigration|sponsorship|relocation))"
    r"|no (visa |work permit )?sponsorship"
    r"|without (the need for |requiring |needing )?(visa |employer )?sponsorship"
    r"|sponsorship (is )?not (available|offered|provided|possible)"
    r"|(must|should) (already )?(have|hold|possess) (the |a |full |valid )?(legal )?(right|authori[sz]ation|permission|eligibility) to work"
    r"|(existing|valid|current|full) (right|authori[sz]ation|permit|eligibility) to work"
    r"|must be (legally )?(authori[sz]ed|eligible|entitled) to work"
    r"|eligible to work in [\w\s]{2,30} without"
    r"|(us|u\.s\.) citizen(ship)? (is )?required|security clearance|green card holders?"
    r"|(eu|european) (citizen|passport|work permit) (is )?required",
    re.I,
)
POS = re.compile(
    r"visa sponsorship (is |will be )?(available|provided|offered|possible)"
    r"|(we|will|can|happy to|able to) (also )?(provide |offer )?sponsor"
    r"|sponsorship (is |will be )?(available|provided|offered|possible)"
    r"|relocation (support|assistance|package|bonus|allowance|budget)"
    r"|(offer|provide|support) (full |generous )?relocation"
    r"|help (you )?(with )?relocat"
    r"|visa (support|assistance|and relocation|& relocation)"
    r"|work permit (support|assistance)"
    r"|immigration (support|assistance)"
    r"|blue card|highly skilled migrant|kennismigrant|skilled worker visa|employment pass"
    r"|open to (international|overseas) (candidates|applicants)",
    re.I,
)
LANG_REQ = re.compile(
    r"(fluent|fluency|native|business[- ]level|business fluent|professional proficiency|proficien\w*|"
    r"excellent|very good|strong|good|working)\s+(command of |knowledge of |skills in |level of )?"
    r"(german|dutch|french|japanese|swedish|danish|polish|spanish|italian|portuguese|arabic|norwegian|finnish)"
    r"(?!\s+(is|would be|a) (a )?(plus|bonus|advantage|nice))"
    r"|(german|dutch|french|japanese|swedish|danish|polish)\s*\(?(c1|c2|b2|n1|n2|jlpt)"
    r"|deutschkenntnisse|sehr gute(n)? deutsch|fließend\w* deutsch|verhandlungssicher\w* deutsch",
    re.I,
)
_GERMAN_WORDS = re.compile(r"\b(und|wir|die|der|das|mit|für|sie|ihre|unser|bei|eine|oder|kenntnisse|erfahrung)\b", re.I)


def sponsorship(text: str) -> str | None:
    """'no' | 'yes' | None (not stated)."""
    if NEG.search(text):
        return "no"
    if POS.search(text):
        return "yes"
    return None


def evidence(text: str) -> str | None:
    """The sentence that mentions sponsorship/relocation, for display."""
    m = POS.search(text)
    if not m:
        return None
    start = max(text.rfind(".", 0, m.start()), text.rfind("\n", 0, m.start())) + 1
    ends = [i for i in (text.find(".", m.end()), text.find("\n", m.end())) if i != -1]
    end = min(ends) if ends else len(text)
    s = text[start:end].strip()
    return (s[:177] + "…") if len(s) > 180 else s


def language_required(text: str) -> str | None:
    m = LANG_REQ.search(text)
    if m:
        for lang in ("german", "dutch", "french", "japanese", "swedish", "danish", "polish", "spanish",
                     "italian", "portuguese", "arabic", "norwegian", "finnish"):
            if lang in m.group(0).lower():
                return lang.capitalize()
        return "German"
    words = text.split()
    if len(words) > 80 and len(_GERMAN_WORDS.findall(text)) / len(words) > 0.06:
        return "German"
    return None


# ---------- official sponsor registers (used for companies we don't already know) ----------
_SUFFIX = re.compile(r"\b(ltd|limited|plc|llp|llc|inc|gmbh|b v|bv|n v|nv|the|uk|group|holdings?|services|technologies|technology|europe|international)\b")


def _key(name: str) -> str:
    return re.sub(r"\s+", " ", _SUFFIX.sub(" ", norm(name))).strip()


class Registers:
    def __init__(self):
        self.uk: set[str] = set()
        self.nl: set[str] = set()
        self.status = {}

    def load(self):
        s = session()
        try:
            page = s.get("https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers", timeout=30).text
            m = re.search(r"https://assets\.publishing\.service\.gov\.uk/[^\"]+\.csv", page)
            if m:
                raw = s.get(m.group(0), timeout=120).content.decode("utf-8", "replace")
                for row in csv.reader(io.StringIO(raw)):
                    if row and row[0] and row[0] != "Organisation Name":
                        self.uk.add(_key(row[0]))
            self.status["uk_register"] = len(self.uk)
        except Exception as e:
            self.status["uk_register"] = f"error: {e.__class__.__name__}"
        try:
            page = s.get("https://ind.nl/en/public-register-recognised-sponsors/public-register-regular-labour-and-highly-skilled-migrants", timeout=60).text
            for cell in re.findall(r"<tr[^>]*>\s*<t[dh][^>]*>(.*?)</t[dh]>", page, re.S):
                name = re.sub(r"<[^>]+>", "", cell).strip()
                if name:
                    self.nl.add(_key(name))
            self.status["nl_register"] = len(self.nl)
        except Exception as e:
            self.status["nl_register"] = f"error: {e.__class__.__name__}"

    def known(self, company: str, country: str | None) -> bool:
        k = _key(company)
        if not k:
            return False
        if country == "United Kingdom":
            return k in self.uk
        if country == "Netherlands":
            return k in self.nl
        return False
