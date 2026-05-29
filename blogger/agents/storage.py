"""
StorageAgent — Node 6 in the LangGraph workflow.
Saves generated articles as markdown files and updates memory.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from agents.memory import update_memory
from utils.text import slugify

logger = logging.getLogger(__name__)


def storage_agent(state: dict) -> dict:
    """
    Save articles as markdown files and update topic memory.

    File naming: YYYY-MM-DD-slug.md
    Includes YAML-style front matter with metadata.

    Args:
        state: Current graph state with articles, filtered_topics, config.

    Returns:
        Updated state with stored_files list.
    """
    articles = state.get("articles", [])
    filtered_topics = state.get("filtered_topics", [])
    config = state.get("config", {})
    articles_dir = config.get("articles_dir", "storage/articles")
    memory_file = config.get("memory_file", "memory/topics.json")

    if not articles:
        logger.warning("StorageAgent received no articles to save")
        return {"stored_files": []}

    logger.info(f"StorageAgent saving {len(articles)} articles...")

    output_dir = Path(articles_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stored_files = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for i, article in enumerate(articles):
        try:
            title = article.get("title", f"Untitled-{i}")
            slug = slugify(title)
            filename = f"{today}-{slug}.md"
            filepath = output_dir / filename

            # Handle duplicate filenames
            counter = 1
            while filepath.exists():
                filename = f"{today}-{slug}-{counter}.md"
                filepath = output_dir / filename
                counter += 1

            # Build markdown content with front matter
            content = _build_markdown(article, today)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            stored_files.append(str(filepath))
            logger.info(f"  ✓ Saved: {filename}")

        except Exception as e:
            logger.error(f"  ✗ Failed to save article '{article.get('title')}': {e}")

    # Update memory with successfully written topics
    if stored_files and filtered_topics:
        try:
            update_memory(filtered_topics, memory_file)
        except Exception as e:
            logger.error(f"Failed to update memory: {e}")

    logger.info(f"StorageAgent saved {len(stored_files)} files")
    return {"stored_files": stored_files}


def _build_markdown(article: dict, date: str) -> str:
    """Build a complete markdown file with Jekyll front matter."""
    title = article.get("title", "Untitled")
    description = article.get("description", article.get("summary", ""))
    body = article.get("body", "")
    tags = article.get("tags", [])
    category = article.get("category", "general")
    keywords = article.get("keywords", ", ".join(tags))
    image = article.get("image", "assets/images/gemini-ocr-pydantic-ai.webp")

    # Map category and tags to Jekyll categories
    categories = list(dict.fromkeys([category] + tags))
    categories_str = ", ".join(categories)

    front_matter = f"""---
layout: post
title: "{title}"
description: "{description}"
author: professor-xai
categories: [{categories_str}]
image: {image}
featured: false
last_modified_at: {date}
keywords: "{keywords}"
---

"""

    # Full markdown document
    content = front_matter
    content += body
    content += "\n"

    return content
