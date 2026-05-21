"""
Hacker News scraper.
Scrapes the Hacker News front page for top stories.
"""

import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from utils.mock_data import get_mock_hacker_news

logger = logging.getLogger(__name__)

HN_URL = "https://news.ycombinator.com/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
}


def scrape_hacker_news() -> list[dict]:
    """
    Scrape Hacker News front page for top stories.

    Returns:
        List of dictionaries containing story information.
        Falls back to mock data on failure.
    """
    logger.info("Scraping Hacker News...")

    try:
        response = httpx.get(HN_URL, headers=HEADERS, timeout=15.0)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        stories = []

        # HN uses <tr class="athing"> for story rows
        story_rows = soup.select("tr.athing")

        if not story_rows:
            logger.warning("No HN stories found. Structure may have changed.")
            return get_mock_hacker_news()

        for row in story_rows[:15]:  # Top 15 stories
            try:
                # Title and link
                title_cell = row.select_one("td.title")
                if not title_cell:
                    continue

                title_link = title_cell.select_one("a.titleline > a") or title_cell.select_one("span.titleline > a")
                if not title_link:
                    # Alternative selector
                    title_link = title_cell.select_one("a")

                if not title_link:
                    continue

                title = title_link.text.strip()
                url = title_link.get("href", "")

                # Make relative URLs absolute
                if url and not url.startswith("http"):
                    url = f"https://news.ycombinator.com/{url}"

                # Score and comments are in the next sibling row
                subtext_row = row.find_next_sibling("tr")
                points = "0"
                comments = "0"

                if subtext_row:
                    subtext = subtext_row.select_one("td.subtext") or subtext_row.select_one("span.subline")
                    if subtext:
                        # Points
                        score_tag = subtext.select_one("span.score")
                        if score_tag:
                            points = score_tag.text.replace(" points", "").replace(" point", "").strip()

                        # Comments
                        comment_links = subtext.select("a")
                        for link in comment_links:
                            text = link.text.strip()
                            if "comment" in text.lower():
                                comments = text.split()[0]
                                break

                stories.append({
                    "source": "hacker_news",
                    "title": title,
                    "url": url,
                    "points": points,
                    "comments": comments,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                })

            except Exception as e:
                logger.debug(f"Error parsing HN story: {e}")
                continue

        if stories:
            logger.info(f"Scraped {len(stories)} Hacker News stories")
            return stories

        logger.warning("Parsed 0 HN stories, falling back to mock data")
        return get_mock_hacker_news()

    except httpx.HTTPError as e:
        logger.warning(f"Hacker News scrape failed: {e}. Using mock data.")
        return get_mock_hacker_news()
    except Exception as e:
        logger.error(f"Unexpected error scraping HN: {e}. Using mock data.")
        return get_mock_hacker_news()
