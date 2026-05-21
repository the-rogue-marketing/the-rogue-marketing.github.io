"""
TopicSelectorAgent — Node 3 in the LangGraph workflow.
Uses Gemma 4 (via native Google GenAI SDK) to intelligently select topics.
"""

import json
import logging

from services.llm import get_client, invoke_llm
from templates.prompts import TOPIC_SELECTOR_SYSTEM, TOPIC_SELECTOR_USER

logger = logging.getLogger(__name__)


def topic_selector_agent(state: dict) -> dict:
    """
    Select top N topics for blog post generation using Gemma 4.

    Args:
        state: Current graph state with topics and config.

    Returns:
        Updated state with selected_topics list.
    """
    topics = state.get("topics", [])
    config = state.get("config", {})
    num_articles = config.get("num_articles", 3)

    if not topics:
        logger.warning("TopicSelectorAgent received no topics")
        return {"selected_topics": []}

    logger.info(f"TopicSelectorAgent selecting top {num_articles} from {len(topics)} topics...")

    # Prepare topic data for LLM (top 15 by score)
    top_topics = topics[:15]
    topics_for_llm = []

    for t in top_topics:
        topics_for_llm.append({
            "title": t["title"],
            "description": t.get("description", ""),
            "keywords": t.get("keywords", [])[:8],
            "sources": t.get("sources", []),
            "score": t.get("score", 0),
            "item_count": t.get("item_count", 1),
        })

    topics_json = json.dumps(topics_for_llm, indent=2)

    user_prompt = TOPIC_SELECTOR_USER.format(
        topics_json=topics_json,
        num_topics=num_articles,
    )

    try:
        client = get_client(api_key=config.get("gemini_api_key", ""))
        model = config.get("model_name", "gemma-4-26b-a4b-it")

        response_text = invoke_llm(
            client=client,
            model=model,
            system_prompt=TOPIC_SELECTOR_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.4,
        )

        selected = _parse_llm_response(response_text)

        if not selected:
            logger.warning("LLM returned no valid selections. Using fallback.")
            selected = _fallback_selection(topics, num_articles)

        enriched = _enrich_selections(selected, topics)

        logger.info(f"TopicSelectorAgent selected {len(enriched)} topics:")
        for i, topic in enumerate(enriched, 1):
            logger.info(f"  #{i}: {topic['title']} [{topic.get('category', 'general')}]")

        return {"selected_topics": enriched}

    except Exception as e:
        logger.error(f"LLM-based selection failed: {e}. Using fallback selection.")
        selected = _fallback_selection(topics, num_articles)
        return {"selected_topics": selected}


def _parse_llm_response(response_text: str) -> list[dict]:
    """Parse the JSON array from the LLM response."""
    text = response_text.strip()

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        return []
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

        logger.warning(f"Failed to parse LLM response as JSON: {text[:200]}")
        return []


def _fallback_selection(topics: list[dict], num: int) -> list[dict]:
    """Fallback: select top N topics by score with category diversity."""
    selected = []
    seen_categories: set[str] = set()

    for topic in topics:
        if len(selected) >= num:
            break

        keywords_str = " ".join(topic.get("keywords", []))
        category = _detect_category(keywords_str)

        if category in seen_categories and len(selected) < num - 1:
            continue

        seen_categories.add(category)
        selected.append({
            "title": topic["title"],
            "blog_angle": f"Analysis and insights on: {topic['title']}",
            "category": category,
            "justification": f"High trending score ({topic.get('score', 0)}) across {len(topic.get('sources', []))} sources",
            "original_data": topic,
        })

    if len(selected) < num:
        for topic in topics:
            if len(selected) >= num:
                break
            if topic["title"] not in {s["title"] for s in selected}:
                selected.append({
                    "title": topic["title"],
                    "blog_angle": f"Deep dive into: {topic['title']}",
                    "category": _detect_category(" ".join(topic.get("keywords", []))),
                    "justification": "Selected to fill remaining slots",
                    "original_data": topic,
                })

    return selected


def _enrich_selections(selected: list[dict], all_topics: list[dict]) -> list[dict]:
    """Enrich LLM selections with data from the original topics."""
    enriched = []

    for sel in selected:
        original = None
        sel_title_lower = sel.get("title", "").lower()

        for topic in all_topics:
            if topic["title"].lower() == sel_title_lower:
                original = topic
                break

        if not original:
            for topic in all_topics:
                sel_words = set(sel_title_lower.split())
                topic_words = set(topic["title"].lower().split())
                if len(sel_words & topic_words) >= 3:
                    original = topic
                    break

        enriched.append({
            "title": sel.get("title", ""),
            "blog_angle": sel.get("blog_angle", ""),
            "category": sel.get("category", "general"),
            "justification": sel.get("justification", ""),
            "original_data": original or {},
        })

    return enriched


def _detect_category(text: str) -> str:
    """Simple keyword-based category detection."""
    text = text.lower()

    if any(w in text for w in ["ai", "llm", "model", "neural", "machine", "learning", "gpt", "gemma"]):
        return "ai"
    if any(w in text for w in ["pakistan", "dawn", "karachi", "islamabad", "lahore"]):
        return "pakistan"
    if any(w in text for w in ["python", "rust", "javascript", "code", "developer", "programming", "github"]):
        return "dev"
    if any(w in text for w in ["climate", "space", "physics", "research", "quantum"]):
        return "science"
    if any(w in text for w in ["startup", "investment", "economy", "billion", "market"]):
        return "business"

    return "tech"
