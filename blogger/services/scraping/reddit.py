"""
Reddit scraper.
Scrapes top posts from specified subreddits using old.reddit.com for easier parsing.
"""

import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from utils.mock_data import get_mock_reddit

logger = logging.getLogger(__name__)

SUBREDDITS = ["programming", "MachineLearning", "LocalLLaMA", "Python", "rust"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _scrape_subreddit(subreddit: str) -> list[dict]:
    """
    Scrape top posts from a single subreddit using old.reddit.com.

    Args:
        subreddit: Subreddit name (without r/ prefix).

    Returns:
        List of post dictionaries.
    """
    url = f"https://old.reddit.com/r/{subreddit}/hot/"
    logger.info(f"Scraping r/{subreddit}...")

    try:
        response = httpx.get(url, headers=HEADERS, timeout=15.0, follow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        posts = []

        # old.reddit.com uses div.thing for each post
        things = soup.select("div.thing[data-type='link']")

        if not things:
            # Fallback: try regular link elements
            things = soup.select("div.thing")

        for thing in things[:8]:
            try:
                # Skip promoted/sponsored posts
                if "promoted" in thing.get("class", []) or thing.get("data-promoted"):
                    continue

                # Title and link
                title_tag = thing.select_one("a.title")
                if not title_tag:
                    continue

                title = title_tag.text.strip()
                post_url = title_tag.get("href", "")

                if post_url and not post_url.startswith("http"):
                    post_url = f"https://old.reddit.com{post_url}"

                # Score
                score_tag = thing.select_one("div.score.unvoted")
                score = score_tag.text.strip() if score_tag else "0"
                if score == "•":
                    score = "0"

                # Comments count
                comments = "0"
                comment_tag = thing.select_one("a.comments")
                if comment_tag:
                    comment_text = comment_tag.text.strip()
                    parts = comment_text.split()
                    if parts and parts[0].isdigit():
                        comments = parts[0]

                posts.append({
                    "source": "reddit",
                    "subreddit": f"r/{subreddit}",
                    "title": title,
                    "url": post_url,
                    "score": score,
                    "comments": comments,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                })

            except Exception as e:
                logger.debug(f"Error parsing Reddit post: {e}")
                continue

        logger.info(f"Scraped {len(posts)} posts from r/{subreddit}")
        return posts

    except httpx.HTTPError as e:
        logger.warning(f"Reddit r/{subreddit} scrape failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error scraping r/{subreddit}: {e}")
        return []


def scrape_reddit() -> list[dict]:
    """
    Scrape top posts from all configured subreddits.
    Falls back to mock data if all subreddit scrapes fail.

    Returns:
        Combined list of posts from all subreddits.
    """
    all_posts = []

    for subreddit in SUBREDDITS:
        posts = _scrape_subreddit(subreddit)
        all_posts.extend(posts)

    if not all_posts:
        logger.warning("All Reddit scrapers failed. Using mock data.")
        return get_mock_reddit()

    logger.info(f"Total Reddit posts scraped: {len(all_posts)}")
    return all_posts
