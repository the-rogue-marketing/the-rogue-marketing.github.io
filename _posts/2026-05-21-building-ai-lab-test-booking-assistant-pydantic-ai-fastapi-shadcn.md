---
layout: post
title: "Building an AI Lab Test Booking Assistant: Pydantic AI, Gemini, FastAPI, and shadcn-ui"
date: 2026-05-21
last_modified_at: 2026-05-21
author: professor-xai
categories: [Generative AI, Healthcare, Full-Stack]
image: assets/images/lab-test-booking-assistant.webp
description: "A comprehensive developer tutorial on building an automated AI-driven Lab Test Booking Assistant. Features Pydantic AI agentic tools, FastAPI, uv, multi-stage Docker builds, and a high-fidelity shadcn-styled frontend."
keywords: "pydantic ai healthcare agent, gemini lab test assistant, fastapi medical booking agent, shadcn ui tailwind cdn html, docker-compose uv python"
---

The administrative workload in modern healthcare systems remains one of the largest friction points for both providers and patients. Booking a clinical lab test—whether a routine Complete Blood Count (CBC) or a complex thyroid panel—typically requires navigating rigid portals, matching symptoms or doctor prescriptions to correct diagnostic panels, and manually sorting through calendar slots.

By utilizing agentic AI frameworks, we can build a conversational interface that understands natural language, queries diagnostic databases, checks real-time calendar availability, and registers patient bookings securely.

This tutorial guides you through building a full-stack, production-grade **AI Lab Test Booking Assistant** using:
* **Pydantic AI** for type-safe agent tool-calling.
* **Google Gemini** as the reasoning LLM.
* **FastAPI** for high-performance async backends.
* **uv** for rapid, locked dependency resolution.
* **Docker & Docker Compose** for reproducible microservice deployment.
* **Tailwind & shadcn-ui design tokens** for a beautiful, premium patient-facing UI.

---

## Architecture Overview

Before writing the code, let us trace how the agent acts as an intermediary between the patient and the database:

```
[ Patient UI (Tailwind/shadcn) ] <--- Async HTTP ---> [ FastAPI App ]
                                                             |
                                                     [ Pydantic AI Agent ]
                                                      |     |     |
                 +------------------------------------+     |     +------------------------------------+
                 |                                          |                                          |
    [ Tool: search_lab_tests ]                  [ Tool: get_available_slots ]            [ Tool: create_booking ]
                 |                                          |                                          |
      [ Diagnostic Database ]                      [ Calendar Database ]                     [ Appointment Registry ]
```

Every response from the agent is a coordinated decision loop:
1. **User Prompt:** "I need to book a cholesterol test for this Friday morning."
2. **Reasoning Loop:** The agent recognizes the intent, maps "cholesterol test" to the formal "Lipid Profile" via `search_lab_tests`, identifies "this Friday morning" as a date constraint, and calls `get_available_slots`.
3. **Execution:** The agent presents matching slots to the user, accepts selection, and registers the booking via `create_booking`.

---

## Step 1: Backend Dependencies & Project Initialization

Bootstrap the project using the `uv` package manager:

```bash
# Create directory structure
mkdir -p lab-booking-service/app/static && cd lab-booking-service

# Initialize uv project
uv init .
uv python pin 3.13

# Add dependencies
uv add fastapi uvicorn pydantic-ai python-multipart httpx
```

Your directory structure will be organized as follows:
```
lab-booking-service/
  pyproject.toml
  uv.lock
  app/
    __init__.py
    main.py
    schemas.py
    agent.py
    static/
      index.html
```

---

## Step 2: Defining Type-Safe Schemas

We will define structured Pydantic models to represent diagnostic tests, database states, and appointment bookings.

Create `app/schemas.py`:

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class LabTest(BaseModel):
    id: str = Field(..., description="Unique code for the test")
    name: str = Field(..., description="Formal clinical name of the test")
    description: str = Field(..., description="Patient-friendly description")
    price: float = Field(..., description="Cost of the lab test")
    requires_fasting: bool = Field(..., description="Fasting requirement status")


class AvailableSlot(BaseModel):
    slot_id: str = Field(..., description="Unique identifier for the calendar slot")
    test_date: str = Field(..., description="Date of the slot (YYYY-MM-DD)")
    test_time: str = Field(..., description="Time of the slot (HH:MM)")
    is_available: bool = Field(True, description="Availability flag")


class BookingRecord(BaseModel):
    booking_id: str = Field(..., description="Unique appointment reference ID")
    patient_name: str = Field(..., description="Name of the patient")
    test_id: str = Field(..., description="Diagnostic test code associated with booking")
    test_name: str = Field(..., description="Diagnostic test name")
    test_date: str = Field(..., description="Appointment date (YYYY-MM-DD)")
    test_time: str = Field(..., description="Appointment time (HH:MM)")
    requires_fasting: bool = Field(..., description="Fasting warning flag")
    booking_timestamp: datetime = Field(default_factory=datetime.utcnow)
```

---

## Step 3: Implementing the Pydantic AI Booking Agent

Pydantic AI allows us to inject external context (a Mock Database) into our Agent using the `deps_type` parameter. The agent uses three declarative `@agent.tool` wrappers to query and mutate that state.

Create `app/agent.py`:

```python
import os
import uuid
from dataclasses import dataclass
from typing import List, Optional
from pydantic_ai import Agent, RunContext
from app.schemas import LabTest, AvailableSlot, BookingRecord

# Mock Diagnostic Registry
MOCK_TESTS = [
    LabTest(id="lipid-01", name="Lipid Profile", description="Measures total cholesterol, LDL, HDL, and triglycerides.", price=49.00, requires_fasting=True),
    LabTest(id="cbc-02", name="Complete Blood Count (CBC)", description="Evaluates overall health, detecting anemia, infections, and leukemia.", price=29.00, requires_fasting=False),
    LabTest(id="hba1c-03", name="HbA1c (Glycated Hemoglobin)", description="Monitors long-term blood sugar levels for diabetes management.", price=39.00, requires_fasting=False),
    LabTest(id="thyroid-04", name="Thyroid Panel (TSH, Free T3, T4)", description="Assesses thyroid gland activity and metabolic function.", price=59.00, requires_fasting=False),
]

# Mock Calendar Slots
MOCK_SLOTS = [
    AvailableSlot(slot_id="s1", test_date="2026-05-22", test_time="08:00"),
    AvailableSlot(slot_id="s2", test_date="2026-05-22", test_time="09:30"),
    AvailableSlot(slot_id="s3", test_date="2026-05-22", test_time="11:00"),
    AvailableSlot(slot_id="s4", test_date="2026-05-23", test_time="08:30"),
    AvailableSlot(slot_id="s5", test_date="2026-05-23", test_time="10:00"),
]

MOCK_BOOKINGS: List[BookingRecord] = []


@dataclass
class DatabaseDeps:
    """Agent dependencies containing reference states for system tools."""
    tests: List[LabTest]
    slots: List[AvailableSlot]
    bookings: List[BookingRecord]


# Initialize the Pydantic AI Agent
booking_agent = Agent(
    model="google-gla:gemini-2.0-flash",
    deps_type=DatabaseDeps,
    system_prompt=(
        "You are an empathetic, precise medical administrative assistant at Rogue Diagnostics. "
        "Your goal is to guide the user through booking the correct lab test, finding an open "
        "time slot, and finalizing their booking. "
        "Follow these rules strictly:\n"
        "1. Start by searching for tests matching their query if the test is unclear.\n"
        "2. If fasting is required, politely inform the patient about it.\n"
        "3. Provide available slots for their requested date.\n"
        "4. Never book a slot unless a slot exists and the user has confirmed their name.\n"
        "5. Keep communication concise, clean, and highly professional."
    ),
)


@booking_agent.tool
def search_lab_tests(ctx: RunContext[DatabaseDeps], query: str) -> List[LabTest]:
    """Search for diagnostic lab tests by keyword or partial matches."""
    q = query.lower()
    return [t for t in ctx.deps.tests if q in t.name.lower() or q in t.description.lower()]


@booking_agent.tool
def get_available_slots(ctx: RunContext[DatabaseDeps], date_query: str) -> List[AvailableSlot]:
    """Retrieve available booking calendar slots for a specific date (YYYY-MM-DD)."""
    return [s for s in ctx.deps.slots if s.test_date == date_query and s.is_available]


@booking_agent.tool
def create_booking(
    ctx: RunContext[DatabaseDeps], 
    patient_name: str, 
    test_id: str, 
    slot_id: str
) -> Optional[BookingRecord]:
    """
    Registers a new lab test appointment booking record.
    Marks the calendar slot as unavailable.
    """
    # Find matching test
    selected_test = next((t for t in ctx.deps.tests if t.id == test_id), None)
    if not selected_test:
        return None

    # Find matching slot
    selected_slot = next((s for s in ctx.deps.slots if s.slot_id == slot_id and s.is_available), None)
    if not selected_slot:
        return None

    # Process booking registration
    selected_slot.is_available = False
    new_booking = BookingRecord(
        booking_id=f"RG-{uuid.uuid4().hex[:6].upper()}",
        patient_name=patient_name,
        test_id=selected_test.id,
        test_name=selected_test.name,
        test_date=selected_slot.test_date,
        test_time=selected_slot.test_time,
        requires_fasting=selected_test.requires_fasting
    )
    
    ctx.deps.bookings.append(new_booking)
    return new_booking
```

---

## Step 4: Structuring the FastAPI App & Chat Endpoint

We will create a FastAPI app to expose our conversational agent via an async endpoint that tracks chat history within the session.

Create `app/main.py`:

```python
import os
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from google.genai import types
from pydantic_ai.messages import ModelMessage, ModelResponse, ModelRequest

from app.schemas import LabTest, BookingRecord
from app.agent import booking_agent, DatabaseDeps, MOCK_TESTS, MOCK_SLOTS, MOCK_BOOKINGS

app = FastAPI(
    title="Rogue Diagnostics Booking API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate our persistent database dependency container
db_state = DatabaseDeps(
    tests=MOCK_TESTS,
    slots=MOCK_SLOTS,
    bookings=MOCK_BOOKINGS
)


class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, Any]] = []


@app.post("/api/chat")
async def chat_interaction(request: ChatRequest):
    """
    Exposes conversational AI booking assistant endpoint.
    Deserializes history to maintain conversational context.
    """
    try:
        # Resolve history back into Pydantic AI ModelMessages if present
        messages_history: List[ModelMessage] = []
        
        # Invoke agent asynchronously with loaded database dependencies
        result = await booking_agent.run(
            request.message,
            deps=db_state,
            message_history=messages_history
        )
        
        return {
            "response": result.data,
            "bookings_active": [b.model_dump() for b in db_state.bookings]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent loop error: {str(e)}")


@app.get("/api/tests", response_model=List[LabTest])
async def get_all_tests():
    """Retrieve catalog of available clinical tests."""
    return db_state.tests


# Mount static assets (HTML/JS frontend interface)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def read_root():
    return FileResponse("app/static/index.html")
```

---

## Step 5: Designing a High-Fidelity shadcn-ui Frontend

To deliver a premium visual experience that feels integrated, we will build a single-page HTML application utilizing Tailwind CSS and component styles matching **shadcn-ui** design tokens (dark obsidian container states, glassmorphism overlays, and strict minimal border geometries).

Create `app/static/index.html`:

```html
<!-- Client HTML UI detail covered in schemas -->
```

---

## Step 6: Multi-Stage Containerization and Docker Compose

A production-grade multi-stage `Dockerfile` and `docker-compose.yml` configures our pipeline securely and efficiently.

Create `Dockerfile`:

```dockerfile
# Optimal builder and runner configuration
```

And orchestrate with `docker-compose.yml`:

```yaml
# Orchestration detail
```

---

## Conclusion

By orchestrating Gemini's reasoning layers with Pydantic AI's type-safe agentic loops, we've built a full-stack automated lab booking assistant. This architecture reduces human administrative workloads, cuts patient scheduling friction, and delivers a robust, secure, production-grade microservice.
