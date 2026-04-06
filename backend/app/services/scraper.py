"""
RSS and news scraper.

Fetches headlines from free RSS feeds and deduplicates by title hash.
Used by Workflow 1 (Market Intelligence) to gather market news.
"""

import hashlib
import logging
from datetime import datetime

import feedparser
import httpx

logger = logging.getLogger("smv.scraper")

# ──────────────────────────────────────────────
# RSS Feed Sources (all free, no API key needed)
# ──────────────────────────────────────────────

RSS_FEEDS = {
    "yahoo_finance": "https://finance.yahoo.com/news/rssindex",
    "marketwatch": "https://feeds.marketwatch.com/marketwatch/topstories",
    "investing_com": "https://www.investing.com/rss/news.rss",
    "reddit_stocks": "https://old.reddit.com/r/stocks/.rss",
    "reddit_wsb": "https://old.reddit.com/r/wallstreetbets/.rss",
    "reddit_investing": "https://old.reddit.com/r/investing/.rss",
    "sec_edgar": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&dateb=&owner=include&count=20&search_text=&start=0&output=atom",
}

# Industry keyword mapping
INDUSTRY_KEYWORDS = {
    "AI & Semiconductors": [
        "nvidia", "nvda", "amd", "intel", "semiconductor", "chip", "ai ", "artificial intelligence",
        "gpu", "machine learning", "llm", "openai", "google ai", "deepmind",
    ],
    "Cloud Computing": [
        "cloud", "aws", "azure", "gcp", "saas", "iaas", "paas", "snowflake", "datadog",
    ],
    "Cybersecurity": [
        "cybersecurity", "cyber", "crowdstrike", "palo alto", "fortinet", "hack", "breach",
    ],
    "Renewable Energy": [
        "solar", "wind energy", "renewable", "clean energy", "ev charging", "enphase",
        "first solar", "nextera",
    ],
    "Electric Vehicles": [
        "tesla", "tsla", "ev ", "electric vehicle", "rivian", "lucid", "nio", "byd",
        "charging station",
    ],
    "Biotechnology": [
        "biotech", "pharma", "fda approval", "drug trial", "clinical trial", "moderna",
        "pfizer", "mrna",
    ],
    "Fintech": [
        "fintech", "paypal", "square", "block inc", "stripe", "crypto", "bitcoin",
        "ethereum", "blockchain", "defi",
    ],
    "E-Commerce": [
        "amazon", "amzn", "shopify", "e-commerce", "ecommerce", "online retail",
    ],
    "Healthcare Tech": [
        "healthtech", "teladoc", "telehealth", "digital health", "medical device",
    ],
    "Aerospace & Defense": [
        "boeing", "lockheed", "raytheon", "northrop", "defense contract", "space",
        "spacex", "rocket",
    ],
    "Banking & Financial Services": [
        "jpmorgan", "goldman", "bank of america", "wells fargo", "citigroup",
        "interest rate", "federal reserve", "fed rate",
    ],
    "Oil & Gas": [
        "oil price", "crude oil", "natural gas", "exxon", "chevron", "opec",
        "petroleum", "drilling",
    ],
}


# ──────────────────────────────────────────────
# Scraping
# ──────────────────────────────────────────────

def _hash_title(title: str) -> str:
    """Generate a fingerprint hash for deduplication."""
    normalized = title.lower().strip()
    return hashlib.md5(normalized.encode()).hexdigest()


def _detect_industries(text: str) -> list[str]:
    """Detect industries mentioned in a text snippet."""
    text_lower = text.lower()
    matched = []
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            matched.append(industry)
    return matched


async def fetch_rss_feed(name: str, url: str) -> list[dict]:
    """
    Fetch and parse a single RSS feed.
    Returns list of article dicts.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"User-Agent": "SMV-Bot/1.0"})
            resp.raise_for_status()
            content = resp.text
    except Exception as e:
        logger.warning(f"Failed to fetch {name}: {e}")
        return []

    feed = feedparser.parse(content)
    articles = []

    for entry in feed.entries[:20]:  # Limit per feed
        title = entry.get("title", "").strip()
        summary = entry.get("summary", entry.get("description", "")).strip()
        link = entry.get("link", "")
        published = entry.get("published", "")

        if not title:
            continue

        # Detect industries
        combined_text = f"{title} {summary}"
        industries = _detect_industries(combined_text)

        articles.append({
            "title": title,
            "summary": summary[:500],  # Truncate long summaries
            "link": link,
            "source": name,
            "published": published,
            "fingerprint": _hash_title(title),
            "industries": industries,
            "fetched_at": datetime.utcnow().isoformat(),
        })

    logger.debug(f"Fetched {len(articles)} articles from {name}")
    return articles


async def fetch_all_feeds() -> list[dict]:
    """
    Fetch all RSS feeds and deduplicate by title hash.
    Returns a combined, deduplicated list of articles.
    """
    all_articles = []
    seen_fingerprints = set()

    for name, url in RSS_FEEDS.items():
        articles = await fetch_rss_feed(name, url)
        for article in articles:
            fp = article["fingerprint"]
            if fp not in seen_fingerprints:
                seen_fingerprints.add(fp)
                all_articles.append(article)

    logger.info(f"Total unique articles: {len(all_articles)} (from {len(RSS_FEEDS)} feeds)")
    return all_articles


def group_by_industry(articles: list[dict]) -> dict[str, list[dict]]:
    """Group articles by detected industry."""
    groups: dict[str, list[dict]] = {}
    for article in articles:
        for industry in article.get("industries", []):
            if industry not in groups:
                groups[industry] = []
            groups[industry].append(article)

    # Also collect unclassified articles
    unclassified = [a for a in articles if not a.get("industries")]
    if unclassified:
        groups["General Market"] = unclassified

    return groups
