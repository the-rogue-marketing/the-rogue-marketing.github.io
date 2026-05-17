---
layout: post
title: "Google Gemini TTS & Speech AI Pricing May 2026: Text-to-Speech, Live Audio & STT Complete Guide"
description: "Complete pricing guide for Google's speech and audio AI APIs as of May 2026 — Gemini 3.1 Flash TTS, 2.5 Flash/Pro TTS, Live API audio, Google Cloud STT (Chirp), and Gemini audio understanding."
author: professor-xai
categories: [gemini, ai-api, google-ai, pricing, text-to-speech, speech-ai]
image: assets/images/gemini-tts-speech-pricing-may-2026.png
featured: false
last_modified_at: 2026-05-17
keywords: "gemini tts pricing, gemini text to speech cost, google ai speech api, gemini 3.1 flash tts, gemini live api pricing, google stt pricing, chirp speech to text"
---

Google now offers speech AI through **multiple different services**, each with its own pricing model. Whether you're building a voice assistant, transcribing podcasts, or generating audiobook narrations, this guide maps every option and its exact cost.

---

## 🗣️ The Google Speech AI Landscape

Google's speech capabilities are split across three distinct services:

| Service | What It Does | Pricing Model |
| :--- | :--- | :--- |
| **Gemini TTS** | Text → Natural speech | Per token |
| **Gemini Live API** | Real-time bidirectional voice | Per token (audio) |
| **Google Cloud STT** | Audio → Text transcription | Per minute |
| **Gemini Audio Understanding** | Audio → Analysis/summary | Per token |

Let's break each one down.

---

## 🎙️ Gemini TTS Models — Text-to-Speech

### Gemini 3.1 Flash TTS (Preview)

The latest and most capable TTS model. Supports 70+ languages, multi-speaker synthesis, and granular control via natural language audio tags.

**Model ID:** `gemini-3.1-flash-tts-preview`

| Cost Type | Price per 1M Tokens |
| :--- | :--- |
| **Input (text)** | **$1.00** |
| **Output (audio)** | **$20.00** |
| **Batch Input** | **$0.50** |
| **Batch Output** | **$10.00** |

> 💡 **Token-to-seconds conversion:** Audio output tokens correspond to **25 tokens per second**. This means 1 million output tokens = ~11 hours of audio.

#### Real-World Cost Example

**Generate a 10-minute podcast narration (~6,000 words input, 600 seconds of audio):**

| Cost Component | Calculation | Amount |
| :--- | :--- | :--- |
| Input tokens (~8,000) | 8K × $1.00/1M | **$0.008** |
| Output tokens (600s × 25) | 15,000 × $20.00/1M | **$0.30** |
| **Total** | | **~$0.31** |

At **31 cents for 10 minutes** of high-quality speech, Gemini TTS is extremely competitive.

---

### Gemini 2.5 Flash TTS (Preview)

A more cost-efficient option, optimized for lower latency.

**Model ID:** `gemini-2.5-flash-preview-tts`

| Cost Type | Price per 1M Tokens |
| :--- | :--- |
| **Input (text)** | **$0.15** |
| **Output (audio)** | **$6.00** |
| **Batch Input** | **$0.075** |
| **Batch Output** | **$3.00** |

> 🎯 **Best for:** High-volume TTS at lower cost. At $6/M output tokens, a 10-minute narration costs only **~$0.09** — 3× cheaper than 3.1 Flash TTS.

---

### Gemini 2.5 Pro TTS (Preview)

The premium TTS option — more natural outputs and easier-to-steer prompts.

**Model ID:** `gemini-2.5-pro-preview-tts`

| Cost Type | Price per 1M Tokens |
| :--- | :--- |
| **Input (text)** | **$1.25** |
| **Output (audio)** | **$20.00** |
| **Batch Input** | **$0.625** |
| **Batch Output** | **$10.00** |

---

## 📊 TTS Model Comparison at a Glance

| Model | Input/1M | Output/1M | 10-min Cost | Best For |
| :--- | :--- | :--- | :--- | :--- |
| **2.5 Flash TTS** | $0.15 | $6.00 | ~$0.09 | Budget narration, IVR |
| **3.1 Flash TTS** | $1.00 | $20.00 | ~$0.31 | Natural conversation, apps |
| **2.5 Pro TTS** | $1.25 | $20.00 | ~$0.31 | Premium voice quality |

---

## 🔴 Gemini Live API — Real-Time Voice

For real-time, bidirectional audio conversations (think: voice assistants, customer service bots).

**Model ID:** `gemini-3.1-flash-live-preview`

| Cost Type | Price per 1M Tokens |
| :--- | :--- |
| **Text Input** | **$1.00** |
| **Audio Input** | **$1.00** |
| **Text Output** | **$6.00** |
| **Audio Output** | **$20.00** |

### Key Details

- **Audio tokens:** 25 tokens per second of audio (both input and output)
- **Real-time streaming:** Low-latency, designed for conversational agents
- **Multimodal:** Supports audio + video input for "see and speak" applications
- **Acoustic awareness:** Detects tone, emotion, and ambient sounds

> ⚠️ **Cost warning:** A 1-hour voice conversation would cost approximately **$1.80 in audio input** + **$72 in audio output**. Design your agent to keep responses concise!

---

## 🎧 Gemini Audio Understanding — Speech-to-Analysis

Instead of traditional STT, Gemini can directly **analyze, summarize, and reason** about audio content using its multimodal capabilities.

| Model | Input/1M Tokens | Output/1M Tokens |
| :--- | :--- | :--- |
| **Gemini 3.1 Flash-Lite** | $0.25 | $1.50 |
| **Gemini 3 Flash** | $0.50 | $3.00 |
| **Gemini 3.1 Pro** | $2.00 | $12.00 |

**Use this when** you need more than transcription — summarization, sentiment analysis, meeting action items, translation, or Q&A about audio content.

---

## 📝 Google Cloud Speech-to-Text (Chirp) — Traditional STT

For dedicated, high-accuracy transcription, Google Cloud's STT API remains the best option.

| Model | Price per Minute | Free Tier |
| :--- | :--- | :--- |
| **Chirp (Standard)** | **$0.016** | 60 min/month |
| **Chirp (High Volume 500K+ min)** | **$0.012** | — |
| **Chirp (High Volume 2M+ min)** | **$0.004** | — |

### Important Billing Details

- Billed in **15-second increments** (rounds up)
- Supports 125+ languages with auto-detection
- **$300 free credits** for new Google Cloud accounts

---

## 🧮 Full Cost Comparison: All Speech Services

**Scenario:** Process 1 hour of audio content

| Task | Best Service | Estimated Cost |
| :--- | :--- | :--- |
| **Transcribe audio → text** | Google Cloud STT (Chirp) | **$0.96** |
| **Summarize meeting audio** | Gemini 3 Flash (audio input) | **~$1.50** |
| **Generate 1-hour audiobook** | Gemini 2.5 Flash TTS | **~$5.40** |
| **Generate 1-hour audiobook** | Gemini 3.1 Flash TTS | **~$18.00** |
| **Real-time voice agent (1 hour)** | Gemini Live API | **~$73.80** |

---

## ✅ Key Takeaways

1. **Gemini 2.5 Flash TTS** is the cheapest option at **$0.09 per 10 minutes** of speech
2. **Gemini 3.1 Flash TTS** offers the best quality-to-cost ratio for natural speech
3. **Live API** is designed for real-time agents — but costs add up fast for long conversations
4. **Google Cloud STT** is still the cheapest for pure transcription at $0.016/minute
5. **Gemini Audio Understanding** is the smart choice when you need analysis, not just transcription
6. **Batch API** saves 50% on all TTS models for non-urgent workloads

### Get Started

Try Gemini TTS in [Google AI Studio](https://aistudio.google.com/generate-speech) or check the [official pricing page](https://ai.google.dev/pricing) for the latest rates.

---

*Prices are current as of May 2026. Always verify with Google's official documentation before production deployment.*
