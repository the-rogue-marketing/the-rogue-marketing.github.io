# 🤖 Autonomous Blogger Agent

A production-grade multi-agent AI system that scrapes real-time trending data from the web, analyzes topics, and generates high-quality blog posts — all orchestrated using **LangGraph** and powered by **Gemma 4** via the native Google GenAI SDK.

## 🏗️ Architecture

```
START → ScraperAgent → TrendAnalyzerAgent → TopicSelectorAgent
      → MemoryAgent → ContentWriterAgent → StorageAgent → END
```

| Agent | Role |
|-------|------|
| **ScraperAgent** | Scrapes GitHub Trending, Hacker News, BBC, Dawn, Al Jazeera, Reddit |
| **TrendAnalyzerAgent** | Cleans data, clusters topics, scores by frequency/diversity/engagement |
| **TopicSelectorAgent** | Uses Gemma 4 to select diverse, high-value topics |
| **MemoryAgent** | Prevents duplicate topics via persistent JSON memory |
| **ContentWriterAgent** | Generates full blog posts with Gemma 4 (title, summary, body, tags) |
| **StorageAgent** | Saves articles as dated markdown files with front matter |

## 📦 Tech Stack

- **LangGraph** — Multi-agent orchestration
- **Gemma 4** (`gemma-4-26b-a4b-it`) via native `google-genai` SDK
- **httpx + BeautifulSoup** — Real-time web scraping
- **Python 3.10+**

## 🚀 Setup

### 1. Create virtual environment & install dependencies

```bash
cd blogger
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:

```env
GEMINI_API_KEY=your_key_here
```

Get a key at: https://aistudio.google.com/apikey

### 3. Run

```bash
source venv/bin/activate

# Live scraping, 3 articles
python main.py --articles 3 --mode live

# Mock data (no internet needed for scraping), 1 article
python main.py --articles 1 --mode mock

# Use a different model
python main.py --articles 2 --mode live --model gemma-4-31b-it
```

## 📁 Project Structure

```
blogger/
├── main.py                    # CLI entry point
├── config.py                  # Configuration + .env loading
├── requirements.txt           # Dependencies
├── agents/
│   ├── scraper.py             # Web scraping orchestration
│   ├── trend_analyzer.py      # Topic clustering & scoring
│   ├── topic_selector.py      # LLM-powered topic selection
│   ├── content_writer.py      # Blog post generation
│   ├── memory.py              # Duplicate prevention
│   └── storage.py             # Markdown file output
├── graph/
│   └── workflow.py            # LangGraph StateGraph definition
├── services/
│   ├── llm.py                 # Gemma 4 via native google-genai SDK
│   └── scraping/
│       ├── github_trending.py # GitHub Trending scraper
│       ├── hacker_news.py     # Hacker News scraper
│       ├── news_sites.py      # BBC, Dawn, Al Jazeera
│       └── reddit.py          # Reddit scraper
├── templates/
│   └── prompts.py             # LLM prompt templates
├── utils/
│   ├── text.py                # Text processing utilities
│   └── mock_data.py           # Fallback mock data
├── storage/
│   ├── articles/              # Generated blog posts (*.md)
│   └── data/raw/              # Raw scraping snapshots
└── memory/
    └── topics.json            # Persistent topic memory
```

## 📄 Output

Articles are saved to `storage/articles/` as:

```
2026-04-24-ai-regulation-global-leaders-agree.md
```

Each file includes YAML front matter:

```yaml
---
title: "AI Regulation: What the New Global Framework Means for Developers"
date: 2026-04-24
category: ai
tags: ["ai", "regulation", "policy"]
summary: "A deep dive into the landmark AI regulation..."
---
```

## 🧠 Memory

The system remembers previously written topics in `memory/topics.json` and avoids repeating them on subsequent runs.

## ⚙️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | (required) | Google AI Studio / Gemini API key |
| `MODEL_NAME` | `gemma-4-26b-a4b-it` | Gemma 4 model to use |
| `SCRAPING_MODE` | `live` | `live` or `mock` |
| `NUM_ARTICLES` | `3` | Number of articles to generate |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
