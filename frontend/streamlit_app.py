"""
streamlit_app.py
-----------------
Interactive demo frontend. Run with:
    streamlit run frontend/streamlit_app.py

Lets you paste/upload invoice text, watch the agent pipeline run step by
step (parsing -> classification -> retrieval/escalation -> calculation),
see the audit trail, and download the generated ESRS E1-aligned PDF.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd

from app.agent import CarbonLedgerAgent
from app.report_generator import generate_narrative, build_pdf_report

st.set_page_config(page_title="CarbonLedger — AI Carbon Accounting", page_icon="🌍", layout="wide")

st.title("🌍 CarbonLedger")
st.caption("AI-agent powered Scope 1/2/3 carbon accounting · ESRS E1-aligned reporting · Portfolio/technical demo project")

if not os.environ.get("GEMINI_API_KEY"):
    st.info(
        "Running in **mock mode** — no `GEMINI_API_KEY` environment variable set. "
        "Document parsing, LLM escalation, and report narrative will use clearly-labeled "
        "fallback stubs. Get a free key at aistudio.google.com/apikey to see live Gemini API calls.",
        icon="ℹ️",
    )

if "agent" not in st.session_state:
    st.session_state.agent = CarbonLedgerAgent()

with st.sidebar:
    st.header("Company details")
    company_name = st.text_input("Company name", value="Sample Exports Pvt Ltd")
    reporting_period = st.text_input("Reporting period", value="Q1 2026 (Jan–Mar)")
    st.divider()
    st.caption(
        "**Architecture:** Gemini (document parsing + narrative generation) → "
        "sklearn MLP neural network (line-item classification) → TF-IDF retrieval "
        "(RAG fallback for low-confidence items) → deterministic Python calculation "
        "engine → ReportLab PDF generation."
    )

sample_doc = """Invoice: Bharat Petroleum
Item: Diesel fuel for backup generator, 1200 litres

Invoice: State Electricity Board
Item: Industrial electricity consumption, 84000 kWh

Invoice: XYZ Logistics
Item: Road freight transport of raw materials, 15000 tonne-km

Invoice: Cotton Traders Co
Item: Cotton yarn raw material purchase, 22000 kg

Invoice: City Waste Management
Item: Factory waste disposal, 3400 kg sent to landfill"""

document_text = st.text_area(
    "Paste invoice / bill / supplier statement text",
    value=sample_doc,
    height=220,
)

col1, col2 = st.columns([1, 1])
run_button = col1.button("▶ Run agent pipeline", type="primary", use_container_width=True)
report_button = col2.button("📄 Run + generate PDF report", use_container_width=True)

if run_button or report_button:
    with st.spinner("Agent processing document..."):
        result = st.session_state.agent.process_document(document_text)
        summary = result.emissions_report.summary()

    st.success(f"Processed {len(result.audit_trail)} line items · {len(result.unmatched_items)} unmatched")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Scope 1 (tCO2e)", summary["scope_1_tco2e"])
    m2.metric("Scope 2 (tCO2e)", summary["scope_2_tco2e"])
    m3.metric("Scope 3 (tCO2e)", summary["scope_3_tco2e"])
    m4.metric("Total (tCO2e)", summary["total_tco2e"], delta=f"{summary['scope_3_share_pct']}% Scope 3")

    st.subheader("Emissions by category")
    if summary["by_category"]:
        cat_df = pd.DataFrame(
            list(summary["by_category"].items()), columns=["Category", "tCO2e"]
        ).sort_values("tCO2e", ascending=False)
        st.bar_chart(cat_df.set_index("Category"))
        st.dataframe(cat_df, use_container_width=True, hide_index=True)

    st.subheader("🔍 Agent audit trail")
    st.caption("Every classification decision, and which component made it — required for compliance traceability.")
    audit_df = pd.DataFrame([vars(a) for a in result.audit_trail])
    if not audit_df.empty:
        def highlight_source(row):
            color = "#FAEEDA" if row["decision_source"] == "llm_escalation" else "#E1F5EE"
            return [f"background-color: {color}"] * len(row)
        st.dataframe(audit_df.style.apply(highlight_source, axis=1), use_container_width=True, hide_index=True)

    if result.unmatched_items:
        st.warning(f"Unmatched line items (need manual review): {result.unmatched_items}")

    if report_button:
        with st.spinner("Generating narrative + PDF report..."):
            narrative = generate_narrative(summary)
            output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "generated_reports")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{company_name.replace(' ', '_')}_report.pdf")
            build_pdf_report(
                company_name=company_name,
                reporting_period=reporting_period,
                summary=summary,
                narrative=narrative,
                audit_trail_count=len(result.audit_trail),
                output_path=output_path,
            )
        st.subheader("📄 Generated report")
        with open(output_path, "rb") as f:
            st.download_button(
                "⬇ Download ESRS E1-aligned PDF report",
                data=f.read(),
                file_name=os.path.basename(output_path),
                mime="application/pdf",
            )
