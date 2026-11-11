---
layout: post
title: 'FastAPI + PydanticAI: Streaming Partially Validated Structured JSON to React Frontends with SSE'
description: A complete developer guide on streaming real-time structured Pydantic objects from FastAPI to React frontends using Server-Sent Events (SSE), partial-JSON parsing, and PydanticAI.
author: professor-xai
categories: [AI Agents & Autonomous Systems]
image: assets/images/fastapi-streaming-json.webp
featured: true
last_modified_at: 2026-10-02
keywords: fastapi pydanticai stream json, sse streaming pydantic react, real time structured llm output, pydantic partial validation streaming, partial json parsing python
faq:
- question: 'Why use Server-Sent Events (SSE) over WebSockets for LLM streaming?'
  answer: 'SSE operates over standard HTTP/2 and HTTP/1.1, requires no complex stateful connection handshakes, automatically handles client reconnection on network drops, and passes cleanly through corporate proxies, firewalls, and cloud load balancers without custom protocol overhead.'
- question: 'How does progressive partial JSON parsing work in PydanticAI?'
  answer: 'As raw token chunks arrive from the LLM, the JSON stream contains incomplete syntax (unclosed quotes, missing brackets). PydanticAI utilizes specialized partial parsers (like jiter) that automatically close uncompleted structures in memory, populating Pydantic model fields progressively before the final closing brace arrives.'
- question: 'How do you prevent Nginx or Cloudflare from buffering SSE streaming chunks?'
  answer: 'Configure backend HTTP headers with "Cache-Control: no-cache", "Connection: keep-alive", and "X-Accel-Buffering: no". In Nginx reverse proxy configurations, explicitly disable proxy buffering with "proxy_buffering off;" and set "proxy_cache off;".'
tags: [AI APIs, DevOps, PydanticAI, Python, TypeScript]
---

Waiting 8 to 15 seconds for an LLM to generate an exhaustive JSON object creates a sluggish, unresponsive user experience. In modern AI applications, users demand **immediate progressive visual feedback**—watching summary paragraphs, bulleted risks, and metrics render dynamically on the screen as tokens are generated.

However, streaming structured data introduces a core technical challenge:
* Streaming raw text prose is trivial (`yield chunk.text`).
* But streaming structured data means token fragments like `{"summary": "Market exhibits strong` are **syntactically invalid JSON**. Calling `JSON.parse()` on the frontend will throw immediate syntax errors and crash the UI.

The solution is **Progressive Partial-Model Streaming**: combining **PydanticAI's** built-in partial JSON parser with a **FastAPI Server-Sent Events (SSE)** endpoint and a resilient **React streaming hook**.

This guide provides the complete end-to-end implementation for both backend and frontend.

---

## 1. The Real-Time Streaming Architecture

```
┌─────────────────┐       HTTP GET /api/analyze-stream       ┌─────────────────┐
│  React Browser  │ ───────────────────────────────────────> │  FastAPI Server │
│                 │ <─────────────────────────────────────── │                 │
└────────┬────────┘      text/event-stream (SSE Chunks)      └────────┬────────┘
         │                                                            │
         │ Updates state on every chunk                               │ run_stream()
         ▼                                                            ▼
┌─────────────────┐                                          ┌─────────────────┐
│ Progressive UI  │                                          │ PydanticAI      │
│ Renders cards,  │                                          │ Progressive     │
│ lists & scores  │                                          │ Partial Parser  │
│ in real time    │                                          └─────────────────┘
└─────────────────┘
```

---

## 2. The FastAPI Backend: Progressive Structured Streaming

PydanticAI provides a native `run_stream()` context manager. Calling `stream_structured()` yields partially validated snapshots of your target Pydantic model at each token increment:

```python
import asyncio
import json
from typing import List, Optional
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_ai import Agent

app = FastAPI(title="PydanticAI Real-Time SSE Gateway")

# Enable CORS for local React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Define the Structured Response Contract
class FinancialAnalysisPayload(BaseModel):
    executive_summary: str = Field(description="High-level overview of current asset condition")
    bull_catalysts: List[str] = Field(default_factory=list, description="Key upward drivers")
    bear_risks: List[str] = Field(default_factory=list, description="Downside risk factors")
    target_price_12m: Optional[float] = Field(None, description="Projected 12-month valuation")
    conviction_score: Optional[int] = Field(None, description="Confidence rating from 1 to 100")

# 2. Initialize PydanticAI Agent
analyst_agent = Agent(
    "google-gla:gemini-2.5-flash",
    result_type=FinancialAnalysisPayload,
    system_prompt=(
        "You are a Wall Street quantitative equities analyst. "
        "Provide thorough, data-driven financial research structured precisely into the requested format."
    )
)

# 3. Streaming SSE Endpoint
@app.get("/api/v1/analyze-equity-stream")
async def stream_equity_analysis(ticker: str):
    """Streams progressive partial JSON snapshots to frontend via SSE."""
    
    async def sse_event_generator():
        prompt = f"Conduct a comprehensive technical and fundamental valuation analysis of {ticker}."
        
        try:
            async with analyst_agent.run_stream(prompt) as stream:
                # stream_structured() emits progressive Pydantic model instances
                async for partial_snapshot in stream.stream_structured():
                    # Serialize partial snapshot to JSON string
                    payload_json = partial_snapshot.model_dump_json()
                    
                    # Yield standards-compliant SSE event
                    yield f"event: partial\ndata: {payload_json}\n\n"
                    await asyncio.sleep(0.015)  # Yield control to event loop

            # Emit terminal completion event
            yield "event: complete\ndata: {}\n\n"

        except Exception as exc:
            error_data = json.dumps({"error": str(exc)})
            yield f"event: error\ndata: {error_data}\n\n"

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"  # Crucial: Disables Nginx reverse proxy buffering
    }

    return StreamingResponse(sse_event_generator(), headers=headers)
```

---

## 3. The React Frontend: TypeScript Streaming Hook

To consume an SSE stream with high reliability, use the `fetch()` API with a `ReadableStreamDefaultReader` rather than the legacy `EventSource` API (which lacks support for custom headers and granular error handling):

```typescript
import { useState, useCallback } from 'react';

export interface FinancialAnalysis {
  executive_summary?: string;
  bull_catalysts?: string[];
  bear_risks?: string[];
  target_price_12m?: number;
  conviction_score?: number;
}

export function useStructuredAnalysis() {
  const [data, setData] = useState<FinancialAnalysis | null>(null);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const startStream = useCallback(async (ticker: string) => {
    setIsStreaming(true);
    setError(null);
    setData(null);

    try {
      const response = await fetch(`http://localhost:8000/api/v1/analyze-equity-stream?ticker=${encodeURIComponent(ticker)}`);
      if (!response.ok || !response.body) {
        throw new Error(`HTTP network error: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || ''; // Keep partial line in buffer

        for (const block of lines) {
          if (!block.trim()) continue;

          const match = block.match(/^event:\s*(\w+)\s*\ndata:\s*(.*)$/s);
          if (!match) continue;

          const [, eventType, rawData] = match;

          if (eventType === 'partial') {
            try {
              const parsed: FinancialAnalysis = JSON.parse(rawData);
              setData(parsed);
            } catch (err) {
              console.warn('Skipping malformed SSE frame', err);
            }
          } else if (eventType === 'complete') {
            setIsStreaming(false);
          } else if (eventType === 'error') {
            setError(rawData);
            setIsStreaming(false);
          }
        }
      }
    } catch (err: any) {
      setError(err.message || 'Stream processing failed');
    } finally {
      setIsStreaming(false);
    }
  }, []);

  return { data, isStreaming, error, startStream };
}
```

---

## 4. Building the Real-Time React Dashboard Component

With the hook in place, building an interactive progressive dashboard is simple:

```tsx
import React, { useState } from 'react';
import { useStructuredAnalysis } from './useStructuredAnalysis';

export const EquityDashboard: React.FC = () => {
  const [ticker, setTicker] = useState('NVDA');
  const { data, isStreaming, error, startStream } = useStructuredAnalysis();

  return (
    <div style={{ maxWidth: '800px', margin: '40px auto', fontFamily: 'sans-serif' }}>
      <h2>Real-Time Equity Research Terminal</h2>
      
      <div style={{ display: 'flex', gap: '10px', marginBottom: '24px' }}>
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          style={{ padding: '8px 16px', fontSize: '16px' }}
          placeholder="Ticker (e.g. AAPL)"
        />
        <button
          onClick={() => startStream(ticker)}
          disabled={isStreaming}
          style={{ padding: '8px 24px', fontSize: '16px', cursor: 'pointer' }}
        >
          {isStreaming ? 'Streaming Research...' : 'Run Analysis'}
        </button>
      </div>

      {error && <div style={{ color: 'red', marginBottom: '16px' }}>Error: {error}</div>}

      {data && (
        <div style={{ border: '1px solid #e2e8f0', padding: '24px', borderRadius: '8px' }}>
          {/* Executive Summary */}
          <h3>Executive Summary</h3>
          <p>{data.executive_summary || <span style={{ color: '#94a3b8' }}>Generating summary...</span>}</p>

          {/* Catalysts Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginTop: '20px' }}>
            <div>
              <h4 style={{ color: '#16a34a' }}>Bullish Catalysts</h4>
              <ul>
                {data.bull_catalysts?.map((catalyst, idx) => (
                  <li key={idx}>{catalyst}</li>
                ))}
              </ul>
            </div>

            <div>
              <h4 style={{ color: '#dc2626' }}>Downside Risks</h4>
              <ul>
                {data.bear_risks?.map((risk, idx) => (
                  <li key={idx}>{risk}</li>
                ))}
              </ul>
            </div>
          </div>

          {/* Key Metrics */}
          <div style={{ display: 'flex', gap: '30px', marginTop: '24px', paddingTop: '16px', borderTop: '1px solid #eee' }}>
            <div>
              <strong>Target Price (12M): </strong>
              {data.target_price_12m ? `$${data.target_price_12m}` : 'Calculating...'}
            </div>
            <div>
              <strong>Analyst Conviction: </strong>
              {data.conviction_score ? `${data.conviction_score} / 100` : 'Evaluating...'}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
```

---

## 5. Nginx Production Reverse Proxy Configuration

When deploying behind an Nginx reverse proxy, Nginx defaults to **buffering backend responses until buffers fill**, completely breaking SSE real-time streaming and forcing users to wait until the request finishes.

Add the following directives to your Nginx `location` block:

```nginx
location /api/v1/analyze-equity-stream {
    proxy_pass http://fastapi_backend:8000;
    
    # 1. Disable Nginx Proxy Buffering
    proxy_buffering off;
    proxy_cache off;
    
    # 2. Enforce HTTP/1.1 for persistent chunked connections
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    
    # 3. Increase timeouts for long-running generative sessions
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    
    # 4. Forward host headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

By enforcing `proxy_buffering off;` and pairing PydanticAI's `stream_structured()` with React state reducers, users receive immediate, responsive UI updates with zero parsing crashes.
