import os
import json
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.parser_schemas import GenericInvoiceData, DynamicInvoiceResponse
from app.parser_agent import run_generic_parser, run_query_parser

app = FastAPI(
    title="Multimodal Invoice Processing Hub",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def validate_image(file: UploadFile):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {file.content_type}. Use JPEG, PNG, or WebP."
        )


@app.post("/api/v1/parser/generic", response_model=GenericInvoiceData)
async def extract_generic_fields(file: UploadFile = File(...)):
    """Generic invoice parser: extracts standard metadata and item tables."""
    validate_image(file)
    try:
        image_bytes = await file.read()
        extracted_data = await run_generic_parser(image_bytes, file.content_type)
        return extracted_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generic extraction error: {str(e)}")


@app.post("/api/v1/parser/query", response_model=DynamicInvoiceResponse)
async def extract_custom_fields(
    file: UploadFile = File(...),
    queries: str = Form(..., description="String containing custom fields instructions")
):
    """Dynamic query parser: extracts only client-defined specific fields."""
    validate_image(file)
    try:
        image_bytes = await file.read()
        extracted_data = await run_query_parser(image_bytes, file.content_type, queries)
        return extracted_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Custom extraction error: {str(e)}")


# Serve Client Frontend Panel
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def read_root():
    return FileResponse("app/static/parser.html")
