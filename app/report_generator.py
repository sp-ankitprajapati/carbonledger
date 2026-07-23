"""
report_generator.py
--------------------
Generates a CSRD/ESRS E1 - structured PDF report.

Numbers come exclusively from the deterministic calculator (calculator.py)
— never from the LLM. The LLM (Gemini) is used only to write the narrative/
prose sections (climate context, methodology note, scope 3 commentary),
grounded by passing it the already-computed numbers as context. This
"numbers are computed, then narrated" separation is the same pattern real
compliance/fintech products use to keep LLMs out of the numerical
correctness path while still using them for the genuinely hard NLP task
of producing readable, well-structured prose.

Uses Google Gemini (free tier). Get a free API key at
https://aistudio.google.com/apikey and set it as GEMINI_API_KEY.
"""

import os
import json
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

try:
    from google import genai
    _HAS_GENAI = True
except ImportError:
    _HAS_GENAI = False

MODEL = "gemini-3.6-flash"

NARRATIVE_SYSTEM_PROMPT = """You are writing the narrative sections of a
CSRD/ESRS E1 climate disclosure report for a mid-size company. You will be
given the company's computed emissions figures. Write three short sections:

1. "Methodology Note" (2-3 sentences): how emissions were calculated
   (GHG Protocol Corporate Standard, activity-based method, India/EU grid
   factors as applicable).
2. "Emissions Summary Narrative" (3-4 sentences): plain-language summary
   of the scope 1/2/3 split and what it indicates about the company's
   emissions profile.
3. "Scope 3 Commentary" (2-3 sentences): note on why Scope 3 typically
   dominates supply-chain-heavy businesses and what data quality caveats
   apply.

Be factual, conservative, and avoid making compliance claims the company
hasn't verified (e.g. do not claim "fully CSRD compliant" — say "prepared
in alignment with ESRS E1 structure" instead, since formal compliance
requires external assurance this draft has not undergone).

Return ONLY valid JSON: {"methodology_note": "...", "emissions_narrative": "...", "scope3_commentary": "..."}"""


def _mock_narrative(summary: dict) -> dict:
    return {
        "methodology_note": (
            "[MOCK - no API key set] Emissions were calculated using the "
            "activity-based method under the GHG Protocol Corporate Standard, "
            "applying India grid and standard combustion emission factors to "
            "metered/invoiced activity data."
        ),
        "emissions_narrative": (
            f"[MOCK] Total emissions for the reporting period were "
            f"{summary['total_tco2e']} tCO2e, with Scope 3 representing "
            f"{summary['scope_3_share_pct']}% of the total footprint."
        ),
        "scope3_commentary": (
            "[MOCK] Scope 3 emissions typically dominate the footprint of "
            "manufacturing and export-oriented businesses due to upstream "
            "purchased goods and logistics. Data quality depends on supplier "
            "reporting completeness and should be treated as estimate-grade "
            "pending supplier-level verification."
        ),
    }


def _get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not _HAS_GENAI or not api_key:
        return None
    return genai.Client(api_key=api_key)


def generate_narrative(summary: dict) -> dict:
    client = _get_client()
    if client is None:
        return _mock_narrative(summary)

    response = client.models.generate_content(
        model=MODEL,
        contents=json.dumps(summary),
        config={
            "system_instruction": NARRATIVE_SYSTEM_PROMPT,
            "response_mime_type": "application/json",
            "temperature": 0.3,
        },
    )
    text_out = (response.text or "").strip()
    if text_out.startswith("```"):
        text_out = text_out.strip("`").replace("json\n", "", 1).strip()
    try:
        return json.loads(text_out)
    except json.JSONDecodeError:
        return _mock_narrative(summary)


def build_pdf_report(
    company_name: str,
    reporting_period: str,
    summary: dict,
    narrative: dict,
    audit_trail_count: int,
    output_path: str,
):
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCustom", parent=styles["Title"], fontSize=20, spaceAfter=6
    )
    h2_style = ParagraphStyle(
        "H2Custom", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6,
        textColor=colors.HexColor("#1D9E75"),
    )
    body_style = ParagraphStyle(
        "BodyCustom", parent=styles["BodyText"], fontSize=10, leading=15
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer", parent=styles["BodyText"], fontSize=8,
        textColor=colors.grey, leading=11,
    )

    story = []
    story.append(Paragraph(f"{company_name}", title_style))
    story.append(Paragraph(
        f"Climate Disclosure Report — Prepared in alignment with ESRS E1", styles["Heading3"]
    ))
    story.append(Paragraph(f"Reporting period: {reporting_period}", body_style))
    story.append(Paragraph(f"Generated: {date.today().isoformat()}", body_style))
    story.append(Spacer(1, 0.6 * cm))

    story.append(Paragraph("1. Methodology Note", h2_style))
    story.append(Paragraph(narrative["methodology_note"], body_style))

    story.append(Paragraph("2. Emissions Summary", h2_style))
    story.append(Paragraph(narrative["emissions_narrative"], body_style))
    story.append(Spacer(1, 0.3 * cm))

    table_data = [["Scope", "Emissions (tCO2e)"]]
    table_data.append(["Scope 1 — Direct emissions", f"{summary['scope_1_tco2e']}"])
    table_data.append(["Scope 2 — Purchased energy", f"{summary['scope_2_tco2e']}"])
    table_data.append(["Scope 3 — Value chain", f"{summary['scope_3_tco2e']}"])
    table_data.append(["TOTAL", f"{summary['total_tco2e']}"])

    t = Table(table_data, colWidths=[10 * cm, 5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D9E75")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EAF3DE")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("3. Emissions by Category", h2_style))
    cat_data = [["Category", "tCO2e"]]
    for cat, val in summary.get("by_category", {}).items():
        cat_data.append([cat, f"{val}"])
    t2 = Table(cat_data, colWidths=[10 * cm, 5 * cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#534AB7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t2)

    story.append(Paragraph("4. Scope 3 Commentary", h2_style))
    story.append(Paragraph(narrative["scope3_commentary"], body_style))

    story.append(Paragraph("5. Audit Trail", h2_style))
    story.append(Paragraph(
        f"This report's emission category assignments were determined via "
        f"{audit_trail_count} classification decisions, logged with full "
        f"source attribution (neural-network classifier vs. LLM-escalated "
        f"review) for traceability. Full audit log available on request.",
        body_style,
    ))

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(
        "Disclaimer: This report is a technology demonstration / portfolio "
        "project output. It has not undergone external limited or "
        "reasonable assurance and does not constitute a formal CSRD/ESRS "
        "compliance filing. Emission factors used are reference-grade "
        "public values; a production deployment would require "
        "jurisdiction- and year-specific verified factors.",
        disclaimer_style,
    ))

    doc.build(story)
    return output_path


if __name__ == "__main__":
    from app.agent import CarbonLedgerAgent

    agent = CarbonLedgerAgent()
    sample_doc = """
    Invoice: Bharat Petroleum - Diesel fuel for backup generator, 1200 litres
    Invoice: State Electricity Board - Industrial electricity consumption, 84000 kWh
    Invoice: XYZ Logistics - Road freight transport of raw materials, 15000 tonne-km
    Invoice: Cotton Traders Co - Cotton yarn raw material purchase, 22000 kg
    """
    result = agent.process_document(sample_doc)
    summary = result.emissions_report.summary()
    narrative = generate_narrative(summary)

    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_report.pdf")
    build_pdf_report(
        company_name="Sample Exports Pvt Ltd",
        reporting_period="Q1 2026 (Jan-Mar)",
        summary=summary,
        narrative=narrative,
        audit_trail_count=len(result.audit_trail),
        output_path=output_path,
    )
    print(f"Report generated at: {output_path}")
