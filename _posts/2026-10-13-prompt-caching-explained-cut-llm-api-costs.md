---
layout: post
title: "Prompt Caching Explained: How to Cut LLM API Costs and Latency Across OpenAI, Anthropic and Gemini"
description: "A practical guide to how prompt caching works at each major provider, how to structure prompts so the cache actually hits, and when caching pays off."
date: 2026-10-13 09:00:00 +0000
author: muhammad-usama
image: assets/images/prompt-caching-llm-cost-2026.webp
categories:
  - AI Models & API Pricing
tags:
  - AI APIs
  - API Pricing
  - Gemini
  - OpenAI
  - Python
keywords: "prompt caching explained, llm api cost reduction, openai prompt caching, anthropic cache_control, gemini context caching, reduce llm latency"
faqs:
  - question: "What is prompt caching?"
    answer: "Prompt caching lets a provider reuse the processed form of a repeated prompt prefix, so you pay a discounted rate and get faster responses for the part of the prompt that does not change."
  - question: "Why is my prompt cache not hitting?"
    answer: "Caches match on an exact prefix. Any change near the start of the prompt, such as a timestamp or user name in the system prompt, invalidates everything after it."
  - question: "Is prompt caching worth it for short prompts?"
    answer: "Usually not. Providers apply minimum token thresholds, and the savings matter most for long, repeated system prompts, documents or tool definitions."
---

Most production LLM applications send the same large block of text again and again: a long system prompt, tool definitions, a policy document, or a codebase snapshot. Without caching, you pay full price to process that identical prefix on every single request.

**Prompt caching** fixes this. The provider stores the processed prefix and reuses it on later requests, which lowers the cost of those cached input tokens and cuts time-to-first-token.

---

## 1. How Each Provider Implements Caching

| Provider | How it is enabled | What you control |
| :--- | :--- | :--- |
| **OpenAI** | Automatic for prompts above a minimum length | Prompt structure only; cached tokens are reported in usage |
| **Anthropic** | Explicit `cache_control` breakpoints on message blocks | Which blocks are cached and the cache lifetime |
| **Google Gemini** | Implicit caching on supported models, plus explicit context caches via the API | Cache objects with a time-to-live for large shared context |

Discount levels and minimum token thresholds change over time, so check each provider's current pricing page before building cost models.

---

## 2. Structure Prompts for Cache Hits

Caches match on an **exact prefix**. Put everything static first and everything dynamic last:

```
[ static system prompt ]      <- cached
[ tool / function schemas ]   <- cached
[ reference documents ]       <- cached
[ conversation history ]      <- partly cached as it grows
[ latest user message ]       <- never cached
```

The most common mistake is injecting the current date, a request ID or the user's name into the first line of the system prompt. That single change breaks the cache for every token that follows.

---

## 3. Explicit Caching with Anthropic

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": LONG_POLICY_DOCUMENT,
            "cache_control": {"type": "ephemeral"},
        }
    ],
    messages=[{"role": "user", "content": user_question}],
)

print(response.usage)  # shows cache creation vs cache read tokens
```

The first call writes the cache; later calls within the cache lifetime read from it.

---

## 4. Measure, Do Not Assume

Every provider returns cache statistics in the usage object. Log them per request and track:

- **Cache hit ratio**: cached input tokens divided by total input tokens
- **Effective input cost**: blended price after cache discounts
- **Time-to-first-token**: before and after enabling caching

If your hit ratio is low, look for dynamic content leaking into the prefix. In well-structured agent and RAG pipelines, most input tokens can come from cache, which is where the large savings appear.
