from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class DocumentType(str, Enum):
    PASSPORT = "passport"
    LICENSE = "driver_license"
    UNKNOWN = "unknown"


# Structured extraction schema for Passports
class PassportDetails(BaseModel):
    passport_number: str = Field(..., description="Unique passport identifier")
    given_names: str = Field(..., description="First and middle names")
    surname: str = Field(..., description="Last name or family name")
    date_of_birth: str = Field(..., description="Birthdate formatted as YYYY-MM-DD")
    nationality: str = Field(..., description="Country of citizenship")
    expiry_date: str = Field(..., description="Expiration date formatted as YYYY-MM-DD")
    mrz_code: Optional[str] = Field(None, description="Machine-readable zone text at bottom")


# Structured extraction schema for Driver's Licenses
class LicenseDetails(BaseModel):
    license_number: str = Field(..., description="Unique license identifier")
    full_name: str = Field(..., description="Full name of licensee")
    date_of_birth: str = Field(..., description="Birthdate formatted as YYYY-MM-DD")
    expiry_date: str = Field(..., description="Expiration date formatted as YYYY-MM-DD")
    license_class: Optional[str] = Field(None, description="Class of vehicles permitted (e.g. 'Class C')")
    address: Optional[str] = Field(None, description="Physical address listed on license")


# The shared state dictionary representing LangGraph transactional context
class KYCState(BaseModel):
    image_bytes: bytes = Field(..., description="Uploaded raw document image")
    media_type: str = Field(..., description="MIME type of the image")
    document_type: DocumentType = DocumentType.UNKNOWN
    passport_data: Optional[PassportDetails] = None
    license_data: Optional[LicenseDetails] = None
    is_valid: bool = False
    validation_errors: List[str] = Field(default_factory=list)
