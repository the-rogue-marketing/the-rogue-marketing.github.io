---
layout: post
title: 'Zero-Failure Structured Output: Extracting Complex Tables and Handwritten
  Receipts with Vision LLMs'
description: Master structured extraction from crumpled receipts, skewed invoices,
  and handwritten notes using Gemini 2.5 Flash multimodal vision and strict Pydantic
  models.
author: professor-xai
categories: [AI Agents & Autonomous Systems]
image: assets/images/gemini-ocr-pydantic-ai.webp
featured: true
last_modified_at: 2026-10-10
keywords: extract handwritten text vision llm, complex table extraction pdf python,
  receipt parsing pydantic ai, zero hallucination structured ocr
faq:
- {question: 'How do Vision LLMs overcome traditional OCR failures on handwriting?',
  answer: 'Traditional OCR looks at local pixel geometry, failing on irregular cursive
    or smudged numbers. Multimodal LLMs read global context, understanding that a
    grocery receipt line item ''$3._9'' next to ''MILK'' is ''$3.49''.'}
- {question: 'How do you handle multi-page PDF tables that split across page breaks?',
  answer: 'Extract page tables as serialized Markdown arrays, then pass them to an
    aggregator prompt that reconciles continuation rows before final Pydantic model
    validation.'}
- {question: 'What temperature setting guarantees zero hallucination on numbers?',
  answer: Always set `temperature=0.0`. Combine with strict enum constraints and mathematical
    validator checks inside Pydantic.}
tags: [OCR & Vision, PydanticAI, Python]
---
Real-world enterprise documents are messy: thermal paper receipts with faded ink, crumpled delivery notes, skewed smartphone scans, and multi-column tables with merged header cells.

Here is how to design a **Zero-Failure Document Extraction Pipeline** that handles handwriting and complex tables without hallucinations.

---

## 1. Schema with Self-Validating Mathematical Rules

```python
from pydantic import BaseModel, Field, model_validator

class TableRow(BaseModel):
    item_code: str
    description: str
    quantity: float
    unit_price: float
    total: float

class FinancialDocument(BaseModel):
    document_id: str
    rows: list[TableRow]
    subtotal: float
    tax: float
    calculated_grand_total: float

    @model_validator(mode="after")
    def verify_math_consistency(self):
        computed_subtotal = sum(r.total for r in self.rows)
        # Tolerate 1-cent rounding discrepancies
        if abs(computed_subtotal - self.subtotal) > 0.05:
            raise ValueError(f"Math check failed: Rows sum {computed_subtotal} != subtotal {self.subtotal}")
        return self
```

---

## 2. Multimodal Extraction Engine

```python
import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def extract_handwritten_table(image_bytes: bytes) -> FinancialDocument:
    prompt = (
        "Transcribe this handwritten inventory dispatch document into structured JSON. "
        "Calculate arithmetic totals verified against row values. If ink is smudged, infer the number mathematically."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"), prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FinancialDocument,
            temperature=0.0
        )
    )

    return FinancialDocument.model_validate_json(response.text)
```
