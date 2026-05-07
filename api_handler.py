"""
api_handler.py – HTTP Client for News Fetcher + Bookmark System
Part B Requirement: urllib-based HTTP GET (and simulated POST) to a public news API.

API Used: GNews API (https://gnews.io) – free tier available.
Fallback:  NewsAPI.org is also supported via the PROVIDER constant.
"""

import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

# Replace with your own free key from https://gnews.io or https://newsapi.org.
# Environment variables keep the project portable across machines.
API_KEY = os.getenv("GNEWS_API_KEY", os.getenv("NEWS_API_KEY", "579f5af84cb94a4dbd2e2d12bf071be3"))

# Toggle between "gnews" and "newsapi"
PROVIDER = os.getenv("NEWS_PROVIDER", "gnews").strip().lower()

# India-first default country
DEFAULT_COUNTRY = os.getenv("NEWS_COUNTRY", "in").strip().lower()

# GNews endpoints
GNEWS_BASE_URL      = "https://gnews.io/api/v4"
GNEWS_TOP_HEADLINES = f"{GNEWS_BASE_URL}/top-headlines"
GNEWS_SEARCH        = f"{GNEWS_BASE_URL}/search"

# NewsAPI endpoints (alternative)
NEWSAPI_BASE_URL    = "https://newsapi.org/v2"
NEWSAPI_HEADLINES   = f"{NEWSAPI_BASE_URL}/top-headlines"
NEWSAPI_EVERYTHING  = f"{NEWSAPI_BASE_URL}/everything"

# Request settings
REQUEST_TIMEOUT = 10          # seconds
MAX_RESULTS     = 20          # articles per request
DEFAULT_LANG    = "en"

# Category→topic mapping (GNews uses "topic"; NewsAPI uses "category")
GNEWS_TOPICS = {
    "General":    "breaking-news",
    "Technology": "technology",
    "Sports":     "sports",
    "Business":   "business",
    "Science":    "science",
    "Health":     "health",
    "World":      "world",
    "Nation":     "nation",
    "Entertainment": "entertainment",
}

NEWSAPI_CATEGORIES = {
    "General": "general", "Technology": "technology",
    "Sports":  "sports",  "Business":   "business",
    "Science": "science", "Health":     "health",
    "Entertainment": "entertainment",
}


# ─────────────────────────────────────────────
# PART B – HTTP GET  (Primary)
# ─────────────────────────────────────────────

def fetch_top_headlines(category: str = "Nation",
                        country: str = DEFAULT_COUNTRY) -> list[dict]:
    """
    Performs an HTTP GET request to retrieve top news headlines.

    Part B requirement:
        urllib.request.urlopen() is used for the GET request.
        JSON response is parsed with json.loads().

    Args:
        category: News category string (key of GNEWS_TOPICS).
        country:  ISO country code (used by NewsAPI).

    Returns:
        List of article dicts with keys: title, description, url, source, published_at.
    """
    if PROVIDER == "gnews":
        return _gnews_top_headlines(category, country)
    else:
        return _newsapi_top_headlines(category, country)


def search_news(query: str, category: str = "Nation",
                country: str = DEFAULT_COUNTRY) -> list[dict]:
    """
    Performs an HTTP GET request with a search query.

    Part B requirement: GET parameters are encoded with urllib.parse.urlencode().

    Args:
        query:    Keyword search string.
        category: Optional category filter.

    Returns:
        List of article dicts.
    """
    if not query.strip():
        return fetch_top_headlines(category)

    if PROVIDER == "gnews":
        return _gnews_search(query, category, country)
    else:
        return _newsapi_search(query, country)


# ─────────────────────────────────────────────
# PART B – HTTP POST  (Simulated / Optional)
# ─────────────────────────────────────────────

def post_feedback(article_url: str, rating: int,
                  comment: str = "") -> dict:
    """
    Simulates an HTTP POST request for sending article feedback.

    Part B (optional) requirement:
        Uses urllib.request.Request with POST data encoded by urllib.parse.urlencode().
        POST data is sent as application/x-www-form-urlencoded bytes.

    NOTE: This sends to httpbin.org/post (a free echo service) for demonstration,
    since the news APIs used are read-only.  In a real app this would target
    your own backend endpoint.

    Args:
        article_url: URL of the article being rated.
        rating:      Integer rating 1–5.
        comment:     Optional text comment.

    Returns:
        Dict with 'success' key and 'response' from the echo server.
    """
    endpoint = "https://httpbin.org/post"

    post_data = urllib.parse.urlencode({
        "article_url": article_url,
        "rating":      str(rating),
        "comment":     comment,
        "timestamp":   str(int(time.time())),
    }).encode("utf-8")     # encode to bytes as required by urllib

    headers = {
        "Content-Type":  "application/x-www-form-urlencoded",
        "User-Agent":    "NewsFetcherApp/1.0",
        "Accept":        "application/json",
    }

    request = urllib.request.Request(
        endpoint,
        data=post_data,         # presence of data makes it a POST
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
            logger.info("POST feedback sent for: %s", article_url)
            return {"success": True, "response": data}
    except urllib.error.HTTPError as exc:
        logger.error("POST HTTP error %d: %s", exc.code, exc.reason)
        return {"success": False, "error": f"HTTP {exc.code}: {exc.reason}"}
    except urllib.error.URLError as exc:
        logger.error("POST URL error: %s", exc.reason)
        return {"success": False, "error": str(exc.reason)}
    except Exception as exc:
        logger.error("POST unexpected error: %s", exc)
        return {"success": False, "error": str(exc)}


# ─────────────────────────────────────────────
# GNEWS PRIVATE HELPERS
# ─────────────────────────────────────────────

def _gnews_top_headlines(category: str, country: str) -> list[dict]:
    topic = GNEWS_TOPICS.get(category, "breaking-news")
    params = {
        "token":    API_KEY,
        "topic":    topic,
        "lang":     DEFAULT_LANG,
        "country":  country,
        "max":      MAX_RESULTS,
    }
    return _get_request(GNEWS_TOP_HEADLINES, params, _parse_gnews)


def _gnews_search(query: str, category: str, country: str) -> list[dict]:
    topic = GNEWS_TOPICS.get(category, "breaking-news")
    params = {
        "token": API_KEY,
        "q":     query,
        "topic": topic,
        "lang":  DEFAULT_LANG,
        "country": country,
        "max":   MAX_RESULTS,
    }
    return _get_request(GNEWS_SEARCH, params, _parse_gnews)


def _parse_gnews(data: dict) -> list[dict]:
    """Normalises GNews JSON to a flat list of article dicts."""
    articles = []
    for item in data.get("articles", []):
        articles.append({
            "title":        item.get("title", "No Title"),
            "description":  item.get("description", "No description available."),
            "url":          item.get("url", ""),
            "source":       item.get("source", {}).get("name", "Unknown"),
            "published_at": item.get("publishedAt", ""),
            "image":        item.get("image", ""),
        })
    return articles


# ─────────────────────────────────────────────
# NEWSAPI PRIVATE HELPERS
# ─────────────────────────────────────────────

def _newsapi_top_headlines(category: str, country: str) -> list[dict]:
    cat = NEWSAPI_CATEGORIES.get(category, "general")
    params = {
        "apiKey":   API_KEY,
        "category": cat,
        "country":  country,
        "pageSize": MAX_RESULTS,
    }
    return _get_request(NEWSAPI_HEADLINES, params, _parse_newsapi)


def _newsapi_search(query: str, country: str) -> list[dict]:
    search_query = query.strip()
    if country == "in" and "india" not in search_query.lower():
        search_query = f"{search_query} India"

    params = {
        "apiKey":   API_KEY,
        "q":        search_query,
        "language": DEFAULT_LANG,
        "pageSize": MAX_RESULTS,
        "sortBy":   "publishedAt",
    }
    return _get_request(NEWSAPI_EVERYTHING, params, _parse_newsapi)


def _parse_newsapi(data: dict) -> list[dict]:
    """Normalises NewsAPI JSON to a flat list of article dicts."""
    articles = []
    for item in data.get("articles", []):
        articles.append({
            "title":        item.get("title") or "No Title",
            "description":  item.get("description") or "No description available.",
            "url":          item.get("url", ""),
            "source":       (item.get("source") or {}).get("name", "Unknown"),
            "published_at": item.get("publishedAt", ""),
            "image":        item.get("urlToImage", ""),
        })
    return articles


# ─────────────────────────────────────────────
# CORE HTTP GET UTILITY
# ─────────────────────────────────────────────

def _get_request(base_url: str, params: dict,
                 parser_fn) -> list[dict]:
    """
    Performs a urllib HTTP GET request and parses the JSON response.

    Steps (Part B):
        1. Build URL with urllib.parse.urlencode()
        2. Create urllib.request.Request with custom headers
        3. Open with urllib.request.urlopen()
        4. Read and decode response bytes
        5. Parse JSON with json.loads()
        6. Handle HTTPError and URLError separately

    Args:
        base_url:  API endpoint URL without query string.
        params:    Dict of query parameters.
        parser_fn: Callable that converts raw JSON dict → list of article dicts.

    Returns:
        List of normalised article dicts, or empty list on error.
    """
    query_string = urllib.parse.urlencode(params)
    full_url     = f"{base_url}?{query_string}"

    request = urllib.request.Request(
        full_url,
        headers={
            "User-Agent": "NewsFetcherApp/1.0 (Educational Project)",
            "Accept":     "application/json",
        }
    )

    logger.info("GET %s", full_url)

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            status = response.getcode()
            raw    = response.read().decode("utf-8")
            logger.info("Response status: %d, bytes: %d", status, len(raw))

            data = json.loads(raw)
            articles = parser_fn(data)
            logger.info("Parsed %d articles.", len(articles))
            return articles

    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        logger.error("HTTP %d %s | %s", exc.code, exc.reason, err_body[:200])
        raise ConnectionError(f"API error {exc.code}: {exc.reason}") from exc

    except urllib.error.URLError as exc:
        logger.error("URL error: %s", exc.reason)
        raise ConnectionError(f"Network error: {exc.reason}") from exc

    except json.JSONDecodeError as exc:
        logger.error("JSON decode error: %s", exc)
        raise ValueError("Invalid JSON received from API.") from exc

    except Exception as exc:
        logger.error("Unexpected error in GET request: %s", exc)
        raise


# ─────────────────────────────────────────────
# OFFLINE / DEMO DATA
# ─────────────────────────────────────────────

def get_demo_articles(category: str = "Nation") -> list[dict]:
    """
    Returns hard-coded demo articles for offline mode testing.
    No API key or internet required.
    """
    return [
        {
            "title":        f"[DEMO] India {category}: Major Development Announced",
            "description":  "This is a demo article shown in offline mode. "
                            "Connect to the internet and set your API key for live news.",
            "url":          "https://example.com/demo-1",
            "source":       "Demo Source",
            "published_at": "2025-01-01T00:00:00Z",
            "image":        "",
        },
        {
            "title":        f"[DEMO] India {category} Update: Latest Insights",
            "description":  "Demo article 2 – Offline mode is active. "
                            "Your saved bookmarks are still fully accessible.",
            "url":          "https://example.com/demo-2",
            "source":       "Demo Source",
            "published_at": "2025-01-01T01:00:00Z",
            "image":        "",
        },
        {
            "title":        "[DEMO] How to set your API key",
            "description":  "Edit api_handler.py and replace "
                            "YOUR_GNEWS_API_KEY_HERE with your free GNews key "
                            "from https://gnews.io",
            "url":          "https://gnews.io",
            "source":       "Setup Guide",
            "published_at": "2025-01-01T02:00:00Z",
            "image":        "",
        },
    ]


# ─────────────────────────────────────────────
# SENTIMENT ANALYSIS  (Unique Feature – keyword-based)
# ─────────────────────────────────────────────

POSITIVE_WORDS = {
    "breakthrough", "success", "win", "victory", "growth",
    "improve", "innovation", "positive", "record", "gain",
    "profit", "rally", "rise", "recover", "launch", "achieve",
}

NEGATIVE_WORDS = {
    "crash", "fail", "loss", "decline", "crisis", "fall",
    "disaster", "attack", "death", "war", "conflict", "risk",
    "drop", "warning", "concern", "scandal", "fraud", "crime",
}


def analyse_sentiment(title: str, description: str = "") -> str:
    """
    Performs basic keyword-based sentiment analysis.

    Returns one of: 'Positive', 'Negative', 'Neutral'.
    This satisfies the 'Simple sentiment tagging' unique feature requirement.
    """
    text = f"{title} {description}".lower()
    words = set(re.findall(r"[a-z']+", text))

    pos_score = len(words & POSITIVE_WORDS)
    neg_score = len(words & NEGATIVE_WORDS)

    if pos_score > neg_score:
        return "Positive"
    elif neg_score > pos_score:
        return "Negative"
    return "Neutral"
