import os
from pathlib import Path
from dotenv import load_dotenv

try:
    import yaml
except ImportError as error:
    raise RuntimeError(
        "PyYAML is required to load sources.yaml. Install it with 'pip install pyyaml'."
    ) from error

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")


def _load_sources() -> dict:
    sources_path = ROOT_DIR / "sources.yaml"
    with sources_path.open("r", encoding="utf-8") as source_file:
        data = yaml.safe_load(source_file) or {}
    if not isinstance(data, dict):
        raise ValueError("sources.yaml must contain a top-level mapping.")
    return data


SOURCE_CONFIG = _load_sources()

# LLM
# LLM_PROVIDER = "anthropic"
# ANTHROPIC_API_KEY = ""
# OPENAI_API_KEY = ""
# LLM_MODEL_ANTHROPIC = "claude-sonnet-4-20250514"
# LLM_MODEL_OPENAI = "gpt-4o"
# LLM
#LLM_PROVIDER = "openai"  # AI Credits uses OpenAI-compatible format

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

# Model selection per provider
LLM_MODELS = {
    "anthropic": {
        "prefilter": "anthropic/claude-3.5-haiku",
        "scorer":    "claude-sonnet-4.6",
    },
    "openai": {
        "prefilter": "gpt-4o-mini",
        "scorer":    "gpt-4o",
    },
}

# AI Credits exposes the Anthropic model through its OpenAI-compatible API.
# Direct OpenAI mode continues to use the OpenAI model map below.
LLM_MODEL_PREFILTER = os.getenv("LLM_MODEL_PREFILTER", "gpt-4o-mini")
LLM_MODEL_SCORER = os.getenv(
    "LLM_MODEL_SCORER",
    "gpt-4o-mini",
)

# Switch this one line to change how AI calls are made
API_MODE = "aicredits"   # "aicredits" | "openai_direct"

AI_CREDITS_KEY = os.getenv("AI_CREDITS_KEY", "")
OPENAI_DIRECT_KEY = os.getenv("OPENAI_DIRECT_KEY", "")

# AI Credits proxy
AI_CREDITS_BASE_URL = "https://api.aicredits.in/v1"

# Tags + weights (must sum to 1.0)
TAGS = {
    "Time Sensitivity":     0.25,
    "Strategic Alignment":  0.20,
    "Regulatory Risk":      0.18,
    "Competitive Momentum": 0.12,
    "Financial Impact":     0.10,
    "Member Impact":        0.05,
    "Women in Healthcare":  0.10,
}

# Thresholds
HIGH_PRIORITY_THRESHOLD = 0.50
MIN_URGENCY_THRESHOLD   = 0.05

# SEC
# SEC_SUBMISSIONS_BASE = "https://data.sec.gov/submissions"
# SEC_HEADERS = {"User-Agent": "BSC-HealthcareIntel amrawat@uci.edu"}
# SEC_HEALTHCARE_CIKS = {
#     "UnitedHealth": "0000731766",
#     "Elevance":     "0001156039",
#     "CVS Health":   "0000064803",
#     "Humana":       "0000049071",
#     "Cigna":        "0001739940",
# }
SEC_SUBMISSIONS_BASE   = "https://data.sec.gov/submissions"
SEC_FULL_SEARCH_BASE   = "https://efts.sec.gov/LATEST/search-index"
SEC_COMPANY_FACTS_BASE = "https://data.sec.gov/api/xbrl/companyfacts"
SEC_HEADERS = {
    "User-Agent": os.getenv(
        "SEC_USER_AGENT",
        "Meridian-Pulse/1.0 amrawat@uci.edu",
    )
}
SEC_RATE_LIMIT_SLEEP   = 0.15

SEC_HEALTHCARE_CIKS = {
    company["name"]: str(company["cik"])
    for company in SOURCE_CONFIG.get("sec_companies", [])
    if company.get("active", True)
}

# RSS
# RSS_FEEDS = {
#     "Healthcare Dive":    "https://www.healthcaredive.com/feeds/news/",
#     "STAT News":          "https://www.statnews.com/feed/",
#     "KFF Health News":    "https://kffhealthnews.org/feed/",
#     "Fierce Healthcare":  "https://www.fiercehealthcare.com/rss/xml",
#     "Modern Healthcare":  "https://www.modernhealthcare.com/section/rss",
#     "Becker's Hospital":  "https://www.beckershospitalreview.com/rss.xml",
# }
RSS_FEEDS = {
    source["name"]: source["url"]
    for source in SOURCE_CONFIG.get("rss", [])
    if source.get("active", True)
}

# Limits
MAX_ARTICLES_PER_SOURCE = 20
MAX_DASHBOARD_ARTICLES  = 100

# Paths
BASE_OUTPUT_DIR = os.path.expanduser("~/Library/CloudStorage/OneDrive-UCIrvine/Documents/Capstone-BSC")
PATHS = {

    "transcripts": os.path.join(BASE_OUTPUT_DIR, "assets", "data"),
    "excel":       os.path.join(BASE_OUTPUT_DIR, "Exports", "Excel"),
    "ppt":         os.path.join(BASE_OUTPUT_DIR, "Exports", "PPT"),
    "pdf":         os.path.join(BASE_OUTPUT_DIR, "Exports", "PDF"),
    "docs":        os.path.join(BASE_OUTPUT_DIR, "Exports", "Docs"),
    "images":      os.path.join(BASE_OUTPUT_DIR, "Exports", "Images"),
    "cache":       os.path.join(BASE_OUTPUT_DIR, ".cache"),
}

def ensure_directories():
    for path in PATHS.values():
        os.makedirs(path, exist_ok=True)

# Urgency colors (used in dashboard cards)
# URGENCY_COLORS = {
#     "🔴 High":    "#FFE5E5",   # light red
#     "🟡 Medium":  "#FFF8E5",   # light amber
#     "🟢 Low":     "#E5F5E5",   # light green
#     "🔵 Minimal": "#EEF2F7",   # light beige-blue
# }
URGENCY_COLORS = {
    "🔴 High":    {"bg": "#FFF0F0", "text": "#CC0000", "border": "#FFB3B3"},
    "🟡 Medium":  {"bg": "#FFFBF0", "text": "#B8860B", "border": "#FFE082"},
    "🟢 Low":     {"bg": "#F0FFF4", "text": "#276749", "border": "#A8D5B5"},
    "🔵 Minimal": {"bg": "#F5F5F5", "text": "#555555", "border": "#CCCCCC"},
    "Unscored":   {"bg": "#F5F5F5", "text": "#555555", "border": "#CCCCCC"},
}

# App
APP_TITLE    = "Meridian Pulse"
APP_ICON     = "🔆"
APP_TAGLINE  = "Where healthcare intelligence peaks"
CHROMA_DB_PATH         = os.path.join(BASE_OUTPUT_DIR, ".chromadb")
CHROMA_COLLECTION_NAME = "healthcare_news"