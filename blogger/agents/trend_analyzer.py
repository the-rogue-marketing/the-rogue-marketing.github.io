"""
TrendAnalyzerAgent — Node 2 in the LangGraph workflow.
Cleans, clusters, and scores trending topics from raw scraped data.
"""

import logging
from collections import Counter
from datetime import datetime, timezone

from utils.text import clean_text, extract_keywords

logger = logging.getLogger(__name__)


def trend_analyzer_agent(state: dict) -> dict:
    """
    Analyze raw scraped data to identify and score trending topics.

    Process:
    1. Clean and normalize all items
    2. Extract keywords from titles and descriptions
    3. Cluster related items by keyword overlap
    4. Score clusters by frequency, source diversity, and engagement

    Args:
        state: Current graph state with raw_data.

    Returns:
        Updated state with scored topics list.
    """
    raw_data = state.get("raw_data", [])

    if not raw_data:
        logger.warning("TrendAnalyzerAgent received no raw data")
        return {"topics": []}

    logger.info(f"TrendAnalyzerAgent processing {len(raw_data)} items...")

    # Step 1: Clean and enrich items
    cleaned_items = _clean_items(raw_data)

    # Step 2: Extract keywords and build clusters
    clusters = _cluster_topics(cleaned_items)

    # Step 3: Score and rank clusters
    scored_topics = _score_clusters(clusters)

    # Step 4: Sort by score descending
    scored_topics.sort(key=lambda t: t["score"], reverse=True)

    logger.info(f"TrendAnalyzerAgent identified {len(scored_topics)} topic clusters")

    # Log top 5
    for i, topic in enumerate(scored_topics[:5], 1):
        logger.info(f"  #{i}: {topic['title']} (score: {topic['score']:.2f})")

    return {"topics": scored_topics}


def _clean_items(items: list[dict]) -> list[dict]:
    """Clean and normalize raw data items."""
    cleaned = []

    for item in items:
        title = clean_text(item.get("title", ""))
        description = clean_text(item.get("description", ""))

        if not title:
            continue

        # Combine title and description for keyword extraction
        full_text = f"{title} {description}".strip()
        keywords = extract_keywords(full_text)

        cleaned.append({
            "title": title,
            "description": description,
            "source": item.get("source", "unknown"),
            "url": item.get("url", ""),
            "keywords": keywords,
            "metadata": {
                k: v for k, v in item.items()
                if k not in ("title", "description", "source", "url")
            },
        })

    return cleaned


def _cluster_topics(items: list[dict]) -> list[dict]:
    """
    Cluster related items by keyword overlap.
    Items sharing 2+ keywords are grouped together.
    """
    clusters: list[dict] = []
    used_indices: set[int] = set()

    for i, item in enumerate(items):
        if i in used_indices:
            continue

        # Start a new cluster with this item
        cluster_items = [item]
        cluster_keywords = set(item["keywords"][:10])
        used_indices.add(i)

        # Find related items
        for j, other in enumerate(items):
            if j in used_indices:
                continue

            other_keywords = set(other["keywords"][:10])
            overlap = cluster_keywords & other_keywords

            # Require at least 2 keyword overlap to cluster
            if len(overlap) >= 2:
                cluster_items.append(other)
                cluster_keywords.update(other_keywords)
                used_indices.add(j)

        # Create cluster entry
        # Use the item with longest title as representative
        representative = max(cluster_items, key=lambda x: len(x["title"]))

        clusters.append({
            "title": representative["title"],
            "description": representative.get("description", ""),
            "items": cluster_items,
            "keywords": list(cluster_keywords)[:15],
            "sources": list({item["source"] for item in cluster_items}),
            "item_count": len(cluster_items),
        })

    return clusters


def _score_clusters(clusters: list[dict]) -> list[dict]:
    """
    Score topic clusters based on:
    - frequency: number of items in the cluster
    - source_diversity: number of unique sources
    - engagement: numerical signals (points, score, stars)
    """
    scored = []

    for cluster in clusters:
        # Frequency score (more items = more trending)
        freq_score = min(cluster["item_count"] / 3.0, 3.0)

        # Source diversity score (appearing across multiple sources is strong signal)
        diversity_score = len(cluster["sources"]) * 1.5

        # Engagement score (from metadata like points, stars, score)
        engagement = 0.0
        for item in cluster["items"]:
            meta = item.get("metadata", {})
            for key in ("points", "score", "stars", "stars_today"):
                value = meta.get(key, "0")
                if isinstance(value, str):
                    value = value.replace(",", "").strip()
                    try:
                        engagement += float(value) / 1000.0  # Normalize
                    except (ValueError, TypeError):
                        pass

        engagement_score = min(engagement, 5.0)  # Cap at 5

        # Total score
        total_score = freq_score + diversity_score + engagement_score

        scored.append({
            "title": cluster["title"],
            "description": cluster.get("description", ""),
            "keywords": cluster["keywords"],
            "sources": cluster["sources"],
            "item_count": cluster["item_count"],
            "items": cluster["items"],
            "score": round(total_score, 2),
            "score_breakdown": {
                "frequency": round(freq_score, 2),
                "diversity": round(diversity_score, 2),
                "engagement": round(engagement_score, 2),
            },
        })

    return scored
