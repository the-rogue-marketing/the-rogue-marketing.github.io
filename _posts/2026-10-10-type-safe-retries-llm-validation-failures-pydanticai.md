---
layout: post
title: "Type-Safe Retries: Programmatically Recovering from LLM Hallucinations and Schema Errors in PydanticAI"
description: "How to implement programmatic error-recovery loops with PydanticAI. Automatically feed validation tracebacks back to the LLM to self-heal schema errors."
author: professor-xai
categories: [pydantic-ai, python, dev]
image: assets/images/cheap-ai-agent-tutorial.webp
featured: true
last_modified_at: 2026-10-10
keywords: "pydanticai validation error retry, self healing llm schema errors, pydantic field validator retry agent, handle llm hallucinations python"
faq:
  - question: "What happens when an LLM fails a Pydantic validator in PydanticAI?"
    answer: "PydanticAI catches the `ValidationError`, serializes the exact field name and error message into the next model prompt turn, and prompts the LLM to correct only the offending field."
  - question: "How many retries does PydanticAI perform by default?"
    answer: "PydanticAI defaults to 1 retry, but developers can configure `retries=3` on the agent or individual tools for resilient execution."
  - question: "Why is self-healing validation superior to regex fallbacks?"
    answer: "Self-healing allows the LLM to understand why its output violated business rules (e.g. 'Date must be in the future') and reason through the correction rather than breaking your application."
---

Even frontier models occasionally generate invalid outputs: returning an ISO-8601 string where a float was expected, omitting a mandatory nested object, or failing business validation rules.

In traditional frameworks, this triggers a fatal `pydantic.ValidationError` that crashes your API endpoint.

**PydanticAI** introduces **Self-Healing Type-Safe Retries**: intercepting validation errors and feeding the exact schema traceback back to the LLM so it corrects its own mistakes autonomously.

---

## 1. The Self-Healing Validation Loop

```
┌─────────────────┐       1. Generates JSON       ┌────────────────────────┐
│ PydanticAI Agent│ ────────────────────────────> │ Pydantic Validator     │
└────────┬────────┘                               └───────────┬────────────┘
         ▲                                                    │ 2. Fails Rule:
         │                                                    │ "Age must be >= 18"
         │            3. Re-prompts with Traceback            │
         └────────────────────────────────────────────────────┘
```

---

## 2. Complete Code Example

```python
from pydantic import BaseModel, field_validator
from pydantic_ai import Agent, ModelRetry

class FlightBooking(BaseModel):
    passenger_name: str
    passport_number: str
    departure_airport: str
    destination_airport: str
    seat_class: str

    @field_validator("departure_airport", "destination_airport")
    @classmethod
    def validate_iata_code(cls, v: str) -> str:
        if len(v) != 3 or not v.isupper():
            # Raises a ModelRetry instructing the LLM to fix the IATA code!
            raise ModelRetry(f"'{v}' is not a valid 3-letter uppercase IATA code (e.g., LHR, JFK).")
        return v

agent = Agent(
    "google-gla:gemini-2.5-flash",
    result_type=FlightBooking,
    retries=3, # Automatically retries up to 3 times on validation failure
    system_prompt="You are an airline reservation agent. Extract travel itineraries into booking records."
)

result = agent.run_sync("Book a flight for Jane Doe from London Heathrow to New York JFK in business class.")

print("Validated Booking:", result.data)
```

---

## 3. Key Architectural Benefits

1. **Zero Runtime Crashes**: Production endpoints never return unhandled 500 errors due to format discrepancies.
2. **Deterministic Output Guarantees**: Downstream database and payment microservices receive 100% verified data.
3. **Transparent Audit Logging**: PydanticAI records all retry attempts, providing clear debugging telemetry.
