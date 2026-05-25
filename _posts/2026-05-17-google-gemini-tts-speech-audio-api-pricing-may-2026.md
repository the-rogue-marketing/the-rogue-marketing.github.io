---
layout: post
title: "Google Gemini TTS & Speech AI Pricing 2026: The Complete Guide [Audio Token Calculator]"
description: "Complete pricing guide for Google's speech and audio APIs as of May 2026. Gemini 3.1 Flash TTS, 2.5 Flash/Pro TTS, Live API, and Google Cloud STT Chirp."
author: professor-xai
categories: [gemini, ai-api, google-ai, pricing, text-to-speech, speech-ai]
image: assets/images/gemini-tts-speech-pricing-may-2026.png
featured: false
last_modified_at: 2026-05-25
keywords: "gemini tts pricing, gemini text to speech cost, google ai speech api, gemini 3.1 flash tts, gemini live api pricing, google stt pricing, chirp speech to text, audio api pricing"
faq:
  - question: "How much does Gemini's Text-to-Speech (TTS) cost?"
    answer: "Gemini 2.5 Flash TTS costs $0.15/1M input text tokens and $6.00/1M output audio tokens (approx. $0.09 per 10 minutes of audio). Gemini 3.1 Flash TTS costs $1.00/1M input and $20.00/1M output tokens (approx. $0.31 per 10 minutes)."
  - question: "How many tokens are used per second of audio output?"
    answer: "For Gemini TTS and Live API models, audio output corresponds to a rate of 25 tokens per second. This means 1 million output tokens yields approximately 11 hours of audio."
  - question: "What is the cheapest way to generate text-to-speech using Google APIs?"
    answer: "Gemini 2.5 Flash TTS is the cheapest option at $6.00 per million output audio tokens. Additionally, the Batch API offers a 50% discount, bringing the cost down to $3.00/1M."
  - question: "How much does the Gemini Live API cost?"
    answer: "The real-time bidirectional Gemini Live API costs $1.00/1M input tokens (both text and audio) and $20.00/1M output tokens for audio outputs ($6.00/1M for text outputs)."
  - question: "How does Gemini Audio transcription compare to Google Cloud Speech-to-Text?"
    answer: "Traditional Google Cloud STT (Chirp) costs $0.016 per minute. Gemini Audio Understanding is billed at standard Flash rates ($0.50/$3.00 per 1M tokens), which can be much cheaper for short summaries or Q&A."
---

Google now offers speech AI through **multiple different services**, each with its own pricing model. Whether you're building a voice assistant, transcribing podcasts, or generating audiobook narrations, this guide maps every option and its exact cost.

> 🧮 **Calculate your exact audio & speech costs:** Use our [AI API Pricing Calculator](/ai-api-pricing-calculator/) to estimate token usage and monthly fees for text, image, audio, and video across all major models.

---

## The Google Speech AI Landscape

Google's speech capabilities are split across three distinct services:

| Service | What It Does | Pricing Model |
| :--- | :--- | :--- |
| **Gemini TTS** | Text → Natural speech | Per token |
| **Gemini Live API** | Real-time bidirectional voice | Per token (audio) |
| **Google Cloud STT** | Audio → Text transcription | Per minute |
| **Gemini Audio Understanding** | Audio → Analysis/summary | Per token |

---

## Gemini TTS Models — Text-to-Speech

### Gemini 3.1 Flash TTS (Preview)

The latest and most capable TTS model. Supports 70+ languages, multi-speaker synthesis, and granular control via natural language audio tags.

**Model ID:** `gemini-3.1-flash-tts-preview`

| Cost Type | Price per 1M Tokens | Batch API (50% Off) |
| :--- | :--- | :--- |
| **Input (text)** | **$1.00** | $0.50 |
| **Output (audio)** | **$20.00** | $10.00 |

> **Token-to-seconds conversion:** Audio output tokens correspond to **25 tokens per second**. This means 1 million output tokens = ~11 hours of audio.

#### Real-World Cost Example
Generate a 10-minute podcast narration (~6,000 words input, 600 seconds of audio):

| Cost Component | Calculation | Amount |
| :--- | :--- | :--- |
| Input tokens (~8,000) | 8K × $1.00/1M | **$0.008** |
| Output tokens (600s × 25) | 15,000 × $20.00/1M | **$0.300** |
| **Total Cost** | | **~$0.31** |

---

### Gemini 2.5 Flash TTS (Preview)

A more cost-efficient option, optimized for lower latency and high-volume speech generation.

**Model ID:** `gemini-2.5-flash-preview-tts`

| Cost Type | Price per 1M Tokens | Batch API (50% Off) |
| :--- | :--- | :--- |
| **Input (text)** | **$0.15** | $0.075 |
| **Output (audio)** | **$6.00** | $3.000 |

> **Best for:** High-volume text-to-speech. At $6/M output tokens, a 10-minute narration costs only **~$0.09** — 3× cheaper than 3.1 Flash TTS.

---

### Gemini 2.5 Pro TTS (Preview)

The premium text-to-speech option — offers highly natural outputs, better intonation, and easier-to-steer prompts.

**Model ID:** `gemini-2.5-pro-preview-tts`

| Cost Type | Price per 1M Tokens | Batch API (50% Off) |
| :--- | :--- | :--- |
| **Input (text)** | **$1.25** | $0.625 |
| **Output (audio)** | **$20.00** | $10.000 |

---

## Gemini Live API — Real-Time Bidirectional Voice

For real-time, bidirectional audio conversations (voice assistants, customer service bots).

**Model ID:** `gemini-3.1-flash-live-preview`

| Cost Type | Price per 1M Tokens |
| :--- | :--- |
| **Text Input** | **$1.00** |
| **Audio Input** | **$1.00** |
| **Text Output** | **$6.00** |
| **Audio Output** | **$20.00** |

*   **Audio tokens:** 25 tokens per second of audio (both input and output)
*   **Real-time streaming:** Low-latency, designed for conversational agents
*   **Multimodal:** Supports audio + video input for "see and speak" applications

---

## Google Cloud Speech-to-Text (Chirp) — Traditional STT

For dedicated, high-accuracy transcription of recorded audio files.

| Model | Price per Minute | Free Tier |
| :--- | :--- | :--- |
| **Chirp (Standard)** | **$0.016** | 60 min/month |
| **Chirp (High Volume 500K+ min)** | **$0.012** | — |
| **Chirp (High Volume 2M+ min)** | **$0.004** | — |

---

## Full Cost Comparison: All Speech Services

**Scenario:** Process 1 hour of audio content

| Task / Workload | Best Service | Estimated Cost |
| :--- | :--- | :--- |
| **Transcribe audio → text** | Google Cloud STT (Chirp) | **$0.96** |
| **Summarize meeting audio** | Gemini 3 Flash (audio input) | **~$1.50** |
| **Generate 1-hour audiobook** | Gemini 2.5 Flash TTS | **~$5.40** |
| **Generate 1-hour audiobook** | Gemini 3.1 Flash TTS | **~$18.00** |
| **Real-time voice agent (1 hour)** | Gemini Live API | **~$73.80** |

---

## Key Takeaways

1. **Gemini 2.5 Flash TTS** is the cheapest speech synthesis option at **$0.09 per 10 minutes**.
2. **Gemini 3.1 Flash TTS** offers premium audio generation at competitive rates.
3. **Live API** is ideal for conversational voice agents, but costs can accumulate quickly.
4. **Google Cloud STT** (Chirp) remains the standard for pure offline transcription at $0.016/minute.
5. **Context Caching** and **Batch API** can save up to 50-90% on speech workloads.

---

## Related Guides

*   📘 [Google Gemini API Pricing Guide](/google-gemini-api-pricing-may-2026/)
*   📗 [OpenAI API Pricing Guide](/openai-api-pricing-may-2026/)
*   📊 [AI Model Comparison 2026](/ai-model-pricing-comparison-gemini-openai-grok-claude-2026/)
*   🧮 [AI API Pricing Calculator](/ai-api-pricing-calculator/)

*Prices are current as of May 2026. Always verify with Google's official documentation before production deployment.*
