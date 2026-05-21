"""
ContentWriterAgent — Node 5 in the LangGraph workflow.
Uses Gemma 4 (via native Google GenAI SDK) to generate full blog posts.
"""

import json
import logging

from services.llm import get_client, invoke_llm
from templates.prompts import CONTENT_WRITER_SYSTEM, CONTENT_WRITER_USER

logger = logging.getLogger(__name__)


def content_writer_agent(state: dict) -> dict:
    """
    Generate blog posts for each filtered topic using Gemma 4.

    Args:
        state: Current graph state with filtered_topics and config.

    Returns:
        Updated state with articles list.
    """
    filtered_topics = state.get("filtered_topics", [])
    config = state.get("config", {})

    if not filtered_topics:
        logger.warning("ContentWriterAgent received no topics")
        return {"articles": []}

    logger.info(f"ContentWriterAgent generating {len(filtered_topics)} articles...")

    client = get_client(api_key=config.get("gemini_api_key", ""))
    model = config.get("model_name", "gemma-4-26b-a4b-it")

    articles = []
    for i, topic in enumerate(filtered_topics, 1):
        logger.info(f"  Writing article {i}/{len(filtered_topics)}: {topic['title']}")

        try:
            article = _generate_article(client, model, topic)
            if article:
                articles.append(article)
                logger.info(f"  ✓ Generated: {article['title']}")
            else:
                logger.warning(f"  ✗ Failed to generate article for: {topic['title']}")
        except Exception as e:
            logger.error(f"  ✗ Error generating article: {e}")

    logger.info(f"ContentWriterAgent generated {len(articles)} articles")
    return {"articles": articles}


def _generate_article(client, model: str, topic: dict) -> dict | None:
    """Generate a single blog post article."""
    original = topic.get("original_data", {})

    # Build context from original trending data
    context_parts = []
    if original.get("description"):
        context_parts.append(f"Description: {original['description']}")
    if original.get("sources"):
        context_parts.append(f"Trending on: {', '.join(original['sources'])}")
    if original.get("keywords"):
        context_parts.append(f"Keywords: {', '.join(original['keywords'][:8])}")
    if original.get("items"):
        titles = [item.get("title", "") for item in original["items"][:5]]
        context_parts.append(f"Related items: {'; '.join(titles)}")

    context = "\n".join(context_parts) if context_parts else topic.get("title", "")

    user_prompt = CONTENT_WRITER_USER.format(
        topic_title=topic.get("title", ""),
        blog_angle=topic.get("blog_angle", "General analysis"),
        category=topic.get("category", "tech"),
        context=context,
    )

    response_text = invoke_llm(
        client=client,
        model=model,
        system_prompt=CONTENT_WRITER_SYSTEM,
        user_prompt=user_prompt,
        temperature=0.7,
    )

    return _parse_article_response(response_text, topic)


def _parse_article_response(response_text: str, topic: dict) -> dict | None:
    """Parse the JSON article from LLM response."""
    text = response_text.strip()

    if "```json" in text:
        text = text.split("```json")[1].rsplit("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```")[1].rsplit("```", 1)[0].strip()

    try:
        article = json.loads(text)
        if isinstance(article, dict) and "title" in article and "body" in article:
            article["source_topic"] = topic.get("title", "")
            article["category"] = topic.get("category", "general")
            return article
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                article = json.loads(text[start:end])
                if isinstance(article, dict) and "body" in article:
                    article.setdefault("title", topic.get("title", "Untitled"))
                    article.setdefault("summary", "")
                    article.setdefault("tags", [])
                    article["source_topic"] = topic.get("title", "")
                    article["category"] = topic.get("category", "general")
                    return article
            except json.JSONDecodeError:
                pass

    # Last resort: use raw text as article body
    logger.warning("Could not parse article JSON. Using raw response as body.")
    return {
        "title": topic.get("title", "Untitled"),
        "summary": topic.get("blog_angle", ""),
        "body": response_text,
        "tags": [topic.get("category", "general")],
        "source_topic": topic.get("title", ""),
        "category": topic.get("category", "general"),
    }
