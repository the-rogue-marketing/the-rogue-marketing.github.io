---
layout: post
title: "Agentic Financial Compliance: SEC Filing Audits with Gemini 3.1 Pro, Pydantic AI, and FastAPI"
description: "A comprehensive developer guide to building automated fintech compliance auditing engines and SEC filing parsers using Gemini 3.1 Pro, Pydantic AI, and FastAPI."
author: professor-xai
categories: [ai-api, fintech, pydantic-ai, fastapi]
image: assets/images/gemini-api-usecases.png
featured: true
last_modified_at: 2026-05-21
keywords: "fintech ai compliance agent, pydantic ai fintech tutorial, sec filings analysis gemini api, automated credit risk llm, fastapi fintech microservices"
---

In the financial technology sector, compliance is a multi-billion dollar bottleneck. Financial institutions are required to continuously scan thousands of pages of complex documents—including SEC Form 10-K filings, Know Your Customer (KYC) records, internal audits, and credit risk histories—to identify regulatory breaches, operational vulnerabilities, and liability disclosures.

Performing these checks manually is slow and prone to human oversight. In **May 2026**, the standard architectural pattern for solving this is building **Agentic Compliance Audits**. By using Gemini 3.1 Pro's long context window (1M+ tokens) alongside **Pydantic AI** (Pydantic's official agent framework) and **FastAPI**, we can build type-safe, self-correcting agents that parse dense corporate filings and output strictly validated, risk-assessed compliance models.

In this guide, we will write a production-grade, end-to-end agentic audit system. We will configure a high-performance Python runtime with **uv**, build a multi-agent auditing loop using Pydantic AI's advanced dependency injection (`deps_type`), and serve our risk pipeline asynchronously using **FastAPI**.

---

## 🏗️ Bootstrapping the Fintech Service with `uv`

First, let's set up our virtual environment and package dependencies using Astrid's ultra-fast package manager, `uv`. 

Execute these commands in your shell:

```bash
# 1. Initialize a new project directory
uv init fintech-audit-agent
cd fintech-audit-agent

# 2. Add high-performance production dependencies
uv add fastapi uvicorn pydantic-ai google-genai sqlalchemy sqlite3

# 3. Establish our project structure
mkdir -p app/services app/models app/db
touch app/main.py app/models/schemas.py app/services/compliance_agent.py app/db/database.py
```

This guarantees an isolated, lightning-fast execution environment with strict version locking.

---

## 📊 Designing the Financial Audit Schemas

To pass regulatory scrutiny, a financial compliance audit must provide more than a simple "pass/fail" rating. It must detail:
1.  **Risk Profile:** Exact numerical risk assessment (0.0 to 1.0) and regulatory confidence scores.
2.  **Identified Violations:** Cross-references to specific regulatory acts (e.g., Sarbanes-Oxley, Dodd-Frank, SEC Rule 10b-5).
3.  **Audit Trail/Explainability:** The exact textual excerpts that triggered the flag, and the reasoning behind it.

Let's model these parameters inside `app/models/schemas.py`:

```python
from pydantic import BaseModel, Field
from typing import list, Optional

class RegulatoryFlag(BaseModel):
    category: str = Field(description="The category of risk (e.g., Insider Trading, Material Misstatement, Inadequate Liquidity).")
    severity: str = Field(description="Severity classification: LOW, MEDIUM, HIGH, CRITICAL.")
    governing_regulation: str = Field(description="The specific regulation or act violated (e.g., SOX Section 404).")
    supporting_quote: str = Field(description="The exact text snippet extracted from the filing as proof.")
    analytical_reasoning: str = Field(description="Detailed logic explaining why this snippet constitutes a compliance risk.")

class LiabilityExposure(BaseModel):
    item_description: str = Field(description="The specific commercial or regulatory liability identified.")
    estimated_impact_usd: Optional[float] = Field(None, description="The estimated financial impact, if quantifiable.")
    mitigation_strategy: str = Field(description="The proposed corporate strategy to mitigate this exposure.")

class ComplianceAuditReport(BaseModel):
    company_name: str = Field(description="The official name of the corporation being audited.")
    filing_type: str = Field(description="The type of document parsed (e.g., Form 10-K, Form 10-Q).")
    fiscal_period: str = Field(description="The fiscal year or quarter (e.g., FY2025).")
    overall_risk_score: float = Field(ge=0.0, le=1.0, description="Comprehensive risk score where 1.0 represents critical default risk.")
    regulatory_flags: list[RegulatoryFlag] = Field(default_factory=list, description="List of specific regulatory violations identified.")
    liability_exposures: list[LiabilityExposure] = Field(default_factory=list, description="Potential legal and financial liabilities.")
    approved_for_trading: bool = Field(description="Boolean indicator showing if the compliance profile allows investment approval.")
```

---

## 🤖 Building the Audit Agent with Pydantic AI Dependency Injection

A production-grade agent cannot run in isolation. It needs to read data from local relational databases, check current stock prices, and verify internal regulatory databases.

**Pydantic AI** handles this cleanly via **Dependency Injection (`deps_type`)**. When initializing an agent, you define a type-safe dependency class. Pydantic AI will pass this runtime context safely into your agent's system prompts, tools, and processing loops, ensuring your API key sessions or SQLite database connections are managed safely.

Let's write our secure audit database wrapper and our Pydantic AI agent in `app/services/compliance_agent.py`:

```python
import os
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.gemini import GeminiModel
from app.models.schemas import ComplianceAuditReport

# Define a safe dependency class containing database session context
@dataclass
class AuditDependencies:
    db_session: any  # In production, pass an active SQLAlchemy session
    market_feed_client: any  # Active client for checking real-time asset pricing

# Initialize the Gemini Model using standard google-genai configurations
gemini_model = GeminiModel(
    'gemini-3.1-pro',
    api_key=os.environ.get("GEMINI_API_KEY")
)

# System prompt specifying auditing protocols and logical deduction limits
compliance_system_prompt = """
You are an expert, SEC-certified compliance auditor. Your role is to perform exhaustive, data-driven audits of corporate financial filings.
You have direct access to internal company databases and market tickers via your active context dependencies and tools.

Adhere to the following clinical compliance rules:
1. Strict Analysis: Treat all financial metrics as unverified until cross-referenced with your DB records.
2. Flag Aggregation: Document every single warning sign of material misstatement, liquidity strain, or undisclosed legal risks.
3. Verification: Use the 'verify_asset_liquidity' tool before assessing if a company is 'approved_for_trading'.
4. Structure: Output your complete finding strictly in the parsed model format. Do not include loose, unformatted commentary.
"""

# Initialize the Pydantic AI Agent with Dependency Injection and Structured Outputs
compliance_agent = Agent(
    model=gemini_model,
    deps_type=AuditDependencies,
    result_type=ComplianceAuditReport,
    system_prompt=compliance_system_prompt
)

# Define a tool that the Agent can call to perform live validation
@compliance_agent.tool
def verify_asset_liquidity(ctx: RunContext[AuditDependencies], ticker: str) -> str:
    """Queries active market feed to check live capital reserves and stock trading status."""
    # We access the injected dependency class attributes directly
    client = ctx.deps.market_feed_client
    # Simulate a highly optimized internal pipeline call
    return f"Ticker: {ticker} | Live Volume: 15.4M shares | Volatility Index: Stable | Cash Reserves: $1.2B"

class ComplianceAgentService:
    @staticmethod
    async def run_audit(filing_text: str, db_session: any, feed_client: any) -> ComplianceAuditReport:
        """Runs the compliance agent loop with active runtime dependency injection."""
        # Wrap our dependencies securely
        deps = AuditDependencies(db_session=db_session, market_feed_client=feed_client)
        
        try:
            # Execute the agent loop. Pydantic AI handles structural serialization under the hood.
            result = await compliance_agent.run(
                user_prompt=f"Perform a full compliance audit on the following financial document:\n\n{filing_text}",
                deps=deps
            )
            return result.data
        except Exception as e:
            raise RuntimeError(f"Agentic compliance audit failed: {str(e)}")
```

---

## 🌐 Serving the Financial Audit Pipeline with FastAPI

Now let's build our async API layer in `app/main.py`. This route receives the filing text, sets up mock dependency clients (simulating our databases), routes the execution to our Pydantic AI agent, and returns the strictly validated, audit-logged report.

```python
import time
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from app.models.schemas import ComplianceAuditReport
from app.services.compliance_agent import ComplianceAgentService

app = FastAPI(
    title="Agentic Fintech Compliance Engine",
    description="Asynchronous compliance auditing API using Gemini 3.1 Pro, Pydantic AI, and FastAPI",
    version="1.0.0"
)

# Enable CORS for enterprise internal dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your internal VPC origins!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AuditRequest(BaseModel):
    filing_text: str = Field(min_length=100, description="The full-text payload of the corporate financial document.")

class AuditResponse(BaseModel):
    audit_id: str
    processed_at: float
    time_taken_ms: int
    report: ComplianceAuditReport

# Simulated database and feed clients for showcase purposes
class MockDBSession:
    pass

class MockMarketFeedClient:
    pass

@app.get("/health", status_code=status.HTTP_200_OK)
async def check_health():
    """Verify service uptime and agent connectivity."""
    return {"status": "operational", "timestamp": time.time()}

@app.post(
    "/api/v1/audit-filing",
    response_model=AuditResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a validated Compliance Audit Report from corporate filings"
)
async def audit_corporate_filing(payload: AuditRequest):
    """
    Asynchronously ingest raw corporate text filings, execute the Pydantic AI agentic loop 
    with SQLite DB and Market Feed dependencies, and return a validated ComplianceAuditReport.
    """
    start_time = time.time()
    
    # Initialize our database and market clients
    mock_db = MockDBSession()
    mock_feed = MockMarketFeedClient()
    
    try:
        # Pass the text to our compliance service
        audit_report = await ComplianceAgentService.run_audit(
            filing_text=payload.filing_text,
            db_session=mock_db,
            feed_client=mock_feed
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        unique_audit_id = f"aud_{int(time.time())}"
        
        return AuditResponse(
            audit_id=unique_audit_id,
            processed_at=time.time(),
            time_taken_ms=duration_ms,
            report=audit_report
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compliance processing loop aborted: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    # Local development uvicorn runner
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## 🔒 Production Hardening & Regulatory Data isolation

Deploying LLMs into financial infrastructures requires high security:

1.  **VPC Enclaves:** Run your FastAPI microservice entirely within isolated networks (e.g. AWS VPC, GCP VPC Service Controls). The service should communicate with Vertex AI endpoints using private IP routing (Private Service Connect), ensuring zero exposure to the public internet.
2.  **Audit Trail Logging:** Store every single agent tool call, input prompt, and intermediate output in a write-once-read-many (WORM) database. This guarantees a complete audit log, critical when internal compliance decisions are challenged by regulatory commissions.
3.  **Handling Token Overflow on Large Filings:** SEC 10-K filings can span 200,000+ words (nearly 300K tokens). Ensure your system utilizes **Gemini 3.1 Pro's Prompt Caching** to cache the baseline filing text, saving up to 90% in cost when multiple separate compliance agents (e.g. tax, operations, insider-trading) scan the same document simultaneously.

---

## 🚀 Validating and Testing the Fintech Pipeline

Run your financial compliance server locally:

```bash
# Execute your API using uv environment virtualization
uv run uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` to test the API with your custom financial files.

### Sandbox Testing Input
Post this text payload to the `/api/v1/audit-filing` route:

```json
{
  "filing_text": "SEC FORM 10-K. ACME INDUSTRIES CO. FISCAL YEAR ENDED DECEMBER 31, 2025. Item 1A. Risk Factors. We face intense market competition. Additionally, we are currently under active investigation by the Securities and Exchange Commission (SEC) regarding certain stock options grants issued to our executive leadership team in early 2024. While we believe our compensation policies are compliant, an adverse finding could lead to material fines and restitution demands. Cash and cash equivalents decreased by 42% to $120M in FY2025 compared to $206M in FY2024, primarily driven by our patellar-design tooling acquisitions. We have mapped ticker ACMI to verify current operations. Item 3. Legal Proceedings. On March 14, 2025, a class-action lawsuit was filed against us in the Delaware Court of Chancery alleging breach of fiduciary duty by our directors in connection with the patellar tooling acquisitions. The plaintiffs seek damages of $45 million."
}
```

The system will parse the messy SEC text, identify both the class-action lawsuit and the active SEC option-grant investigation, generate precise regulatory flags (SOX breach risks), run the internal `verify_asset_liquidity` tool on the company's ticker to verify financial reserves, and return a clean, fully validated, structures-matching compliance JSON report.

*Are you building autonomous audit engines? What methods are you using to validate risk models and prevent hallucinated violations? Let’s talk in the comments below!*
