#!/usr/bin/env python3
"""
Autonomous Blogger Agent — CLI Entry Point

A multi-agent AI system that scrapes trending data, analyzes topics,
and generates blog posts using LangGraph orchestration and Gemma 4.

Usage:
    python main.py --articles 3 --mode live
    python main.py --articles 1 --mode mock
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Ensure project root is in path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings
from graph.workflow import create_workflow

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Autonomous Blogger Agent — Generate blog posts from trending topics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --articles 3 --mode live
  python main.py --articles 1 --mode mock
  python main.py --articles 2 --mode live --model gemma-4-31b-it
        """,
    )

    parser.add_argument(
        "--articles", "-n",
        type=int,
        default=None,
        help="Number of articles to generate (default: from .env or 3)",
    )

    parser.add_argument(
        "--mode", "-m",
        choices=["live", "mock"],
        default=None,
        help="Scraping mode: 'live' for real scraping, 'mock' for test data",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM model name (default: gemma-4-26b-a4b-it)",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Logging level (default: INFO)",
    )

    return parser.parse_args()


def print_banner() -> None:
    """Print startup banner."""
    banner = """
╔══════════════════════════════════════════════════╗
║         🤖 AUTONOMOUS BLOGGER AGENT 🤖          ║
║                                                  ║
║   LangGraph + Gemma 4 + Real-Time Scraping       ║
╚══════════════════════════════════════════════════╝
    """
    print(banner)


def print_results(result: dict) -> None:
    """Print a summary of the workflow results."""
    stored_files = result.get("stored_files", [])
    articles = result.get("articles", [])

    print("\n" + "=" * 60)
    print("📊 RESULTS SUMMARY")
    print("=" * 60)

    raw_count = len(result.get("raw_data", []))
    topics_count = len(result.get("topics", []))
    selected_count = len(result.get("selected_topics", []))
    filtered_count = len(result.get("filtered_topics", []))

    print(f"  📥 Raw items scraped:     {raw_count}")
    print(f"  📊 Topics identified:     {topics_count}")
    print(f"  🎯 Topics selected:       {selected_count}")
    print(f"  🧠 Topics after dedup:    {filtered_count}")
    print(f"  ✍️  Articles generated:    {len(articles)}")
    print(f"  💾 Files saved:           {len(stored_files)}")

    if stored_files:
        print(f"\n📁 Generated articles:")
        for filepath in stored_files:
            print(f"  → {filepath}")

    if articles:
        print(f"\n📝 Article titles:")
        for article in articles:
            title = article.get("title", "Untitled")
            tags = ", ".join(article.get("tags", []))
            print(f"  • {title}")
            if tags:
                print(f"    Tags: {tags}")

    print("\n" + "=" * 60)


def trigger_indexing(stored_files: list[str]) -> None:
    """Submit successfully generated URLs to the Google Indexing API."""
    if not stored_files:
        return

    import sys
    from pathlib import Path
    
    # Add parent directory to sys.path to import index_urls
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        # Load credentials
        creds_path = parent_dir / "credentials.json"
        if not creds_path.exists():
            logger.warning(f"Google Indexing credentials not found at {creds_path}. Skipping auto-indexing.")
            return
            
        SCOPES = ["https://www.googleapis.com/auth/indexing"]
        credentials = service_account.Credentials.from_service_account_file(
            str(creds_path), scopes=SCOPES
        )
        service = build("indexing", "v3", credentials=credentials)
        logger.info("🔑 Auto-indexing authenticated successfully!")
        
        # Construct site URLs
        # Each filename is like: YYYY-MM-DD-slug.md
        # According to permalink in _config.yml: '/:title/', so url is:
        # SITE_URL/slug/
        site_url = "https://the-rogue-marketing.github.io"
        
        for filepath_str in stored_files:
            filepath = Path(filepath_str)
            filename = filepath.name
            
            # The filename pattern is YYYY-MM-DD-slug.md.
            # Let's extract slug by removing date prefix and .md extension.
            # Example: 2026-05-19-some-topic.md -> some-topic
            parts = filename.replace(".md", "").split("-")
            if len(parts) > 3:
                slug = "-".join(parts[3:])
            else:
                slug = filename.replace(".md", "")
                
            post_url = f"{site_url}/{slug}/"
            
            logger.info(f"Submitting URL for indexing: {post_url}")
            body = {"url": post_url, "type": "URL_UPDATED"}
            try:
                response = service.urlNotifications().publish(body=body).execute()
                print(f"  ✅ {post_url} (Google Indexed!)")
            except Exception as e:
                logger.error(f"  ❌ {post_url} indexing failed: {e}")
                
    except Exception as e:
        logger.error(f"Failed to auto-index new articles: {e}")


def main() -> None:
    """Main entry point for the Blogger Agent."""
    print_banner()

    args = parse_args()

    # Build settings with CLI overrides
    overrides = {}
    if args.articles is not None:
        overrides["num_articles"] = args.articles
    if args.mode is not None:
        overrides["scraping_mode"] = args.mode
    if args.model is not None:
        overrides["model_name"] = args.model
    if args.log_level is not None:
        overrides["log_level"] = args.log_level

    try:
        settings = get_settings(**overrides)
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        sys.exit(1)

    logger.info(f"Mode: {settings.scraping_mode}")
    logger.info(f"Model: {settings.model_name}")
    logger.info(f"Articles: {settings.num_articles}")
    logger.info(f"Output: {settings.articles_dir}")

    # Build the config dict to pass through the graph
    graph_config = {
        "scraping_mode": settings.scraping_mode,
        "num_articles": settings.num_articles,
        "gemini_api_key": settings.gemini_api_key,
        "model_name": settings.model_name,
        "articles_dir": str(settings.articles_dir),
        "raw_data_dir": str(settings.raw_data_dir),
        "memory_file": str(settings.memory_file),
    }

    # Create and run the workflow
    try:
        print("\n🔄 Building LangGraph workflow...")
        workflow = create_workflow()

        print("🚀 Starting agent pipeline...\n")
        start_time = time.time()

        # Invoke the graph
        initial_state = {
            "raw_data": [],
            "topics": [],
            "selected_topics": [],
            "filtered_topics": [],
            "articles": [],
            "stored_files": [],
            "config": graph_config,
        }

        result = workflow.invoke(initial_state)

        elapsed = time.time() - start_time
        print(f"\n⏱️  Pipeline completed in {elapsed:.1f}s")

        print_results(result)

        stored_files = result.get("stored_files", [])
        if stored_files:
            print("\n🚀 Initiating automatic Google Search Console Indexing...")
            trigger_indexing(stored_files)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\n❌ Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
