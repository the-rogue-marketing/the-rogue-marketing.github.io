---
layout: post
title: "AI System Design Series (Part 2): Domain Ontologies and Common Data Models with PEPPOL, HL7 FHIR, and Pydantic"
description: "Why raw JSON extraction fails in enterprise production. How to architect canonical Common Data Models (CDMs) and semantic ontologies using Pydantic, PEPPOL BIS 3.0 for invoices, and HL7 FHIR for healthcare RCM."
author: professor-xai
categories: [system-design, data-modeling, python, pydantic]
image: assets/images/ai-system-design-part-2-ontologies.webp
featured: true
last_modified_at: 2026-10-10
keywords: "common data model ai, domain ontologies software engineering, peppol ubl pydantic, hl7 fhir claim python, enterprise data architecture, pydantic field validators"
faq:
  - question: "Why is a Common Data Model required between LLM outputs and enterprise databases?"
    answer: "LLMs generate arbitrary JSON structures that fluctuate across prompts, model updates, and document layouts. Downstream enterprise systems like SAP, NetSuite, Epic, and Cerner require strict relational schemas with precise business invariants. A Common Data Model serves as the stable, canonical contract decoupling volatile AI extraction from rigid core ledgers."
  - question: "What is the PEPPOL standard for electronic invoicing?"
    answer: "PEPPOL (Pan-European Public Procurement On-Line) is an international standard based on Universal Business Language (UBL). It specifies mandatory semantic fields, tax subtotal calculations, country-specific VAT categorizations, and legal entity identifiers required for automated cross-border accounting."
  - question: "How does HL7 FHIR represent healthcare billing claims?"
    answer: "HL7 FHIR uses standardized resource structures such as Claim, Encounter, Patient, Coverage, and Practitioner. Each resource connects via standardized RESTful references and enforces formal coding ontologies like ICD-10-CM for diagnoses and CPT/HCPCS for medical procedures."
---

In the first part of this series, we designed the distributed ingestion layer: using Kafka to buffer incoming documents, Redis for SHA-256 idempotency locks, and Gemini 3.8 Flash to extract structured JSON from raw scans in under a second.

However, once you have extracted JSON from an LLM, a dangerous trap awaits.

Many teams take the JSON payload returned by an extraction model and write it straight into an application database. In a toy project, this appears to work. In an enterprise system processing millions of dollars in financial transactions or clinical claims, this practice is disastrous.

Every vendor formats their documents differently. One vendor calls a field `invoice_id`, another calls it `bill_no`, and a third calls it `reference`. In healthcare, one clinic sends a diagnosis as `diabetes_type_2`, while another provides the exact ICD-10 code `E11.9`.

If your downstream services consume arbitrary, ad-hoc JSON structures directly from an LLM, your application will quickly accumulate hundreds of brittle conditional statements. A single change in prompt formatting or an unexpected layout will corrupt financial ledgers and trigger insurance claim rejections.

To build software that endures, you must introduce a formal Common Data Model (CDM) and domain ontology.

In this second installment of our AI System Design Series, we build the semantic foundation that bridges raw multimodal LLM extraction with enterprise record-keeping:

1. Canonical Data Modeling: Why semantic normalization must precede data lake persistence.
2. Domain 1 (Accounts Payable): Implementing PEPPOL BIS Billing 3.0 and Universal Business Language (UBL 2.1) structures using Pydantic.
3. Domain 2 (Healthcare RCM): Standardizing clinical billing claims into HL7 FHIR Claim resources with ICD-10-CM and CPT/HCPCS ontological validation.
4. Deterministic Invariant Enforcement: Writing Pydantic validators that catch calculation mismatches and medical policy violations before any data enters downstream databases.

## The Theory of the Common Data Model

A Common Data Model is a standardized, technology-agnostic data schema that represents core business entities within an organization. It establishes a canonical language that all internal microservices agree upon.

Instead of building point-to-point transformations between every incoming document format and every internal database, the CDM establishes an N-to-1-to-M architecture:

Any incoming format (PDF, scanned receipt, EDI 837, PEPPOL XML) is mapped by your extraction agents into the Common Data Model (the single canonical truth).

All downstream systems (ERP ledgers, data lakes, fraud detection engines, vector search indexes) consume exclusively from the Common Data Model.

This architectural separation delivers three critical benefits:

First, complete vendor and model agnosticism. If you switch from Gemini 3.8 Flash to an open-source model like Qwen or DeepSeek in six months, your downstream microservices remain completely unaffected because the CDM contract never changes.

Second, compile-time and runtime type safety. By enforcing strict schemas at the entry point of your domain, bad data is rejected or flagged immediately, rather than silently corrupting analytical tables.

Third, programmatic auditability. Regulators and financial auditors do not want to inspect unstructured JSON blobs. They require standardized entities conforming to statutory guidelines.

## Domain 1: Accounts Payable Invoices (PEPPOL BIS Billing 3.0)

In international corporate finance, the dominant standard for automated electronic invoicing is PEPPOL BIS Billing 3.0, built on Universal Business Language (UBL).

A valid invoice is not merely a collection of text labels. It is governed by rigorous financial invariants:
- The sum of all line item net amounts must equal the document line extension amount.
- Each line item must be associated with a specific tax category code (e.g., standard rate, zero-rated, exempt).
- Tax subtotals must be grouped by tax category and rate, and the sum of tax subtotals must equal the document total tax amount.
- The payable amount must strictly equal: line extension amount minus allowances plus charges plus total tax amount.

Let us build this model in Python using Pydantic:

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

class TaxCategoryCode(str, Enum):
    STANDARD = "S"          # Standard rate
    ZERO_RATED = "Z"        # Zero rated goods
    EXEMPT = "E"            # Exempt from tax
    REVERSE_CHARGE = "AE"   # VAT Reverse charge

class CanonicalInvoiceLine(BaseModel):
    line_id: str
    item_name: str
    item_description: Optional[str] = None
    invoiced_quantity: Decimal = Field(..., gt=0)
    unit_code: str = Field(default="C62", description="UN/ECE Recommendation 20, e.g. C62 for unit/piece")
    price_amount: Decimal = Field(..., ge=0)
    line_extension_amount: Decimal = Field(..., description="Quantity * Price minus line discounts")
    tax_category: TaxCategoryCode
    tax_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)

    @model_validator(mode="after")
    def verify_line_math(self) -> "CanonicalInvoiceLine":
        calculated_extension = (self.invoiced_quantity * self.price_amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if abs(calculated_extension - self.line_extension_amount) > Decimal("0.05"):
            raise ValueError(
                f"Line math mismatch on line {self.line_id}: "
                f"quantity ({self.invoiced_quantity}) * price ({self.price_amount}) = {calculated_extension}, "
                f"but extracted line_extension_amount was {self.line_extension_amount}"
            )
        return self

class CanonicalTaxSubtotal(BaseModel):
    taxable_amount: Decimal
    tax_amount: Decimal
    category: TaxCategoryCode
    percent: Decimal

class CanonicalInvoice(BaseModel):
    specification_identifier: str = Field(
        default="urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0"
    )
    invoice_number: str
    issue_date: str = Field(description="YYYY-MM-DD")
    due_date: Optional[str] = None
    invoice_currency: str = Field(default="USD", min_length=3, max_length=3)
    
    # Legal Entities
    supplier_legal_name: str
    supplier_tax_identifier: str
    customer_legal_name: str
    customer_tax_identifier: Optional[str] = None
    
    # Financial Totals
    line_items: List[CanonicalInvoiceLine] = Field(..., min_items=1)
    tax_subtotals: List[CanonicalTaxSubtotal] = Field(..., min_items=1)
    
    sum_of_lines_amount: Decimal
    tax_exclusive_amount: Decimal
    tax_inclusive_amount: Decimal
    payable_amount: Decimal

    @model_validator(mode="after")
    def verify_peppol_financial_invariants(self) -> "CanonicalInvoice":
        # 1. Verify sum of lines equals sum_of_lines_amount
        calculated_lines_sum = sum(line.line_extension_amount for line in self.line_items)
        if abs(calculated_lines_sum - self.sum_of_lines_amount) > Decimal("0.05"):
            raise ValueError(
                f"PEPPOL Violation: sum of line extensions ({calculated_lines_sum}) "
                f"does not match sum_of_lines_amount ({self.sum_of_lines_amount})"
            )

        # 2. Verify tax calculation
        total_calculated_tax = sum(sub.tax_amount for sub in self.tax_subtotals)
        expected_inclusive = self.tax_exclusive_amount + total_calculated_tax
        if abs(expected_inclusive - self.tax_inclusive_amount) > Decimal("0.05"):
            raise ValueError(
                f"PEPPOL Violation: tax_exclusive ({self.tax_exclusive_amount}) + "
                f"tax ({total_calculated_tax}) != tax_inclusive ({self.tax_inclusive_amount})"
            )

        # 3. Verify final payable amount
        if abs(self.tax_inclusive_amount - self.payable_amount) > Decimal("0.05"):
            raise ValueError(
                f"Payable amount mismatch: tax_inclusive is {self.tax_inclusive_amount}, "
                f"but payable_amount is {self.payable_amount}"
            )

        return self
```

Notice what we have achieved: If an LLM misreads a number or hallucinates a line item total, this Pydantic model immediately intercepts the error with exact mathematical feedback before the record can touch our ERP.

## Domain 2: Healthcare RCM Claims (HL7 FHIR & Ontologies)

Healthcare revenue cycle management is governed by strict formal ontologies:
- ICD-10-CM: International Classification of Diseases, 10th Revision, Clinical Modification (used for diagnoses, e.g., `I10` for Essential Hypertension).
- CPT: Current Procedural Terminology (5-digit numeric codes maintained by the AMA for physician services).
- HCPCS: Healthcare Common Procedure Coding System (alphanumeric codes for supplies, ambulance, medications).
- HL7 FHIR: Fast Healthcare Interoperability Resources (the global modern standard for health data exchange).

A healthcare claim cannot simply state *"the patient received an injection."* It must specify:
1. The exact CPT procedure code.
2. The supporting ICD-10 diagnosis code that establishes medical necessity.
3. The National Provider Identifier (NPI) of the performing clinician (verified via Luhn-algorithm checksum).
4. Billing modifiers (e.g., Modifier 25 indicating a significant, separately identifiable evaluation and management service).

Let us build the canonical FHIR-aligned Claim model:

```python
import re
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from decimal import Decimal
from enum import Enum

class FHIRClaimUse(str, Enum):
    CLAIM = "claim"
    PREAUTHORIZATION = "preauthorization"
    PREDETERMINATION = "predetermination"

class DiagnosisType(str, Enum):
    ADMITTING = "admitting"
    PRINCIPAL = "principal"
    SECONDARY = "secondary"

class FHIRDiagnosis(BaseModel):
    sequence: int = Field(..., ge=1, le=12)
    icd10_code: str = Field(description="ICD-10-CM code without punctuation, e.g. E119")
    diagnosis_type: DiagnosisType

    @field_validator("icd10_code")
    def validate_icd10_syntax(cls, v: str) -> str:
        clean = v.replace(".", "").strip().upper()
        # ICD-10 standard pattern: Letter followed by 2 digits, then up to 4 alphanumeric characters
        if not re.match(r"^[A-Z][0-9]{2}[A-Z0-9]{0,4}$", clean):
            raise ValueError(f"Invalid ICD-10-CM diagnostic syntax: '{v}'")
        return clean

class FHIRItem(BaseModel):
    sequence: int = Field(..., ge=1)
    procedure_code: str = Field(description="5-digit CPT or alphanumeric HCPCS code")
    modifier_codes: List[str] = Field(default_factory=list, max_items=4)
    diagnosis_sequence_references: List[int] = Field(..., min_items=1)
    service_date: str = Field(description="YYYY-MM-DD")
    unit_quantity: int = Field(default=1, gt=0)
    unit_price: Decimal = Field(..., ge=0)
    net_charge: Decimal = Field(..., ge=0)

    @field_validator("procedure_code")
    def validate_procedure_syntax(cls, v: str) -> str:
        clean = v.strip().upper()
        # CPT (5 digits) or HCPCS (1 letter + 4 digits)
        if not re.match(r"^([0-9]{5}|[A-V][0-9]{4})$", clean):
            raise ValueError(f"Invalid CPT/HCPCS procedure code syntax: '{v}'")
        return clean

class CanonicalFHIRClaim(BaseModel):
    resource_type: str = Field(default="Claim")
    claim_id: str
    use: FHIRClaimUse = Field(default=FHIRClaimUse.CLAIM)
    status: str = Field(default="active")
    
    patient_identifier: str
    billing_provider_npi: str = Field(min_length=10, max_length=10)
    rendering_provider_npi: Optional[str] = Field(None, min_length=10, max_length=10)
    
    payer_identifier: str
    payer_name: str
    
    diagnoses: List[FHIRDiagnosis] = Field(..., min_items=1)
    items: List[FHIRItem] = Field(..., min_items=1)
    total_claim_amount: Decimal

    @field_validator("billing_provider_npi", "rendering_provider_npi")
    def validate_npi_luhn(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not v.isdigit() or len(v) != 10:
            raise ValueError(f"NPI must be exactly 10 digits, got '{v}'")
        
        # Verify US CMS NPI Luhn Checksum with prefix 80840
        full_string = "80840" + v
        digits = [int(d) for d in full_string]
        odd_sum = sum(digits[-1::-2])
        even_doubled = [d * 2 for d in digits[-2::-2]]
        even_sum = sum(d - 9 if d > 9 else d for d in even_doubled)
        if (odd_sum + even_sum) % 10 != 0:
            raise ValueError(f"National Provider Identifier (NPI) failed Luhn checksum: '{v}'")
        return v
```

With this model in place, any hallucinated or malformed NPI provider number is caught instantly by the Luhn algorithm before the claim is submitted to an insurance clearinghouse like Change Healthcare or Availity.

## Building the Transformation Layer

Now, how do we bridge the raw Gemini 3.8 Flash extraction we built in Part 1 to these canonical Common Data Models?

We implement a dedicated, idempotent Translation Service:

```python
from decimal import Decimal

class InvoiceNormalizationService:
    @staticmethod
    def map_to_peppol(raw: dict) -> CanonicalInvoice:
        """
        Transforms raw LLM JSON extraction into a fully validated
        Canonical PEPPOL BIS Billing 3.0 invoice entity.
        """
        lines = []
        for idx, item in enumerate(raw.get("line_items", []), start=1):
            qty = Decimal(str(item.get("quantity", 1)))
            price = Decimal(str(item.get("unit_price", 0)))
            extension = Decimal(str(item.get("line_total", qty * price)))
            
            lines.append(CanonicalInvoiceLine(
                line_id=str(idx),
                item_name=item.get("description", "Unknown Item"),
                invoiced_quantity=qty,
                price_amount=price,
                line_extension_amount=extension,
                tax_category=TaxCategoryCode.STANDARD,
                tax_percent=Decimal(str(item.get("tax_rate_percent", 0.0)))
            ))
            
        tax_amount = Decimal(str(raw.get("tax_amount", 0)))
        subtotal = Decimal(str(raw.get("subtotal_amount", 0)))
        total = Decimal(str(raw.get("total_amount", subtotal + tax_amount)))

        subtotals = [
            CanonicalTaxSubtotal(
                taxable_amount=subtotal,
                tax_amount=tax_amount,
                category=TaxCategoryCode.STANDARD,
                percent=Decimal("0.00") if subtotal == 0 else ((tax_amount / subtotal) * 100).quantize(Decimal("0.01"))
            )
        ]

        return CanonicalInvoice(
            invoice_number=raw.get("invoice_number", "UNKNOWN"),
            issue_date=raw.get("invoice_date", "2026-01-01"),
            due_date=raw.get("due_date"),
            invoice_currency=raw.get("currency", "USD"),
            supplier_legal_name=raw.get("vendor_name", "Unknown Supplier"),
            supplier_tax_identifier=raw.get("vendor_tax_id", "NOT_PROVIDED"),
            customer_legal_name=raw.get("customer_name", "Enterprise Customer"),
            line_items=lines,
            tax_subtotals=subtotals,
            sum_of_lines_amount=subtotal,
            tax_exclusive_amount=subtotal,
            tax_inclusive_amount=total,
            payable_amount=total
        )
```

## Summary and What Comes Next

In this second installment, we established the semantic and ontological bedrock of our autonomous system:
- Demonstrated why raw JSON strings must never be passed directly to core business ledgers.
- Implemented the PEPPOL BIS Billing 3.0 canonical invoice schema with strict line-item and tax balance invariants.
- Modeled the HL7 FHIR Claim resource with ICD-10 diagnostic syntax checks and Luhn-validated 10-digit NPI provider algorithms.
- Built a deterministic mapping layer that converts raw LLM vision extractions into type-safe business entities.

Now that we have clean, canonical data models, where should they live? In production, you cannot dump millions of historical records directly into operational Postgres tables without degrading performance. You need a scalable lakehouse architecture.

In Part 3 of this series, we will build the Medallion Data Lakehouse: structuring Bronze, Silver, and Gold layers with Apache Iceberg, and orchestrating deterministic state synchronization using Temporal DAG workflows.
