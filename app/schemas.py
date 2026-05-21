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
