"""Local demonstration API. Explicit input modes and UUID-based artifact downloads."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
import os
from fastapi import FastAPI, HTTPException, Path as ApiPath
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from app.agent import CarbonLedgerAgent
from app.report_generator import generate_narrative, build_pdf_report

app = FastAPI(title="CarbonLedger demonstration API", version="0.2.0")


@lru_cache(maxsize=2)
def get_agent(mode, allow_experimental_model_decisions=False):
    return CarbonLedgerAgent(
        mode=mode, allow_experimental_model_decisions=allow_experimental_model_decisions
    )


class ProcessTextRequest(BaseModel):
    document_text: str = Field(min_length=1)
    mode: Literal["structured", "live"] = "structured"
    allow_experimental_model_decisions: bool = False


class GenerateReportRequest(ProcessTextRequest):
    company_name: str = Field(min_length=1, max_length=200)
    reporting_period: str = Field(min_length=1, max_length=100)


def process(req):
    try:
        return get_agent(
            req.mode, req.allow_experimental_model_decisions
        ).process_document(req.document_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def payload(result):
    return {
        "run_id": result.run_id,
        "mode": result.mode,
        "summary": result.emissions_report.summary(),
        "audit_trail": [vars(a) for a in result.audit_trail],
        "unmatched_items": result.unmatched_items,
        "partial_result": bool(result.unmatched_items),
        "call_counts": result.call_counts,
        "experimental_model_decisions_enabled": result.experimental_decisions,
        "audit_url": f"/audit/{result.run_id}",
    }


@app.get("/")
def root():
    return {
        "service": "CarbonLedger",
        "version": "0.2.0",
        "default_mode": "structured",
        "live_configured": bool(
            os.getenv("GEMINI_API_KEY") and os.getenv("GEMINI_MODEL")
        ),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/process")
def process_document(req: ProcessTextRequest):
    return payload(process(req))


@app.post("/generate-report")
def generate_report(req: GenerateReportRequest):
    result = process(req)
    directory = Path(os.getenv("CARBONLEDGER_REPORT_DIR", "data/generated_reports"))
    path = directory / f"{result.run_id}.pdf"
    summary = result.emissions_report.summary()
    build_pdf_report(
        req.company_name,
        req.reporting_period,
        summary,
        generate_narrative(summary),
        output_path=str(path),
        audit_trail=result.audit_trail,
        run_id=result.run_id,
        mode=result.mode,
    )
    return {**payload(result), "report_url": f"/reports/{result.run_id}"}


@app.get("/reports/{run_id}")
def download_report(run_id: str = ApiPath(pattern=r"^[0-9a-f]{32}$")):
    path = (
        Path(os.getenv("CARBONLEDGER_REPORT_DIR", "data/generated_reports"))
        / f"{run_id}.pdf"
    )
    if not path.is_file():
        raise HTTPException(404, "Report not found")
    return FileResponse(
        path, media_type="application/pdf", filename=f"carbonledger-{run_id}.pdf"
    )


@app.get("/audit/{run_id}")
def download_audit(run_id: str = ApiPath(pattern=r"^[0-9a-f]{32}$")):
    path = Path(os.getenv("CARBONLEDGER_AUDIT_DIR", "data/audit")) / f"{run_id}.json"
    if not path.is_file():
        raise HTTPException(404, "Audit not found")
    return FileResponse(
        path, media_type="application/json", filename=f"audit-{run_id}.json"
    )
