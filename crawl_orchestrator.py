import requests
from urllib.parse import urlparse, urljoin, urlunparse
from bs4 import BeautifulSoup
import pandas as pd

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

EXCLUDED_PATH_KEYWORDS = [
    "login", "signin", "logout", "signup", "register",
    "cart", "checkout", "payment", "order",
    "admin", "wp-admin", "dashboard", "backend",
    "auth", "oauth", "sso", "reset", "forgot"
]

EXCLUDED_EXTENSIONS = (
    ".css", ".js", ".json", ".xml",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".ico", ".mp4", ".mp3", ".zip", ".pdf"
)

TRACKING_PARAMS = (
    "utm_", "gclid", "fbclid", "ref", "source", "campaign"
)

MAX_PATH_DEPTH = 3
MAX_URL_LENGTH = 120

# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

def crawl_site_sections(
    seed_url: str,
    run_scan_func,
    max_pages_per_section: int = 2,
):
    """
    Orchestrates section-based crawl.
    `run_scan_func` MUST be your existing scanner entry function.
    """

    raw_links = discover_internal_links(seed_url)
    clean_links = normalize_and_filter_links(raw_links, seed_url)
    sections = group_links_into_sections(clean_links)
    representative_pages = select_representative_pages(
        sections,
        max_pages_per_section
    )

    raw_results = scan_pages(representative_pages, run_scan_func)
    section_results = aggregate_section_results(raw_results)

    return {
        "scan_mode": "section_crawl",
        "seed_url": seed_url,
        "sections": section_results,
    }

# --------------------------------------------------
# LINK DISCOVERY
# --------------------------------------------------

def discover_internal_links(seed_url: str):
    html = requests.get(seed_url, timeout=15).text
    soup = BeautifulSoup(html, "html.parser")

    base = urlparse(seed_url).netloc
    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        abs_url = urljoin(seed_url, href)
        parsed = urlparse(abs_url)

        if parsed.netloc == base:
            links.add(abs_url)

    return list(links)

# --------------------------------------------------
# NORMALIZATION & FILTERING
# --------------------------------------------------

def normalize_and_filter_links(urls, seed_url):
    clean = []

    for url in urls:
        url = normalize_url(url)

        if not is_html_page(url):
            continue
        if is_excluded_path(url):
            continue
        if is_tracking_only(url):
            continue
        if is_too_deep(url):
            continue
        if is_too_long(url):
            continue
        if url in clean:
            continue

        clean.append(url)

    if seed_url not in clean:
        clean.insert(0, normalize_url(seed_url))

    return clean

def normalize_url(url):
    parsed = urlparse(url)
    clean_query = ""

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/"),
            "",
            clean_query,
            "",
        )
    )

def is_html_page(url):
    return not url.lower().endswith(EXCLUDED_EXTENSIONS)

def is_excluded_path(url):
    path = urlparse(url).path.lower()
    return any(k in path for k in EXCLUDED_PATH_KEYWORDS)

def is_tracking_only(url):
    query = urlparse(url).query.lower()
    return any(p in query for p in TRACKING_PARAMS)

def is_too_deep(url):
    depth = len([p for p in urlparse(url).path.split("/") if p])
    return depth > MAX_PATH_DEPTH

def is_too_long(url):
    return len(url) > MAX_URL_LENGTH

# --------------------------------------------------
# SECTION GROUPING
# --------------------------------------------------

def group_links_into_sections(urls):
    sections = {}

    for url in urls:
        section = infer_section(url)
        sections.setdefault(section, []).append(url)

    return sections

def infer_section(url):
    path = urlparse(url).path.strip("/")

    if not path:
        return "Home"

    return path.split("/")[0].capitalize()

# --------------------------------------------------
# REPRESENTATIVE PAGE SELECTION
# --------------------------------------------------

def select_representative_pages(sections, max_pages):
    selected = {}

    for section, urls in sections.items():
        ranked = sorted(
            urls,
            key=lambda u: (
                len(urlparse(u).path.split("/")),
                len(u),
            )
        )
        selected[section] = ranked[:max_pages]

    return selected

# --------------------------------------------------
# SCANNING (REUSE EXISTING SCANNER)
# --------------------------------------------------

def scan_pages(section_pages, run_scan_func):
    results = []

    for section, urls in section_pages.items():
        for url in urls:
            scan_result = run_scan_func(url)
            results.append({
                "section": section,
                "url": url,
                "result": scan_result,
            })

    return results

# --------------------------------------------------
# AGGREGATION
# --------------------------------------------------

def aggregate_section_results(raw_results):
    sections = {}

    for item in raw_results:
        section = item["section"]
        rules = item["result"]["rules"]

        sections.setdefault(section, {
            "section_name": section,
            "pages": [],
            "rules": [],
        })

        sections[section]["pages"].append(item["url"])
        sections[section]["rules"].append(rules)

    final = {}

    for section, data in sections.items():
        aggregated_rules = aggregate_rules(data["rules"])
        df = pd.DataFrame(aggregated_rules)

        final[section] = {
            "section_name": section,
            "pages": data["pages"],
            "rules": aggregated_rules,
            "section_score": calculate_section_score(df),
            "eaa_risk": calculate_eaa_risk(aggregated_rules),
        }

    return final

def aggregate_rules(rules_per_page):
    rule_map = {}

    for rules in rules_per_page:
        for rule in rules:
            rule_id = rule["id"]

            if rule_id not in rule_map:
                rule_map[rule_id] = rule.copy()
                rule_map[rule_id]["affected_pages"] = []

            if rule["status"] != "pass":
                rule_map[rule_id]["affected_pages"].append(rule.get("page_url"))

    return list(rule_map.values())

# --------------------------------------------------
# SCORING & EAA RISK
# --------------------------------------------------

SEVERITY_WEIGHTS = {
    "critical": 4,
    "serious": 3,
    "moderate": 2,
    "minor": 1,
}

STATUS_MULTIPLIER = {
    "fail": 1.0,
    "assisted": 0.6,
    "manual": 0.4,
    "pass": 0.0,
}

def calculate_section_score(df):
    if df.empty:
        return 100.0

    df = df.copy()
    df["weight"] = df["severity"].map(SEVERITY_WEIGHTS)
    df["multiplier"] = df["status"].map(STATUS_MULTIPLIER)
    impact = (df["weight"] * df["multiplier"]).sum()

    max_impact = len(df) * max(SEVERITY_WEIGHTS.values())
    score = 100 - (impact / max_impact * 100)

    return round(max(score, 0), 1)

def calculate_eaa_risk(rules):
    for r in rules:
        if (
            r.get("level") in ["A", "AA"]
            and r.get("severity") in ["critical", "serious"]
            and r.get("status") == "fail"
        ):
            return "High"

    for r in rules:
        if (
            r.get("level") in ["A", "AA"]
            and r.get("status") in ["manual", "assisted"]
        ):
            return "Medium"

    return "Low"
