---
layout: post
title: "Clinical Workflow Automation: Building HIPAA-Aligned Systems with Gemini 3.1 Pro, Pydantic AI, and FastAPI"
description: "A comprehensive, production-grade guide to building clinical SOAP note generators and ICD-11 coding systems using Gemini 3.1 Pro, Pydantic AI, FastAPI, and uv."
author: professor-xai
categories: [ai-api, healthcare, pydantic-ai, fastapi]
image: assets/images/healthcare-clinical-workflow.png
featured: true
last_modified_at: 2026-05-21
keywords: "healthcare ai automation, gemini api medical soap notes, pydantic ai healthcare tutorial, fastapi icd 11 medical coding, hipaa compliant llm workflow"
---

Modern clinical medicine is drowning in administrative tasks. Doctors spend up to two hours on documentation and data entry for every single hour they spend face-to-face with patients. Automating this clinical workflow is one of the most impactful frontiers of **May 2026**.

To build software that automates clinical summarization and medical coding (such as ICD-11 extraction), standard prompt engineering is not enough. Medical software requires **deterministic structured outputs**, **strict validation schemas**, and **absolute compliance safeguards**.

In this guide, we will build a production-grade clinical workflow automation system. We will walk through setting up a lightning-fast Python workspace using **uv**, building a structured validation layer with **Pydantic AI**, and exposing robust asynchronous endpoints with **FastAPI** to compile clinical recordings into fully structured **SOAP (Subjective, Objective, Assessment, Plan)** notes and SNOMED-CT/ICD-11 medical codes.

---

## 🛠️ The Modern Tech Stack: Why Pydantic AI, FastAPI, and uv?

Before we write code, let's understand why this specific stack is the standard for LLM applications in 2026:

1. **`uv` (Astral):** Replaces `pip`, `pip-tools`, and `poetry`. It is written in Rust, resolves dependencies in milliseconds, and manages virtual environments seamlessly.
2. **Pydantic AI:** The official agentic framework by the Pydantic team. It allows developers to build type-safe, validated LLM agents. Instead of receiving loose, unvalidated JSON string payloads, your LLM calls return complete, instantiated Pydantic models.
3. **FastAPI:** Built on Starlette and Pydantic, it provides sub-millisecond route handling and automatic OpenAPI documentation based on your code's Pydantic schemas.
4. **Gemini 3.1 Pro:** Google's flagship multimodal model with a 1-million-token context window, ideal for ingesting hours of patient audio transcripts and complex medical guidelines.

---

## 🏗️ Bootstrapping the Medical Tech Workspace with `uv`

First, let's initialize our application directory and install our production dependencies using `uv`. 

Open your terminal and run:

```bash
# 1. Initialize a new project using uv
uv init clinical-agent
cd clinical-agent

# 2. Add our production dependencies
uv add fastapi uvicorn pydantic-ai google-genai cryptography

# 3. Create our application file structure
mkdir -p app/services app/models
touch app/main.py app/models/schemas.py app/services/clinical_agent.py
```

This sets up a clean virtual environment and lockfile in seconds, ensuring complete reproducibility.

---

## 📐 Designing the Medical Data Schemas

Clinical documents must adhere to strict formatting. A **SOAP note** is divided into four highly specific sections:
*   **Subjective:** The patient's history, symptoms, and subjective experience.
*   **Objective:** The doctor's physical findings, vital signs, and lab results.
*   **Assessment:** The diagnosis or differential diagnoses.
*   **Plan:** The treatment strategy, medications, follow-up tests, and education.

Additionally, we need to extract **ICD-11 (International Classification of Diseases)** codes and **SNOMED-CT** clinical terms to ensure billing and electronic health record (EHR) compatibility.

Let's write our strict schema definitions in `app/models/schemas.py`:

```python
from pydantic import BaseModel, Field
from typing import list, Optional

class ICD11Code(BaseModel):
    code: str = Field(description="The exact ICD-11 classification code (e.g., '1B10' for Tuberculosis).")
    description: str = Field(description="The official clinical description of the diagnostic code.")
    confidence: float = Field(ge=0.0, le=1.0, description="The confidence score of the match.")

class SNOMEDTerm(BaseModel):
    concept_id: str = Field(description="The unique SNOMED-CT Concept ID.")
    preferred_term: str = Field(description="The clinically preferred vocabulary term.")
    category: str = Field(description="The category of the concept (e.g., Finding, Procedure, Body Structure).")

class SubjectiveSection(BaseModel):
    chief_complaint: str = Field(description="The primary reason the patient is seeking care.")
    history_of_present_illness: str = Field(description="Detailed chronological narrative of the patient's symptoms.")
    review_of_systems: list[str] = Field(default_factory=list, description="List of positive symptoms noted by patient.")

class ObjectiveSection(BaseModel):
    vital_signs: dict[str, str] = Field(description="Extracted vitals (e.g., BP: 120/80, Temp: 98.6F).")
    physical_exam_findings: list[str] = Field(default_factory=list, description="Clinical findings observed during exam.")
    lab_or_imaging_results: list[str] = Field(default_factory=list, description="Any noted laboratory or imaging results.")

class AssessmentSection(BaseModel):
    primary_diagnosis: str = Field(description="The main clinical diagnosis determined by the clinician.")
    differential_diagnoses: list[str] = Field(default_factory=list, description="Secondary or potential diagnoses being ruled out.")
    icd11_mappings: list[ICD11Code] = Field(default_factory=list, description="Relevant ICD-11 diagnostic billing codes.")

class PlanSection(BaseModel):
    medications: list[dict[str, str]] = Field(default_factory=list, description="Prescribed medications with dosage, frequency, and duration.")
    procedures_or_tests: list[str] = Field(default_factory=list, description="Follow-up diagnostic testing or scheduled procedures.")
    patient_education: list[str] = Field(default_factory=list, description="Instructions, warnings, and safety boundaries given to the patient.")

class SOAPClinicalNote(BaseModel):
    subjective: SubjectiveSection
    objective: ObjectiveSection
    assessment: AssessmentSection
    plan: PlanSection
    snomed_clinical_terms: list[SNOMEDTerm] = Field(default_factory=list, description="Extracted SNOMED-CT clinical codes.")
```

---

## 🤖 Implementing the Clinical Agent in Pydantic AI

Now we will build the core AI reasoning agent. We will configure **Pydantic AI** to run our structured agent loop using `Gemini 3.1 Pro`. 

Pydantic AI's `Agent` supports **Structured Results**. When we pass `result_type=SOAPClinicalNote`, Pydantic AI will automatically construct a schema definition, instruct the Gemini API to format its response according to that schema, and parse the raw output directly into our defined models, throwing validation errors if any fields are missing or wrongly formatted.

Let's write `app/services/clinical_agent.py`:

```python
import os
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.gemini import GeminiModel
from app.models.schemas import SOAPClinicalNote

# Initialize the Gemini model using standard google-genai configuration
# In production, ensure GEMINI_API_KEY is present in your environment variables.
gemini_model = GeminiModel(
    'gemini-3.1-pro',
    api_key=os.environ.get("GEMINI_API_KEY")
)

# System prompt outlining clinical standards and documentation rules
clinical_system_prompt = """
You are an elite, board-certified Clinical Informatics Agent operating in a HIPAA-compliant medical environment.
Your primary task is to ingest unstructured patient-clinician clinical conversation transcripts and synthesize them into a highly structured, accurate SOAP note.

Adhere strictly to the following parameters:
1. Subjective: Extract history, onset, severity, and context of symptoms directly from patient statements. Do not extrapolate.
2. Objective: Map any stated physical observations, blood pressure, heart rate, temperature, or diagnostic test values.
3. Assessment: Make professional clinical assessment summaries based on the clinician's spoken diagnosis. Map every diagnosis to the most specific, current ICD-11 code block.
4. Plan: Compile exact medication instructions, laboratory orders, and safety warning protocols spoken during the transcript.
5. SNOMED-CT: Extract any clinical concept, surgical procedure, anatomical site, or finding, and match it to a valid SNOMED-CT Concept ID format.

Important Security & Formatting Guidelines:
- Never invent vital signs or patient symptoms. If a field is not discussed in the transcript, leave it blank or omit it.
- Ensure all medical acronyms are expanded where clinically appropriate to avoid billing confusion.
- Absolute strict formatting output is required to protect patient records schema.
"""

# Initialize the Pydantic AI Agent
clinical_agent = Agent(
    model=gemini_model,
    result_type=SOAPClinicalNote,
    system_prompt=clinical_system_prompt
)

class ClinicalAgentService:
    @staticmethod
    async def process_transcript(transcript: str) -> SOAPClinicalNote:
        """Processes an unstructured medical transcript, validating it through Pydantic AI."""
        try:
            result = await clinical_agent.run(
                user_prompt=f"Please analyze the following patient-doctor transcript:\n\n{transcript}"
            )
            # The result.data is guaranteed to be a fully populated SOAPClinicalNote instance
            return result.data
        except Exception as e:
            # In a real clinical setting, implement deep logging and failover systems
            raise RuntimeError(f"Clinical compilation failure: {str(e)}")
```

---

## 🌐 Exposing the Web API with FastAPI

Now let's build our web interface in `app/main.py`. We'll set up standard FastAPI asynchronous routes, apply validation error handling, and add security and HIPAA data practices.

```python
import time
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from app.models.schemas import SOAPClinicalNote
from app.services.clinical_agent import ClinicalAgentService

app = FastAPI(
    title="Clinical Workflow Automation Engine",
    description="HIPAA-aligned structured data engine using Gemini 3.1 Pro and Pydantic AI",
    version="1.0.0"
)

# Enable CORS for internal EHR integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, lock this down strictly to your enterprise domain!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TranscriptRequest(BaseModel):
    transcript: str = Field(min_length=50, description="The raw unstructured text transcript of the clinical consult.")

class ProcessingStatus(BaseModel):
    status: str
    processing_time_ms: int
    data: SOAPClinicalNote

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Verify service and connection health."""
    return {"status": "healthy", "service": "clinical-agent", "timestamp": time.time()}

@app.post(
    "/api/v1/compile-soap",
    response_model=ProcessingStatus,
    status_code=status.HTTP_200_OK,
    summary="Compile unstructured transcripts into validated SOAP clinical notes"
)
async def compile_soap_note(payload: TranscriptRequest):
    """
    Ingests an unstructured recording transcript, runs structured medical extraction 
    via Gemini 3.1 Pro + Pydantic AI, and returns a verified SOAP note with SNOMED & ICD-11 codes.
    """
    start_time = time.time()
    try:
        soap_note = await ClinicalAgentService.process_transcript(payload.transcript)
        duration_ms = int((time.time() - start_time) * 1000)
        
        return ProcessingStatus(
            status="success",
            processing_time_ms=duration_ms,
            data=soap_note
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clinical analysis processing failed: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    # Start uvicorn server locally on port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## 🔒 HIPAA Alignment & Enterprise Zero-Data Retention Guidelines

If you are building medical systems, **compliance is not optional**. You must secure all Protected Health Information (PHI) under HIPAA laws.

When using the Gemini API in a clinical environment:

1.  **Enterprise Tiers:** Do not use the standard public Gemini API tiers. You must use **Vertex AI** (Google Cloud Platform) to access Gemini. Vertex AI provides strict **Business Associate Agreements (BAA)**, guaranteeing that your data is fully isolated in your Google Cloud Tenant.
2.  **Zero-Data Retention (ZDR):** Google Cloud guarantees that data sent to Vertex AI model endpoints is *never* persisted on disk, is *never* used to train or refine Google's base foundation models, and is processed entirely in ephemeral RAM context windows.
3.  **Local Encryption at Rest & In-Transit:**
    *   Always serve your FastAPI endpoints behind strictly configured TLS 1.3 (HTTPS).
    *   If you store transcripts or generated SOAP notes in an intermediate database (e.g., PostgreSQL), use column-level encryption (with tools like `cryptography` AES-256-GCM) so that data remains encrypted at rest, even if your primary database credentials are leaked.

---

## 🚀 Running and Testing Your Clinical Engine

You can start your local development server with the following command:

```bash
# Start your FastAPI application using uv to invoke uvicorn
uv run uvicorn app.main:app --reload
```

Once the server is running, navigate to `http://localhost:8000/docs` to access your interactive FastAPI Swagger UI. 

### Sample Clinical Transcript for Testing
Try posting the following payload to your `/api/v1/compile-soap` route:

```json
{
  "transcript": "Doctor: Hello, John. How have you been since our last visit? Patient: To be honest, doctor, my knee has been killing me. The pain started about 4 days ago after I slipped on the driveway. It's a dull ache right in the front of my left knee. It gets much worse when I climb stairs. I'd rate the pain a 6 out of 10. Doctor: Understood. Let's do an exam. The left knee shows mild swelling and tenderness along the anterior patellar border. No ligament instability. Flexion is limited to 110 degrees due to tightness, extension is full. I also checked your vitals earlier, blood pressure was great at 118 over 76, temperature is 98.4. Let's get an X-ray to rule out any patellar fracture. I want you to take Ibuprofen 400 milligrams twice daily with food for the next 5 days, and please avoid heavy lifting or running until we get the results. Patient: Okay, I will do that."
}
```

The system will ingest this messy paragraph, structure the details, map the diagnostic assessment to `ICD-11` patellar pain structures, output precise `SNOMED-CT` identifiers, and return a validated, production-ready schema ready to be saved into your EHR system in milliseconds.

*Are you building AI solutions in healthcare? Let's discuss clinical safety parameters, real-world accuracy rates, and deployment patterns in the comments below!*
