---
layout: post
title: "Architecting Multi-Document KYC Pipelines: Gemini OCR and LangGraph"
date: 2026-05-21
last_modified_at: 2026-05-21
author: professor-xai
categories: [Generative AI, Workflow Automation, Security]
image: assets/images/kyc-workflow.webp
description: "A complete developer guide to building a stateful multi-document KYC extraction pipeline. Integrates Gemini vision OCR, LangGraph workflow state machines, and FastAPI."
keywords: "langgraph document extraction workflow, gemini ocr kyc pipeline, fastapi passport license parser, identity verification agent python, docker-compose uv python"
---

Identity verification (Know Your Customer or KYC) is a critical compliance check in fintech, travel, healthcare, and sharing-economy platforms. Extracting data from identity documents—such as passports and driver's licenses—typically requires chaining multiple complex systems: document classification, specialized OCR, key-value extraction, and custom validation heuristics.

Chaining these systems in a robust, stateful manner is challenging. Documents might be uploaded upside down, suffer from low lighting, or turn out to be completely incorrect document types.

By combining the native multimodal vision capabilities of **Google Gemini** with **LangGraph** (a framework for building stateful, multi-actor applications), we can build an automated **KYC Document Processing Pipeline**. 

This pipeline classifies uploaded identity documents, routes them to document-specific extraction nodes, performs validation audits (checking for expiration dates), and outputs verified identity structures.

This tutorial guides you through building this system using LangGraph, Gemini, FastAPI, uv, and Docker Compose.

---

## Stateful Workflow Pipeline Design

Traditional linear workflows break down when processing complex, variable documents. By utilizing LangGraph, we can represent our KYC process as a stateful, directed graph that supports conditional routing:

```
                      +-------------------+
                      |   [ Upload Doc ]  |
                      +---------+---------+
                                |
                     +----------v-----------+
                     |  Node: Classify Doc  |
                     +----------+-----------+
                                |
                   (Is Passport? / Is License?)
                                |
             +------------------+------------------+
             |                                     |
   +---------v----------+                +---------v----------+
   | Node: Ext Passport |                |  Node: Ext License |
   +---------+----------+                +---------+----------+
             |                                     |
             +------------------+------------------+
                                |
                     +----------v-----------+
                     |  Node: Validate KYC  |
                     +----------+-----------+
                                |
                       +--------v--------+
                       |  [ Final State ]|
                       +-----------------+
```

The pipeline state is maintained in a centralized state class (`KYCState`) as it transitions between nodes.

---

## Step 1: Defining KYC State & Extraction Schemas

We will construct schemas representing the web submission and the active state of verification.

Create the schemas in `app/kyc_schemas.py`:

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class DocumentType(str, Enum):
    PASSPORT = "passport"
    LICENSE = "driver_license"
    UNKNOWN = "unknown"


class PassportDetails(BaseModel):
    passport_number: str = Field(..., description="Unique passport identifier")
    given_names: str = Field(..., description="First and middle names")
    surname: str = Field(..., description="Last name or family name")
    date_of_birth: str = Field(..., description="Birthdate formatted as YYYY-MM-DD")
    nationality: str = Field(..., description="Country of citizenship")
    expiry_date: str = Field(..., description="Expiration date formatted as YYYY-MM-DD")
    mrz_code: Optional[str] = Field(None, description="Machine-readable zone text at bottom")


class LicenseDetails(BaseModel):
    license_number: str = Field(..., description="Unique license identifier")
    full_name: str = Field(..., description="Full name of licensee")
    date_of_birth: str = Field(..., description="Birthdate formatted as YYYY-MM-DD")
    expiry_date: str = Field(..., description="Expiration date formatted as YYYY-MM-DD")
    license_class: Optional[str] = Field(None, description="Class of vehicles permitted (e.g. 'Class C')")
    address: Optional[str] = Field(None, description="Physical address listed on license")


class KYCState(BaseModel):
    image_bytes: bytes = Field(..., description="Uploaded raw document image")
    media_type: str = Field(..., description="MIME type of the image")
    document_type: DocumentType = DocumentType.UNKNOWN
    passport_data: Optional[PassportDetails] = None
    license_data: Optional[LicenseDetails] = None
    is_valid: bool = False
    validation_errors: List[str] = Field(default_factory=list)
```

---

## Step 2: Constructing the LangGraph Workflow State Machine

Now we define our processing nodes and orchestrate them using LangGraph. We use Pydantic AI agents internally inside the nodes to perform the targeted extraction using `google-gla:gemini-2.5-flash`.

Create `app/kyc_workflow.py`:

```python
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from pydantic_ai import Agent, BinaryContent
from datetime import datetime

from app.kyc_schemas import KYCState, DocumentType, PassportDetails, LicenseDetails


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


def route_by_document_type(state: KYCState) -> Literal["passport", "driver_license", "unknown"]:
    """Conditional router mapping document classification to extraction nodes."""
    if state.document_type == DocumentType.PASSPORT:
        return "passport"
    elif state.document_type == DocumentType.LICENSE:
        return "driver_license"
    return "unknown"


workflow = StateGraph(KYCState)

workflow.add_node("classify", classify_document_node)
workflow.add_node("extract_passport", extract_passport_node)
workflow.add_node("extract_license", extract_license_node)
workflow.add_node("validate", validate_kyc_node)

workflow.set_entry_point("classify")

workflow.add_conditional_edges(
    "classify",
    route_by_document_type,
    {
        "passport": "extract_passport",
        "driver_license": "extract_license",
        "unknown": END
    }
)

workflow.add_edge("extract_passport", "validate")
workflow.add_edge("extract_license", "validate")
workflow.add_edge("validate", END)

kyc_pipeline = workflow.compile()
```

---

## Step 3: Setting Up the FastAPI Gateway

Create `app/kyc_main.py`:

```python
import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.kyc_schemas import KYCState, DocumentType
from app.kyc_workflow import kyc_pipeline

app = FastAPI(
    title="Stateful KYC Pipeline Hub",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

ALLOWED_IMAGES = {"image/jpeg", "image/png", "image/webp"}


@app.post("/api/v1/kyc/verify")
async def verify_identity_document(file: UploadFile = File(...)):
    """
    KYC document verification pipeline.
    Runs LangGraph workflow asynchronously, returning state verification maps.
    """
    if file.content_type not in ALLOWED_IMAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {file.content_type}. Use JPEG, PNG, or WebP."
        )

    try:
        image_bytes = await file.read()
        
        # Initialize Graph State
        initial_state = KYCState(
            image_bytes=image_bytes,
            media_type=file.content_type
        )

        # Execute Graph Workflow Pipeline
        final_state = await kyc_pipeline.ainvoke(initial_state)

        # Prepare clean response schema payload
        response = {
            "document_type": final_state.document_type.value,
            "is_valid": final_state.is_valid,
            "validation_errors": final_state.validation_errors,
            "extraction_results": None
        }

        if final_state.document_type == DocumentType.PASSPORT:
            response["extraction_results"] = final_state.passport_data.model_dump() if final_state.passport_data else None
        elif final_state.document_type == DocumentType.LICENSE:
            response["extraction_results"] = final_state.license_data.model_dump() if final_state.license_data else None

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")


# Serve static pages
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def read_root():
    return FileResponse("app/static/kyc.html")
```

---

## Conclusion

Combining LangGraph and Google Gemini lets us replace multiple specialized document processing systems with a single stateful, conditional python application. The VLM acts as classifier and extractor, while LangGraph manages routing, errors, and validation, guaranteeing strict control over downstream KYC outputs.
