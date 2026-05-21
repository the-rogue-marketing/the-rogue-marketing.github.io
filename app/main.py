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
