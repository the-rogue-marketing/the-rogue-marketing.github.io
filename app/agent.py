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
