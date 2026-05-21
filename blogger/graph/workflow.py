"""
LangGraph workflow definition for the Blogger Agent.
Defines the multi-agent state graph with 6 nodes.

Flow:
  START → ScraperAgent → TrendAnalyzerAgent → TopicSelectorAgent
        → MemoryAgent → ContentWriterAgent → StorageAgent → END
"""

import logging
import operator
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, END

from agents.scraper import scraper_agent
from agents.trend_analyzer import trend_analyzer_agent
from agents.topic_selector import topic_selector_agent
from agents.memory import memory_agent
from agents.content_writer import content_writer_agent
from agents.storage import storage_agent

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# STATE DEFINITION
# ─────────────────────────────────────────────

class BloggerState(TypedDict, total=False):
    """
    Shared state object that flows through the LangGraph workflow.

    Each agent reads from and writes to specific fields.
    """
    # ScraperAgent → TrendAnalyzerAgent
    raw_data: list[dict]

    # TrendAnalyzerAgent → TopicSelectorAgent
    topics: list[dict]

    # TopicSelectorAgent → MemoryAgent
    selected_topics: list[dict]

    # MemoryAgent → ContentWriterAgent
    filtered_topics: list[dict]

    # ContentWriterAgent → StorageAgent
    articles: list[dict]

    # StorageAgent output
    stored_files: list[str]

    # Runtime configuration (passed through all nodes)
    config: dict


# ─────────────────────────────────────────────
# WORKFLOW FACTORY
# ─────────────────────────────────────────────

def create_workflow():
    """
    Create and compile the LangGraph workflow.

    Returns:
        Compiled StateGraph ready for invocation.
    """
    logger.info("Building LangGraph workflow...")

    # Initialize the state graph
    workflow = StateGraph(BloggerState)

    # ─── Add Nodes ───
    workflow.add_node("scraper", scraper_agent)
    workflow.add_node("trend_analyzer", trend_analyzer_agent)
    workflow.add_node("topic_selector", topic_selector_agent)
    workflow.add_node("memory", memory_agent)
    workflow.add_node("content_writer", content_writer_agent)
    workflow.add_node("storage", storage_agent)

    # ─── Define Edges (linear flow) ───
    workflow.set_entry_point("scraper")

    workflow.add_edge("scraper", "trend_analyzer")
    workflow.add_edge("trend_analyzer", "topic_selector")
    workflow.add_edge("topic_selector", "memory")
    workflow.add_edge("memory", "content_writer")
    workflow.add_edge("content_writer", "storage")
    workflow.add_edge("storage", END)

    # ─── Compile ───
    app = workflow.compile()

    logger.info("LangGraph workflow compiled successfully")
    logger.info("  Flow: scraper → trend_analyzer → topic_selector → memory → content_writer → storage → END")

    return app
