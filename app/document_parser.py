"""
document_parser.py
-------------------
Uses the Google Gemini API to extract structured activity data (quantities,
units, dates, line-item descriptions) from unstructured documents —
electricity bills, fuel receipts, freight invoices, supplier statements.

Why Gemini here: this is the "messy real world data in, structured data
out" layer. Invoices vary wildly in format (no two suppliers use the same
template), which is exactly the kind of unstructured extraction task that
breaks rule-based parsers (regex/templates) but LLMs handle robustly via
few-shot structured prompting. Gemini's free tier (Gemini 2.5 Flash) makes
this viable at zero cost for a student/portfolio project.

Requires GEMINI_API_KEY environment variable (get one free at
https://aistudio.google.com/apikey). If not set, falls back to a
clearly-labeled mock extractor so the rest of the pipeline remains
demoable without API credentials.
"""

import os
import json
from typing import List, Dict

try:
    from google import genai
    _HAS_GENAI = True
except ImportError:
    _HAS_GENAI = False

MODEL="gemini-3.6-flash"

EXTRACTION_SYSTEM_PROMPT = """You are a document extraction engine for a carbon
accounting platform. Given raw text from an invoice, bill, or receipt, extract
every line item that represents an activity with carbon emissions relevance
(fuel purchases, electricity consumption, freight/logistics, raw material
purchases, waste disposal, water usage, travel).

Return ONLY a JSON array, no other text, with this exact structure:
[
  {
    "description": "<short description of the line item as written>",
    "quantity": <number>,
    "unit": "<unit as found in document, e.g. litre, kWh, kg, km, m3>",
    "source_label": "<document reference, e.g. invoice number or date if visible>"
  }
]

If a document has no relevant line items, return an empty array [].
Do not invent data that is not present in the text."""


def _mock_extract(raw_text: str) -> List[Dict]:
    """Fallback used when no GEMINI_API_KEY is configured, so the full
    pipeline can still be demoed end-to-end without live API credentials."""
    return [
        {
            "description": "[MOCK - no API key set] Sample diesel generator fuel line item",
            "quantity": 450.0,
            "unit": "litre",
            "source_label": "mock_extraction_no_api_key",
        }
    ]


def _get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not _HAS_GENAI or not api_key:
        return None
    return genai.Client(api_key=api_key)


def extract_activity_data(raw_text: str) -> List[Dict]:
    """Takes raw extracted text from a PDF/document and returns a list of
    structured line items. Caller is responsible for OCR/PDF-to-text if the
    source is a scanned image or PDF (see notes in README for pdfplumber/
    pytesseract integration)."""

    client = _get_client()
    if client is None:
        return _mock_extract(raw_text)

    response = client.models.generate_content(
        model=MODEL,
        contents=raw_text,
        config={
            "system_instruction": EXTRACTION_SYSTEM_PROMPT,
            "response_mime_type": "application/json",
            "temperature": 0.1,
        },
    )

    text_out = (response.text or "").strip()
    if text_out.startswith("```"):
        text_out = text_out.strip("`")
        text_out = text_out.replace("json\n", "", 1).strip()

    try:
        return json.loads(text_out)
    except json.JSONDecodeError:
        # In production: log this for human review rather than silently failing
        return []


if __name__ == "__main__":
    sample_invoice_text = """
    ACME POWER DISTRIBUTION COMPANY
    Invoice #INV-2026-3381
    Billing period: March 2026
    Industrial Connection - Plant A
    Units consumed: 84,000 kWh
    Amount due: Rs. 6,72,000

    ---
    Separate document: Diesel fuel receipt
    Date: 12 March 2026
    Generator backup fuel: 1,200 litres diesel
    Vendor: Bharat Petroleum
    """
    result = extract_activity_data(sample_invoice_text)
    print(json.dumps(result, indent=2))
