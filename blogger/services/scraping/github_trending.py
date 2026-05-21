"""
GitHub Trending scraper.
Parses the GitHub trending page to extract repository information.
"""

import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from utils.mock_data import get_mock_github_trending

logger = logging.getLogger(__name__)

GITHUB_TRENDING_URL = "https://github.com/trending"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def scrape_github_trending() -> list[dict]:
    """
    Scrape GitHub trending repositories page.

    Returns:
        List of dictionaries containing repo information.
        Falls back to mock data on failure.
    """
    logger.info("Scraping GitHub Trending...")

    try:
        response = httpx.get(
            GITHUB_TRENDING_URL,
            headers=HEADERS,
            timeout=15.0,
            follow_redirects=True,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        repos = []

        # Each trending repo is in an <article> element with class "Box-row"
        articles = soup.select("article.Box-row")

        if not articles:
            logger.warning("No trending repos found in HTML. Structure may have changed.")
            return get_mock_github_trending()

        for article in articles[:10]:  # Top 10 repos
            try:
                # Repository name (e.g., "owner/repo")
                name_tag = article.select_one("h2 a")
                if not name_tag:
                    continue

                repo_name = name_tag.text.strip().replace("\n", "").replace(" ", "")

                # Description
                desc_tag = article.select_one("p")
                description = desc_tag.text.strip() if desc_tag else "No description"

                # URL
                href = name_tag.get("href", "")
                url = f"https://github.com{href}" if href else ""

                # Stars (total)
                star_tags = article.select("a.Link--muted")
                stars = ""
                if star_tags:
                    stars = star_tags[0].text.strip()

                # Programming language
                lang_tag = article.select_one("[itemprop='programmingLanguage']")
                language = lang_tag.text.strip() if lang_tag else "Unknown"

                # Stars today
                stars_today = ""
                stars_today_tag = article.select_one("span.d-inline-block.float-sm-right")
                if stars_today_tag:
                    stars_today = stars_today_tag.text.strip()

                repos.append({
                    "source": "github_trending",
                    "title": repo_name,
                    "description": description,
                    "url": url,
                    "stars": stars,
                    "language": language,
                    "stars_today": stars_today,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                })

            except Exception as e:
                logger.debug(f"Error parsing repo entry: {e}")
                continue

        if repos:
            logger.info(f"Scraped {len(repos)} GitHub trending repos")
            return repos

        logger.warning("Parsed 0 repos, falling back to mock data")
        return get_mock_github_trending()

    except httpx.HTTPError as e:
        logger.warning(f"GitHub Trending scrape failed: {e}. Using mock data.")
        return get_mock_github_trending()
    except Exception as e:
        logger.error(f"Unexpected error scraping GitHub: {e}. Using mock data.")
        return get_mock_github_trending()
