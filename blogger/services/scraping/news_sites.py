"""
News sites scraper.
Scrapes headlines from BBC, Dawn (Pakistan), and Al Jazeera.
"""

import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from utils.mock_data import get_mock_news

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _scrape_bbc() -> list[dict]:
    """Scrape BBC News headlines."""
    logger.info("Scraping BBC News...")
    url = "https://www.bbc.com/news"

    try:
        response = httpx.get(url, headers=HEADERS, timeout=15.0, follow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        headlines = []

        # BBC uses data-testid attributes for headlines
        headline_tags = soup.select("[data-testid='card-headline']")

        if not headline_tags:
            # Fallback: look for h3 tags within links
            headline_tags = soup.select("h3")

        for tag in headline_tags[:8]:
            title = tag.text.strip()
            if not title or len(title) < 10:
                continue

            # Try to find parent link
            link_tag = tag.find_parent("a")
            href = ""
            if link_tag:
                href = link_tag.get("href", "")
                if href and not href.startswith("http"):
                    href = f"https://www.bbc.com{href}"

            headlines.append({
                "source": "bbc",
                "title": title,
                "url": href,
                "category": "news",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })

        logger.info(f"Scraped {len(headlines)} BBC headlines")
        return headlines

    except Exception as e:
        logger.warning(f"BBC scrape failed: {e}")
        return []


def _scrape_dawn() -> list[dict]:
    """Scrape Dawn News (Pakistan) headlines."""
    logger.info("Scraping Dawn News...")
    url = "https://www.dawn.com"

    try:
        response = httpx.get(url, headers=HEADERS, timeout=15.0, follow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        headlines = []

        # Dawn uses article tags and h2 headlines
        article_links = soup.select("article h2 a, .story__title a, h2.story__title a")

        if not article_links:
            # Broader fallback
            article_links = soup.select("h2 a, h3 a")

        seen_titles: set[str] = set()
        for link in article_links[:8]:
            title = link.text.strip()
            if not title or len(title) < 10 or title in seen_titles:
                continue

            seen_titles.add(title)
            href = link.get("href", "")
            if href and not href.startswith("http"):
                href = f"https://www.dawn.com{href}"

            headlines.append({
                "source": "dawn",
                "title": title,
                "url": href,
                "category": "pakistan",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })

        logger.info(f"Scraped {len(headlines)} Dawn headlines")
        return headlines

    except Exception as e:
        logger.warning(f"Dawn scrape failed: {e}")
        return []


def _scrape_aljazeera() -> list[dict]:
    """Scrape Al Jazeera headlines."""
    logger.info("Scraping Al Jazeera...")
    url = "https://www.aljazeera.com"

    try:
        response = httpx.get(url, headers=HEADERS, timeout=15.0, follow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        headlines = []

        # Al Jazeera uses various headline classes
        headline_tags = soup.select(
            "h3.article-card__title a, "
            ".aje-card-content h3 a, "
            "h3 a[href*='/news/'], "
            "h3 a[href*='/economy/'], "
            "h3 a[href*='/features/']"
        )

        if not headline_tags:
            # Broader fallback
            headline_tags = soup.select("h3 a")

        seen_titles: set[str] = set()
        for tag in headline_tags[:8]:
            title = tag.text.strip()
            if not title or len(title) < 10 or title in seen_titles:
                continue

            seen_titles.add(title)
            href = tag.get("href", "")
            if href and not href.startswith("http"):
                href = f"https://www.aljazeera.com{href}"

            headlines.append({
                "source": "aljazeera",
                "title": title,
                "url": href,
                "category": "world",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })

        logger.info(f"Scraped {len(headlines)} Al Jazeera headlines")
        return headlines

    except Exception as e:
        logger.warning(f"Al Jazeera scrape failed: {e}")
        return []


def scrape_news_sites() -> list[dict]:
    """
    Scrape headlines from all configured news sites.
    Falls back to mock data if all scrapers fail.

    Returns:
        Combined list of headlines from BBC, Dawn, and Al Jazeera.
    """
    all_headlines = []

    all_headlines.extend(_scrape_bbc())
    all_headlines.extend(_scrape_dawn())
    all_headlines.extend(_scrape_aljazeera())

    if not all_headlines:
        logger.warning("All news scrapers failed. Using mock data.")
        return get_mock_news()

    logger.info(f"Total news headlines scraped: {len(all_headlines)}")
    return all_headlines
