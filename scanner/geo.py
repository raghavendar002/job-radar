"""Turn a free-text job location into a partition: 'india' (South India), 'abroad', or None."""
import re

from . import config

SOUTH_INDIA = {
    "bengaluru": "Bengaluru", "bangalore": "Bengaluru", "chennai": "Chennai", "madras": "Chennai",
    "hyderabad": "Hyderabad", "secunderabad": "Hyderabad", "kochi": "Kochi", "cochin": "Kochi",
    "ernakulam": "Kochi", "thiruvananthapuram": "Thiruvananthapuram", "trivandrum": "Thiruvananthapuram",
    "technopark": "Thiruvananthapuram", "coimbatore": "Coimbatore", "mysore": "Mysuru",
    "mysuru": "Mysuru", "madurai": "Madurai", "mangalore": "Mangaluru", "mangaluru": "Mangaluru",
    "visakhapatnam": "Visakhapatnam", "vizag": "Visakhapatnam", "vijayawada": "Vijayawada",
    "puducherry": "Puducherry", "pondicherry": "Puducherry", "tiruchirappalli": "Trichy",
    "trichy": "Trichy", "hubli": "Hubballi", "hubballi": "Hubballi", "salem": "Salem",
    "karnataka": "Karnataka", "tamil nadu": "Tamil Nadu", "telangana": "Telangana",
    "kerala": "Kerala", "andhra pradesh": "Andhra Pradesh",
}
OTHER_INDIA = [
    "india", "mumbai", "pune", "delhi", "gurgaon", "gurugram", "noida", "kolkata", "ahmedabad",
    "jaipur", "chandigarh", "indore", "maharashtra", "haryana", "uttar pradesh", "gujarat",
    "bhubaneswar", "nagpur", "lucknow", "mohali", "vadodara", "thane",
]

COUNTRIES = {
    "Germany": ["germany", "deutschland", "berlin", "munich", "münchen", "muenchen", "hamburg", "frankfurt",
                "cologne", "köln", "stuttgart", "düsseldorf", "dusseldorf", "leipzig", "dresden",
                "nuremberg", "nürnberg", "karlsruhe", "bonn", "hannover", "walldorf", "de-"],
    "Netherlands": ["netherlands", "nederland", "amsterdam", "rotterdam", "utrecht", "eindhoven",
                    "the hague", "den haag", "delft", "nl-"],
    "Ireland": ["ireland", "dublin", "cork", "galway", "limerick"],
    "United Kingdom": ["united kingdom", "uk", "u.k.", "london", "manchester", "edinburgh", "bristol",
                       "glasgow", "belfast", "leeds", "birmingham", "england", "scotland", "wales",
                       "great britain", "gb-", "reading", "milton keynes", "oxford"],
    "Singapore": ["singapore"],
    "United Arab Emirates": ["united arab emirates", "uae", "dubai", "abu dhabi"],
    "Luxembourg": ["luxembourg"],
    "Switzerland": ["switzerland", "zurich", "zürich", "geneva", "genève", "lausanne", "basel", "zug"],
    "Sweden": ["sweden", "stockholm", "gothenburg", "göteborg", "malmö", "malmo"],
    "Denmark": ["denmark", "copenhagen", "aarhus"],
    "Japan": ["japan", "tokyo", "osaka", "kyoto", "fukuoka"],
    "Canada": ["canada", "toronto", "vancouver", "montreal", "montréal", "ottawa", "waterloo",
               "calgary", "edmonton", "ontario", "british columbia", "quebec"],
    "Australia": ["australia", "sydney", "melbourne", "brisbane", "perth", "canberra", "adelaide"],
    "New Zealand": ["new zealand", "auckland", "wellington"],
    "Poland": ["poland", "warsaw", "warszawa", "krakow", "kraków", "wroclaw", "wrocław", "gdansk", "poznan"],
    "Spain": ["spain", "madrid", "barcelona", "valencia", "malaga", "málaga"],
    "Portugal": ["portugal", "lisbon", "lisboa", "porto"],
    "France": ["france", "paris", "lyon", "toulouse", "nantes"],
    "Austria": ["austria", "vienna", "wien", "graz"],
    "Finland": ["finland", "helsinki", "espoo"],
    "Norway": ["norway", "oslo"],
    "Belgium": ["belgium", "brussels", "antwerp", "ghent"],
    "Estonia": ["estonia", "tallinn"],
    "Lithuania": ["lithuania", "vilnius"],
    "Thailand": ["thailand", "bangkok"],
    "Malaysia": ["malaysia", "kuala lumpur", "penang"],
    "Hong Kong": ["hong kong"],
    "Saudi Arabia": ["saudi arabia", "riyadh", "jeddah"],
    "Qatar": ["qatar", "doha"],
    "United States": ["united states", "usa", "u.s.", "new york", "san francisco", "seattle", "austin",
                      "boston", "california", "texas", "chicago", "atlanta", "denver", "los angeles",
                      "san jose", "palo alto", "mountain view", "sunnyvale", "menlo park", "bellevue",
                      "redmond", "washington, dc", "new jersey", "jersey city", "virginia", "plano",
                      "dallas", "miami", "philadelphia", "pittsburgh", "portland", "salt lake",
                      "phoenix", "charlotte", "minneapolis", "raleigh", "columbus", "detroit",
                      "massachusetts", "illinois", "colorado", "georgia, us", "oregon", "utah",
                      "arizona", "north carolina", "minnesota", "missouri", "ohio", "michigan",
                      "maryland", "pennsylvania", "connecticut", "wisconsin", "tennessee", "florida",
                      "mclean", "richmond", "brooklyn", "remote - us", "remote, us", "us-remote",
                      "us remote", "remote (us)", "remote us", "nyc", "sf bay", "bay area"],
}

_cache: dict[str, re.Pattern] = {}


def _rx(word: str) -> re.Pattern:
    p = _cache.get(word)
    if p is None:
        if word.endswith("-"):  # ISO-ish prefixes like "GB-London"
            p = re.compile(r"(?<![a-z])" + re.escape(word))
        else:
            p = re.compile(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])")
        _cache[word] = p
    return p


def _has(text: str, word: str) -> bool:
    return bool(_rx(word).search(text))


US_STATE_ABBR = re.compile(r",\s*(CA|NY|WA|TX|MA|IL|CO|GA|NJ|VA|NC|PA|OR|UT|AZ|FL|MN|MO|OH|MI|MD|CT|DC)\b")


def classify(location: str | None, *, remote_flag: bool = False):
    """Return (partition, place) where partition is 'india' | 'abroad' | None."""
    raw = location or ""
    t = raw.lower()
    if not t.strip():
        return None, None
    is_remote = remote_flag or "remote" in t

    for key, city in SOUTH_INDIA.items():
        if _has(t, key):
            return "india", city

    if any(_has(t, w) for w in OTHER_INDIA):
        if is_remote and config.INCLUDE_REMOTE_INDIA and not any(_has(t, c) for c in OTHER_INDIA[1:]):
            return "india", "Remote (India)"
        return None, None

    for country, words in COUNTRIES.items():
        if country == "United States":
            continue
        if any(_has(t, w) for w in words):
            if country in config.TARGET_COUNTRIES:
                # "Remote - UK" with no office city is still a UK job; keep it.
                return "abroad", country
            return None, None

    if any(_has(t, w) for w in COUNTRIES["United States"]) or US_STATE_ABBR.search(raw):
        if "United States" in config.TARGET_COUNTRIES:
            return "abroad", "United States"
    return None, None


def classify_many(locations: list[str], *, remote_flag: bool = False):
    """Several locations for one job: prefer South India, then the best abroad country."""
    best = (None, None)
    for loc in locations:
        part, place = classify(loc, remote_flag=remote_flag)
        if part == "india":
            return part, place
        if part == "abroad":
            if best[0] is None or config.TARGET_COUNTRIES.get(place, 0) > config.TARGET_COUNTRIES.get(best[1], 0):
                best = (part, place)
    return best
