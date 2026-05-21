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
