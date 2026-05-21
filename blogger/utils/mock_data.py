"""
Mock data for all scraping sources.
Used as fallback when live scraping fails or in mock mode.
"""

from datetime import datetime, timezone


def get_mock_github_trending() -> list[dict]:
    """Return mock GitHub trending repositories."""
    return [
        {
            "source": "github_trending",
            "title": "ollama/ollama",
            "description": "Get up and running with Llama 3, Gemma, Mistral, and other large language models.",
            "url": "https://github.com/ollama/ollama",
            "stars": "128,450",
            "language": "Go",
            "stars_today": "1,245",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "github_trending",
            "title": "langchain-ai/langgraph",
            "description": "Build resilient language agents as graphs.",
            "url": "https://github.com/langchain-ai/langgraph",
            "stars": "18,200",
            "language": "Python",
            "stars_today": "342",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "github_trending",
            "title": "anthropics/anthropic-cookbook",
            "description": "A collection of notebooks/recipes showcasing some fun and effective ways of using Claude.",
            "url": "https://github.com/anthropics/anthropic-cookbook",
            "stars": "12,800",
            "language": "Jupyter Notebook",
            "stars_today": "198",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "github_trending",
            "title": "microsoft/autogen",
            "description": "A programming framework for agentic AI.",
            "url": "https://github.com/microsoft/autogen",
            "stars": "45,600",
            "language": "Python",
            "stars_today": "567",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "github_trending",
            "title": "pocketbase/pocketbase",
            "description": "Open Source realtime backend in 1 file.",
            "url": "https://github.com/pocketbase/pocketbase",
            "stars": "52,300",
            "language": "Go",
            "stars_today": "423",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
    ]


def get_mock_hacker_news() -> list[dict]:
    """Return mock Hacker News top stories."""
    return [
        {
            "source": "hacker_news",
            "title": "Show HN: I built an open-source AI code editor",
            "url": "https://news.ycombinator.com/item?id=12345",
            "points": "842",
            "comments": "312",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "hacker_news",
            "title": "The end of Moore's Law and what it means for AI hardware",
            "url": "https://news.ycombinator.com/item?id=12346",
            "points": "567",
            "comments": "234",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "hacker_news",
            "title": "Why Rust is taking over systems programming in 2026",
            "url": "https://news.ycombinator.com/item?id=12347",
            "points": "423",
            "comments": "178",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "hacker_news",
            "title": "Pakistan's tech startup ecosystem grows 300% in 2025",
            "url": "https://news.ycombinator.com/item?id=12348",
            "points": "356",
            "comments": "145",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "hacker_news",
            "title": "Google DeepMind releases Gemma 4 — open weights AI model",
            "url": "https://news.ycombinator.com/item?id=12349",
            "points": "1203",
            "comments": "456",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
    ]


def get_mock_news() -> list[dict]:
    """Return mock news headlines from various sources."""
    return [
        {
            "source": "bbc",
            "title": "AI regulation: Global leaders agree on landmark framework",
            "url": "https://www.bbc.com/news/technology-12345",
            "category": "technology",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "bbc",
            "title": "Climate summit 2026: Key pledges and promises",
            "url": "https://www.bbc.com/news/science-12346",
            "category": "science",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "dawn",
            "title": "Pakistan launches national AI strategy with $500m investment",
            "url": "https://www.dawn.com/news/12345",
            "category": "pakistan",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "dawn",
            "title": "IT exports surge to $5 billion milestone",
            "url": "https://www.dawn.com/news/12346",
            "category": "economy",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "aljazeera",
            "title": "Middle East tech hub: Saudi Arabia's Vision 2030 progress",
            "url": "https://www.aljazeera.com/economy/12345",
            "category": "economy",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "aljazeera",
            "title": "Cybersecurity threats rise as AI tools become more accessible",
            "url": "https://www.aljazeera.com/technology/12346",
            "category": "technology",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
    ]


def get_mock_reddit() -> list[dict]:
    """Return mock Reddit top posts."""
    return [
        {
            "source": "reddit",
            "subreddit": "r/programming",
            "title": "Why every developer should learn about LangGraph in 2026",
            "url": "https://reddit.com/r/programming/comments/abc123",
            "score": "2,345",
            "comments": "456",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "reddit",
            "subreddit": "r/programming",
            "title": "The state of WebAssembly: beyond the browser",
            "url": "https://reddit.com/r/programming/comments/abc124",
            "score": "1,876",
            "comments": "234",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "reddit",
            "subreddit": "r/MachineLearning",
            "title": "[R] New paper: Efficient fine-tuning with 90% less compute",
            "url": "https://reddit.com/r/MachineLearning/comments/abc125",
            "score": "3,456",
            "comments": "567",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "reddit",
            "subreddit": "r/MachineLearning",
            "title": "[D] Is RAG still relevant with 1M+ context windows?",
            "url": "https://reddit.com/r/MachineLearning/comments/abc126",
            "score": "2,123",
            "comments": "345",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "reddit",
            "subreddit": "r/worldnews",
            "title": "EU passes comprehensive AI Act enforcement regulations",
            "url": "https://reddit.com/r/worldnews/comments/abc127",
            "score": "15,678",
            "comments": "2,345",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "source": "reddit",
            "subreddit": "r/worldnews",
            "title": "Global semiconductor production hits record high",
            "url": "https://reddit.com/r/worldnews/comments/abc128",
            "score": "8,901",
            "comments": "1,234",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
    ]


def get_all_mock_data() -> list[dict]:
    """Return combined mock data from all sources."""
    data = []
    data.extend(get_mock_github_trending())
    data.extend(get_mock_hacker_news())
    data.extend(get_mock_news())
    data.extend(get_mock_reddit())
    return data
