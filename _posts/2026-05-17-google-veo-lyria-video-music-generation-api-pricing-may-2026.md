---
layout: post
title: "Google Veo & Lyria API Pricing May 2026: Video Generation & AI Music Complete Cost Guide"
description: "Complete pricing guide for Google's video and music generation APIs as of May 2026 — Veo 3.1, Veo 3, Veo 2 video generation and Lyria 3 Clip & Pro music generation with real-world cost examples."
author: professor-xai
categories: [gemini, ai-api, google-ai, pricing, video-generation, music-generation]
image: assets/images/veo-lyria-media-pricing-may-2026.webp
featured: true
last_modified_at: 2026-05-17
keywords: "veo 3.1 pricing, veo 3 api cost, lyria 3 pricing, google ai video generation, google ai music generation, veo api per second cost, lyria 3 pro pricing"
---

Google's creative AI stack now includes dedicated **video generation** (Veo) and **music generation** (Lyria) APIs. These models can generate cinematic videos with synchronized audio, produce full-length songs, and create 30-second music clips — all through API calls.

This guide covers the exact pricing for every Veo and Lyria model available in May 2026.

---

## Veo — AI Video Generation

Google's Veo family generates videos from text or image prompts. The latest **Veo 3.1** includes native audio generation — dialogue, sound effects, and ambient sounds synchronized to the visuals.

### Veo Model Overview

| Model | Model ID | Key Features |
| :--- | :--- | :--- |
| **Veo 3.1 Standard** | `veo-3.1-generate-preview` | Highest quality, native audio, 4K support |
| **Veo 3.1 Fast** | `veo-3.1-fast-generate-preview` | Faster generation, balanced quality |
| **Veo 3.1 Lite** | `veo-3.1-lite-generate-preview` | Budget option, 720p/1080p |
| **Veo 3 Standard** | `veo-3.0-generate-001` | Stable release, native audio |
| **Veo 3 Fast** | `veo-3.0-fast-generate-001` | Stable fast generation |
| **Veo 2** | `veo-2.0-generate-001` | Previous generation, reliable |

---

## Veo Pricing (Per Second of Video)

| Model Tier | Price per Second | 8-sec Video | 15-sec Video |
| :--- | :--- | :--- | :--- |
| **Veo 3.1 Lite** | **$0.05–$0.08** | ~$0.40–$0.64 | ~$0.75–$1.20 |
| **Veo 3.1 Fast** | **~$0.15** | ~$1.20 | ~$2.25 |
| **Veo 3.1 Standard** | **$0.40–$0.75** | ~$3.20–$6.00 | ~$6.00–$11.25 |
| **Veo 3 Fast** | **~$0.15** | ~$1.20 | ~$2.25 |
| **Veo 3 Standard (video only)** | **~$0.50** | ~$4.00 | ~$7.50 |
| **Veo 3 Standard (with audio)** | **~$0.75** | ~$6.00 | ~$11.25 |
| **Veo 2** | **~$0.35** | ~$2.80 | ~$5.25 |

> **Cost tip:** Use **Veo 3.1 Lite** ($0.05–$0.08/sec) for drafts and storyboarding, then upgrade to **Standard** for the final render. This can cut your iteration costs by 80%.

### Important Notes

- **Native audio:** Veo 3 and 3.1 generate synchronized sound. The "with audio" tier costs more but eliminates the need for separate audio post-production.
- **Resolution affects cost:** Higher resolutions (4K) will be at the upper end of the price range.
- **Paid tier only:** All Veo models require a paid Gemini API plan.

---

## Lyria 3 — AI Music Generation

Google's **Lyria 3** family generates music from text prompts. Unlike per-second pricing, Lyria uses a **flat fee per generation**.

### Lyria Model Overview

| Model | Model ID | Output | Duration |
| :--- | :--- | :--- | :--- |
| **Lyria 3 Clip** | `lyria-3-clip-preview` | Short music clips | Up to 30 seconds |
| **Lyria 3 Pro** | `lyria-3-pro-preview` | Full songs with structure | Up to ~3 minutes |

---

## Lyria 3 Pricing (Per Generation)

| Model | Price per Generation | Max Duration | Per-Second Cost |
| :--- | :--- | :--- | :--- |
| **Lyria 3 Clip** | **$0.04** | ~30 seconds | ~$0.0013/sec |
| **Lyria 3 Pro** | **$0.08** | ~3 minutes | ~$0.0004/sec |

> **Incredible value:** At **$0.08 per 3-minute song**, Lyria 3 Pro is by far the cheapest AI music generation service available. You can generate 1,000 full songs for just $80.

### Lyria 3 Pro Features

- **Structural control:** Define intros, verses, choruses, bridges
- **Genre support:** Pop, rock, electronic, classical, ambient, and more
- **Instrument specification:** Request specific instruments in your prompt
- **Mood control:** Specify energy level, emotion, and tempo

---

## Veo vs. Competitors: How Does Google Compare?

| Provider | Model | Cost for 8-sec Video |
| :--- | :--- | :--- |
| **Google Veo 3.1 Lite** | Budget | **~$0.50** |
| **Google Veo 3.1 Fast** | Mid-tier | **~$1.20** |
| **Google Veo 3.1 Standard** | Premium | **~$4.00+** |
| OpenAI Sora | Standard | ~$3.00+ |
| Runway Gen-4 | Standard | ~$2.50+ |

> Veo 3.1 Lite is extremely competitive for prototyping and social media content at just ~$0.50 per 8-second clip.

---

## Lyria vs. Competitors: Music Generation Costs

| Provider | Cost per Song | Max Duration |
| :--- | :--- | :--- |
| **Google Lyria 3 Pro** | **$0.08** | ~3 minutes |
| **Google Lyria 3 Clip** | **$0.04** | ~30 seconds |
| Suno v4 | ~$0.05–$0.10 | ~4 minutes |
| Udio | ~$0.05–$0.10 | ~2 minutes |

---

## Real-World Cost Scenarios

### Scenario 1: Create a 60-second social media ad

| Step | Model | Cost |
| :--- | :--- | :--- |
| Generate 4 draft clips (8 sec each) | Veo 3.1 Lite | $2.00 |
| Final render (15 sec, with audio) | Veo 3.1 Standard | $11.25 |
| Background music track | Lyria 3 Clip | $0.04 |
| **Total** | | **~$13.29** |

### Scenario 2: Generate 100 product demo videos

| Component | Calculation | Cost |
| :--- | :--- | :--- |
| 100 × 8-sec videos (Veo 3.1 Fast) | 100 × $1.20 | **$120** |
| 100 × background music clips | 100 × $0.04 | **$4** |
| **Total** | | **$124** |

### Scenario 3: Produce a full music album (12 songs)

| Component | Calculation | Cost |
| :--- | :--- | :--- |
| 12 × full songs (Lyria 3 Pro) | 12 × $0.08 | **$0.96** |
| Extra iterations (3× per song) | 36 × $0.08 | **$2.88** |
| **Total** | | **~$3.84** |

> A full 12-track album for under $4. That's the power of AI music generation in 2026.

---

## Access & Availability

| Service | Free Tier | Paid Required | Platform |
| :--- | :--- | :--- | :--- |
| **Veo 3.1** |  |  | Gemini API, Vertex AI |
| **Veo 3** |  |  | Gemini API, Vertex AI |
| **Veo 2** |  |  | Gemini API, Vertex AI |
| **Lyria 3 Clip** | Limited |  | Gemini API, AI Studio |
| **Lyria 3 Pro** | Limited |  | Gemini API, AI Studio |

---

## Key Takeaways

1. **Veo 3.1 Lite** ($0.05–$0.08/sec) is the budget choice for video generation
2. **Veo 3.1 Standard** delivers the highest quality with native audio at ~$0.40–$0.75/sec
3. **Lyria 3 Pro** at **$0.08 per 3-minute song** is absurdly cheap for music generation
4. Use **Lite/Fast** tiers for drafts, then **Standard** for final renders to minimize costs
5. All Veo models require a **paid tier** — no free access
6. Lyria models are available in preview on the Gemini API and Google AI Studio

### Get Started

Try Veo in [Google AI Studio](https://aistudio.google.com/) or explore the [Gemini API video docs](https://ai.google.dev/gemini-api/docs/video). For music, check out [Lyria 3 docs](https://ai.google.dev/gemini-api/docs/music-generation).

---

*Prices are current as of May 2026. Always verify with Google's official documentation before production deployment.*
