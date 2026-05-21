"""
MemoryAgent — Node 4 in the LangGraph workflow.
Prevents duplicate topic usage by maintaining a persistent memory store.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def memory_agent(state: dict) -> dict:
    """Filter out previously written topics to prevent duplication."""
    selected_topics = state.get("selected_topics", [])
    config = state.get("config", {})
    memory_file = config.get("memory_file", "memory/topics.json")

    if not selected_topics:
        logger.warning("MemoryAgent received no selected topics")
        return {"filtered_topics": []}

    logger.info(f"MemoryAgent checking {len(selected_topics)} topics against memory...")

    memory = _load_memory(memory_file)
    past_titles = {entry["title"].lower() for entry in memory.get("topics", [])}

    filtered = []
    for topic in selected_topics:
        title = topic.get("title", "")
        title_lower = title.lower()

        if title_lower in past_titles:
            logger.info(f"  SKIPPED (exact match): {title}")
            continue

        title_words = set(title_lower.split())
        is_duplicate = False
        for past_title in past_titles:
            past_words = set(past_title.split())
            if title_words and past_words:
                overlap = len(title_words & past_words)
                similarity = overlap / max(len(title_words), len(past_words))
                if similarity > 0.6:
                    logger.info(f"  SKIPPED (fuzzy {similarity:.0%}): {title}")
                    is_duplicate = True
                    break

        if not is_duplicate:
            filtered.append(topic)
            logger.info(f"  PASSED: {title}")

    if not filtered and selected_topics:
        logger.warning("All topics were duplicates. Allowing first through.")
        filtered = [selected_topics[0]]

    logger.info(f"MemoryAgent: {len(filtered)}/{len(selected_topics)} topics passed")
    return {"filtered_topics": filtered}


def update_memory(topics: list[dict], memory_file: str) -> None:
    """Add generated topics to memory store after article creation."""
    memory = _load_memory(memory_file)
    for topic in topics:
        original = topic.get("original_data", {})
        entry = {
            "title": topic.get("title", ""),
            "category": topic.get("category", ""),
            "keywords": original.get("keywords", [])[:10],
            "used_at": datetime.now(timezone.utc).isoformat(),
        }
        memory["topics"].append(entry)
    _save_memory(memory, memory_file)
    logger.info(f"Memory updated with {len(topics)} new topics")


def _load_memory(filepath: str) -> dict:
    """Load memory from JSON file."""
    path = Path(filepath)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "topics" in data:
                    return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading memory file: {e}")
    return {"topics": [], "created_at": datetime.now(timezone.utc).isoformat()}


def _save_memory(memory: dict, filepath: str) -> None:
    """Save memory to JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        memory["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logger.error(f"Failed to save memory: {e}")
