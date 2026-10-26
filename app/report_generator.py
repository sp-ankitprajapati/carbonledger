"""Deterministic draft narrative and an escaped PDF with per-item audit details."""

from dataclasses import asdict, is_dataclass
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors


def generate_narrative(summary):
    return {
        "methodology_note": "Activity quantities are normalized to compatible units and multiplied by a static demonstration factor table. Scopes follow the selected factor keys. Reporting boundaries and factor suitability need independent review.",
        "emissions_narrative": f"Calculated emissions for accepted items total {summary['total_tco2e']} tCO2e. Scope 1: {summary['scope_1_tco2e']}; Scope 2: {summary['scope_2_tco2e']}; Scope 3: {summary['scope_3_tco2e']} tCO2e. Rejected items are excluded and listed in the audit appendix.",
        "scope3_commentary": "This draft covers supplied and accepted activity items only. Factor set demo-reference-v1 is illustrative, with no independently verified year/geography applicability. This is not a complete emissions inventory or compliance filing.",
    }


def build_pdf_report(
    company_name,
    reporting_period,
    summary,
    narrative,
    audit_trail_count=0,
    output_path="report.pdf",
    *,
    audit_trail=None,
    run_id="",
    mode="structured",
):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()

    def p(text, style="BodyText"):
        return Paragraph(escape(str(text)), styles[style])

    story = [
        p(company_name, "Title"),
        p("Carbon accounting demonstration draft", "Heading2"),
        p(f"Reporting period: {reporting_period}"),
        p(f"Generated: {date.today().isoformat()}"),
        p(f"Run: {run_id} / Input mode: {mode}"),
        Spacer(1, 0.4 * cm),
        p("Methodology", "Heading2"),
        p(narrative["methodology_note"]),
        p("Calculated emissions", "Heading2"),
        p(narrative["emissions_narrative"]),
    ]
    data = [["Scope", "tCO2e"]] + [
        [name, str(summary[key])]
        for name, key in [
            ("Scope 1", "scope_1_tco2e"),
            ("Scope 2", "scope_2_tco2e"),
            ("Scope 3", "scope_3_tco2e"),
            ("Total", "total_tco2e"),
        ]
    ]
    table = Table(data, colWidths=[10 * cm, 5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6F2ED")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend(
        [
            Spacer(1, 0.3 * cm),
            table,
            p("Scope and factor limitations", "Heading2"),
            p(narrative["scope3_commentary"]),
            p("Audit appendix", "Heading2"),
        ]
    )
    entries = audit_trail or []
    story.append(
        p(f"{len(entries)} item decisions included. Factor set: demo-reference-v1.")
    )
    if audit_trail_count and not entries:
        story.append(
            p(
                "Only the audit count was provided by this caller; full item details were not attached."
            )
        )
    for i, entry in enumerate(entries, 1):
        row = asdict(entry) if is_dataclass(entry) else entry
        story.extend(
            [
                p(f"{i}. {row['line_item']}", "Heading3"),
                p(f"Source label: {row.get('source_label', '')}"),
                p(
                    f"Status: {row['status']}; source: {row['decision_source']}; category: {row['activity_key']}"
                ),
                p(
                    f"Original: {row['source_quantity']} {row['source_unit']}; normalized: {row.get('normalized_quantity')} {row.get('normalized_unit')}"
                ),
                p(
                    f"Factor: {row.get('factor_kgco2e')} kgCO2e/unit; emissions: {row.get('emissions_kgco2e')} kgCO2e"
                ),
                p(row["confidence_or_reasoning"]),
            ]
        )
    story.extend(
        [
            Spacer(1, 0.4 * cm),
            p(
                "Portfolio technology demonstration. No external assurance or formal ESRS/CSRD compliance assessment. Local JSON audit files are editable records, not a tamper-proof ledger."
            ),
        ]
    )
    SimpleDocTemplate(
        str(path),
        pagesize=A4,
        topMargin=1.7 * cm,
        bottomMargin=1.7 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    ).build(story)
    return str(path)
