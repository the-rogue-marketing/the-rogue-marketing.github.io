from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from pydantic_ai import Agent, BinaryContent
from datetime import datetime

from app.kyc_schemas import KYCState, DocumentType, PassportDetails, LicenseDetails


# 1. Initialize Pydantic AI Agents
classifier_agent = Agent(
    model="google-gla:gemini-2.5-flash",
    result_type=DocumentType,
    system_prompt=(
        "You are an identity document classification expert. "
        "Analyze the provided image and classify if it is a passport, "
        "a driver_license, or unknown."
    )
)

passport_extractor = Agent(
    model="google-gla:gemini-2.5-flash",
    result_type=PassportDetails,
    system_prompt=(
        "You are a passport parsing specialist. "
        "Extract all details from the passport image into the structured schema."
    )
)

license_extractor = Agent(
    model="google-gla:gemini-2.5-flash",
    result_type=LicenseDetails,
    system_prompt=(
        "You are a driver's license parsing specialist. "
        "Extract all details from the driver's license image into the structured schema."
    )
)


# 2. Define Graph Nodes
async def classify_document_node(state: KYCState) -> Dict[str, Any]:
    """Classifies the uploaded image document type."""
    result = await classifier_agent.run(
        [
            "Classify this identity document image.",
            BinaryContent(data=state.image_bytes, media_type=state.media_type)
        ]
    )
    return {"document_type": result.output}


async def extract_passport_node(state: KYCState) -> Dict[str, Any]:
    """Extracts passport metadata from the image."""
    result = await passport_extractor.run(
        [
            "Extract structured passport details from this image.",
            BinaryContent(data=state.image_bytes, media_type=state.media_type)
        ]
    )
    return {"passport_data": result.output}


async def extract_license_node(state: KYCState) -> Dict[str, Any]:
    """Extracts license details from the image."""
    result = await license_extractor.run(
        [
            "Extract structured license details from this image.",
            BinaryContent(data=state.image_bytes, media_type=state.media_type)
        ]
    )
    return {"license_data": result.output}


async def validate_kyc_node(state: KYCState) -> Dict[str, Any]:
    """Audits the extracted metadata checking for expiration limits."""
    errors = []
    is_valid = True
    current_date = datetime.utcnow().date()

    expiry_str = None
    if state.document_type == DocumentType.PASSPORT and state.passport_data:
        expiry_str = state.passport_data.expiry_date
    elif state.document_type == DocumentType.LICENSE and state.license_data:
        expiry_str = state.license_data.expiry_date

    if expiry_str:
        try:
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
            if expiry_date < current_date:
                is_valid = False
                errors.append(f"Document has expired on {expiry_str}")
        except Exception:
            is_valid = False
            errors.append(f"Invalid date format: {expiry_str}")
    else:
        is_valid = False
        errors.append("No valid expiration date could be found on the document.")

    return {"is_valid": is_valid, "validation_errors": errors}


# 3. Define Routing Logic
def route_by_document_type(state: KYCState) -> Literal["passport", "driver_license", "unknown"]:
    """Conditional router mapping document classification to extraction nodes."""
    if state.document_type == DocumentType.PASSPORT:
        return "passport"
    elif state.document_type == DocumentType.LICENSE:
        return "driver_license"
    return "unknown"


# 4. Build the LangGraph Workflow
workflow = StateGraph(KYCState)

# Add Node definitions
workflow.add_node("classify", classify_document_node)
workflow.add_node("extract_passport", extract_passport_node)
workflow.add_node("extract_license", extract_license_node)
workflow.add_node("validate", validate_kyc_node)

# Configure Entry Point
workflow.set_entry_point("classify")

# Configure Conditional Routing
workflow.add_conditional_edges(
    "classify",
    route_by_document_type,
    {
        "passport": "extract_passport",
        "driver_license": "extract_license",
        "unknown": END
    }
)

# Connect remaining edges
workflow.add_edge("extract_passport", "validate")
workflow.add_edge("extract_license", "validate")
workflow.add_edge("validate", END)

# Compile Workflow Graph
kyc_pipeline = workflow.compile()
