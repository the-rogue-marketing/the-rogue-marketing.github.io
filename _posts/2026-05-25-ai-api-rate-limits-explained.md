---
layout: post
title: "AI API Rate Limits Explained: Why Your App Keeps Failing [And the Fix]"
description: "Is your AI app throwing 429 Too Many Requests errors? I explained standard rate limit rules for OpenAI, Gemini, and Claude, and how to implement retry queues."
author: professor-xai
categories: [ai-api, error-handling, engineering, developers]
image: assets/images/ai-api-rate-limit-fixes.png
featured: false
last_modified_at: 2026-05-25
keywords: "api rate limits openai gemini, ai api throttling fix, 429 error code llm, exponential backoff python, rate limit headers, handle rate limits"
faq:
  - question: "What does HTTP 429 Too Many Requests mean in AI APIs?"
    answer: "HTTP 429 indicates that your application has exceeded the provider's Rate Limits. These are measured in Requests Per Minute (RPM), Tokens Per Minute (TPM), or Requests Per Day (RPD)."
  - question: "How do I fix rate limit errors in Python?"
    answer: "You should implement exponential backoff with jitter in your api call loops, use token bucket queues to throttle outbound requests, or implement fallback model routing."
  - question: "Which provider offers the highest rate limits?"
    answer: "Google Gemini offers some of the highest default developer rate limits (up to 4,000 requests per minute on pay-as-you-go tiers). OpenAI and Claude scale rate limits based on usage tiers."
  - question: "What are rate limit headers?"
    answer: "AI providers send rate limit metadata headers in HTTP responses (e.g. x-ratelimit-remaining-tokens). You can read these headers to throttle requests dynamically."
---

If you've ever scaled an AI-powered application past a few hundred daily users, you've likely run into the dreaded **HTTP 429: Too Many Requests** error.

Unlike traditional database APIs where rate limits are simple (e.g., 60 requests per minute), AI APIs use a two-dimensional limit schema: **Requests Per Minute (RPM)** and **Tokens Per Minute (TPM)**.

Even if you only send 5 requests, a large document context can trigger a TPM rate limit error and crash your app.

This guide explains how rate limits are calculated across OpenAI, Gemini, and Claude, and shows you how to write bulletproof error handling code to keep your app online.

> 🧮 **Calculate your token throughput:** Use our [AI API Pricing Calculator](/ai-api-pricing-calculator/) to project your expected token limits per minute based on user counts.

---

## Understanding the 3 Types of Limits

AI providers throttle your app based on three distinct metrics:

1.  **Requests Per Minute (RPM):** How many times your code calls their endpoint in 60 seconds.
2.  **Tokens Per Minute (TPM):** The sum of all input and output tokens processed in 60 seconds.
3.  **Requests Per Day (RPD):** Daily cap (primarily enforced on free developer tiers).

---

## Rate Limit Comparison (Tier 1 / Pay-As-You-Go)

Here are the typical starting limits for new developer accounts:

| Provider | Model | Default RPM | Default TPM |
| :--- | :--- | :--- | :--- |
| **OpenAI** | GPT-4o-mini | 500 RPM | 200,000 TPM |
| **OpenAI** | GPT-4o | 500 RPM | 30,000 TPM |
| **Google** | Gemini 2.5 Flash | **2,000 RPM** | **4,000,000 TPM** |
| **Anthropic** | Claude Sonnet | 50 RPM | 40,000 TPM |

> **The Winner:** **Google Gemini** provides exceptionally high default limits, making it the most resilient provider for high-velocity startup traffic.

---

## How to Fix Rate Limit Errors (Python)

### 1. Implement Exponential Backoff with Jitter

Do not immediately retry a failed request. Instead, wait, increasing the delay with each failure. Adding random "jitter" prevents all your concurrent requests from retrying at the exact same millisecond.

Here is the production-ready Python decorator using the `tenacity` library:

```python
import random
import time
from google import genai
from google.genai.errors import APIError
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type

client = genai.Client()

# Retry up to 5 times with exponential backoff between 1 and 60 seconds
@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(APIError)
)
def call_gemini_safely(prompt: str):
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    return response.text
```

### 2. Read Rate Limit Headers Dynamically

Every time you make an API call, the provider returns headers indicating how close you are to your limits. You can parse these values to slow down your code proactively:

*   `x-ratelimit-remaining-requests`
*   `x-ratelimit-remaining-tokens`
*   `x-ratelimit-reset-requests` (Time until RPM resets)
*   `x-ratelimit-reset-tokens` (Time until TPM resets)

### 3. Implement Fallback Routing (Multi-Model Resiliency)

If your primary model provider is fully throttled, route the query to a fallback model. 

```python
def generate_text_with_fallback(prompt: str):
    try:
        # 1. Try OpenAI
        return call_openai(prompt)
    except Exception as e:
        if "429" in str(e):
            print("⚠️ OpenAI Throttled! Falling back to Gemini...")
            # 2. Route to Gemini
            return call_gemini_safely(prompt)
```

---

## Related Guides

*   📘 [Google Gemini API Pricing Guide](/google-gemini-api-pricing-may-2026/)
*   📗 [OpenAI API Pricing Guide](/openai-api-pricing-may-2026/)
*   📊 [AI Model Comparison 2026](/ai-model-pricing-comparison-gemini-openai-grok-claude-2026/)
*   🧮 [AI API Pricing Calculator](/ai-api-pricing-calculator/)
