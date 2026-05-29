"""
ScraperAgent — Node 1 in the LangGraph workflow.
Orchestrates all scraping services to collect real-time trending data.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from services.scraping.github_trending import scrape_github_trending
from services.scraping.hacker_news import scrape_hacker_news
from services.scraping.news_sites import scrape_news_sites
from services.scraping.reddit import scrape_reddit
from utils.mock_data import get_all_mock_data

logger = logging.getLogger(__name__)


def scraper_agent(state: dict) -> dict:
    """
    Scrape real-time trending data from multiple sources.

    Collects data from GitHub Trending, Hacker News, news sites (BBC, Dawn,
    Al Jazeera), and Reddit. Falls back to mock data if in mock mode.

    Args:
        state: Current graph state containing config.

    Returns:
        Updated state with raw_data populated.
    """
    config = state.get("config", {})
    mode = config.get("scraping_mode", "live")
    raw_data_dir = config.get("raw_data_dir", "storage/data/raw")

    logger.info(f"ScraperAgent starting in '{mode}' mode...")

    if mode == "mock":
        logger.info("Using mock data (mock mode enabled)")
        raw_data = get_all_mock_data()
    else:
        raw_data = []

        # Scrape all sources independently
        try:
            github_data = scrape_github_trending()
            raw_data.extend(github_data)
        except Exception as e:
            logger.error(f"GitHub scraping failed completely: {e}")

        try:
            hn_data = scrape_hacker_news()
            raw_data.extend(hn_data)
        except Exception as e:
            logger.error(f"Hacker News scraping failed completely: {e}")



        try:
            reddit_data = scrape_reddit()
            raw_data.extend(reddit_data)
        except Exception as e:
            logger.error(f"Reddit scraping failed completely: {e}")

        if not raw_data:
            logger.warning("All live scrapers failed. Falling back to mock data.")
            raw_data = get_all_mock_data()

    # Save raw data snapshot
    _save_raw_snapshot(raw_data, raw_data_dir)

    logger.info(f"ScraperAgent collected {len(raw_data)} items from {_count_sources(raw_data)} sources")

    return {"raw_data": raw_data}


def _save_raw_snapshot(data: list[dict], output_dir: str) -> None:
    """Save raw scraped data as a timestamped JSON snapshot."""
    try:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        filepath = path / f"raw_{timestamp}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Raw data saved to {filepath}")

    except Exception as e:
        logger.warning(f"Failed to save raw data snapshot: {e}")


def _count_sources(data: list[dict]) -> int:
    """Count unique sources in the data."""
    return len({item.get("source", "unknown") for item in data})
