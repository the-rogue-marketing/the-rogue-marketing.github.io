---
layout: post
title: "FastAPI + PydanticAI: Streaming Partially Validated Structured JSON to React Frontends with SSE"
description: "Step-by-step developer guide on streaming real-time structured Pydantic objects from FastAPI to React frontends using Server-Sent Events (SSE) and PydanticAI."
author: professor-xai
categories: [pydantic-ai, fastapi, python, dev]
image: assets/images/cheap-ai-agent-tutorial.webp
featured: true
last_modified_at: 2026-10-02
keywords: "fastapi pydanticai stream json, sse streaming pydantic react, real time structured llm output, pydantic partial validation streaming"
faq:
  - question: "Why use Server-Sent Events (SSE) over WebSockets for LLM streaming?"
    answer: "SSE operates over standard HTTP/2, requires no stateful connection handshakes, automatically reconnects on drops, and passes cleanly through corporate proxies and firewalls without custom protocol overhead."
  - question: "How does PydanticAI handle partial JSON parsing?"
    answer: "PydanticAI features built-in progressive validation. As token fragments arrive, it uses jiter or partial-json parsers to populate model fields dynamically before the trailing curly brace arrives."
  - question: "Can React components render partial streaming objects without flickering?"
    answer: "Yes. By subscribing to the SSE stream and updating local React state via useReducer, components can update table rows or progress bars progressively as fields stream in."
---

Waiting 8 to 15 seconds for an LLM to generate an exhaustive JSON object creates terrible user experience. In modern web applications, users demand **instant progressive feedback**—seeing sections, bullet points, and tables render smoothly line-by-line.

Here is the battle-tested blueprint for streaming **partially validated structured objects** from a **FastAPI** backend to a **React** frontend using **Server-Sent Events (SSE)** and **PydanticAI**.

---

## 1. Architectural Pipeline

```
┌──────────────┐          HTTP POST /stream          ┌──────────────┐
│ React Client │ ──────────────────────────────────> │ FastAPI App  │
│              │ <────────────────────────────────── │              │
└──────────────┘      text/event-stream (SSE)        └──────┬───────┘
                                                            │ run_stream()
                                                     ┌──────▼───────┐
                                                     │ PydanticAI   │
                                                     │ Agent Loop   │
                                                     └──────────────┘
```

---

## 2. FastAPI Backend Implementation

```python
import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pydantic_ai import Agent

app = FastAPI(title="PydanticAI SSE Streamer")

class MarketAnalysis(BaseModel):
    summary: str = Field(description="Executive summary")
    bull_points: list[str] = Field(description="Bullish catalysts")
    bear_points: list[str] = Field(description="Downside risks")
    sentiment_score: int = Field(description="0 to 100 sentiment rating")

agent = Agent("google-gla:gemini-2.5-flash", result_type=MarketAnalysis)

@app.get("/api/analyze-stream")
async def stream_analysis(ticker: str):
    async def event_generator():
        prompt = f"Analyze current technical and fundamental setup for {ticker}."
        async with agent.run_stream(prompt) as result:
            async for partial_model in result.stream_structured():
                # Stream partial JSON snapshot as SSE payload
                yield f"data: {partial_model.model_dump_json()}

"
                await asyncio.sleep(0.02)
        yield "event: done
data: {}

"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## 3. React Frontend Consumption Hook

```typescript
import React, { useState, useEffect } from 'react';

export function useStreamingAnalysis(ticker: string) {
  const [data, setData] = useState<any>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const startStream = () => {
    setIsStreaming(true);
    const eventSource = new EventSource(`/api/analyze-stream?ticker=${ticker}`);

    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        setData(parsed);
      } catch (err) {
        console.error("JSON parse error on chunk", err);
      }
    };

    eventSource.addEventListener("done", () => {
      eventSource.close();
      setIsStreaming(false);
    });

    eventSource.onerror = () => {
      eventSource.close();
      setIsStreaming(false);
    };
  };

  return { data, isStreaming, startStream };
}
```

---

## 4. Key Takeaways

1. **Zero UI Blocking**: Users see the headline and first bullet point within 400ms rather than waiting for the entire response to finish.
2. **Type-Safe Contract**: Frontend and backend share exact TypeScript/Pydantic schemas, eliminating runtime parsing exceptions.
3. **HTTP/2 Efficiency**: Multiple concurrent streams multiplex seamlessly across a single TCP connection.
