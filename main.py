"""
main.py
-------
FastAPI backend exposing the CarbonLedger pipeline as REST endpoints.
Run with: uvicorn main:app --reload --port 8000
Docs auto-generated at: http://localhost:8000/docs
"""

import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from app.agent import CarbonLedgerAgent
from app.report_generator import generate_narrative, build_pdf_report

app = FastAPI(
    title="CarbonLedger API",
    description="AI-agent powered Scope 1/2/3 carbon accounting pipeline for ESRS E1 / CSRD-aligned reporting.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = CarbonLedgerAgent()


class ProcessTextRequest(BaseModel):
    document_text: str


class GenerateReportRequest(BaseModel):
    document_text: str
    company_name: str
    reporting_period: str


@app.get("/")
def root():
    return {
        "service": "CarbonLedger API",
        "status": "running",
        "gemini_api_configured": bool(os.environ.get("GEMINI_API_KEY")),
    }


@app.post("/process")
def process_document(req: ProcessTextRequest):
    """Run the full agent pipeline on raw document text and return the
    emissions summary + audit trail, without generating a PDF."""
    result = agent.process_document(req.document_text)
    return {
        "summary": result.emissions_report.summary(),
        "audit_trail": [vars(a) for a in result.audit_trail],
        "unmatched_items": result.unmatched_items,
    }


@app.post("/generate-report")
def generate_report(req: GenerateReportRequest):
    """Run the full pipeline AND generate a PDF report, returning the
    file path. In a real deployment this would return a signed download
    URL (e.g. S3 presigned URL) instead of a local path."""
    result = agent.process_document(req.document_text)
    summary = result.emissions_report.summary()
    narrative = generate_narrative(summary)

    output_dir = os.path.join(os.path.dirname(__file__), "data", "generated_reports")
    os.makedirs(output_dir, exist_ok=True)
    safe_name = req.company_name.replace(" ", "_")
    output_path = os.path.join(output_dir, f"{safe_name}_report.pdf")

    build_pdf_report(
        company_name=req.company_name,
        reporting_period=req.reporting_period,
        summary=summary,
        narrative=narrative,
        audit_trail_count=len(result.audit_trail),
        output_path=output_path,
    )

    return {
        "summary": summary,
        "audit_trail": [vars(a) for a in result.audit_trail],
        "report_path": output_path,
    }


@app.get("/health")
def health():
    return {"status": "ok"}
