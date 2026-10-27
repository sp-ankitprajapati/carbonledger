"""Run with streamlit run frontend/streamlit_app.py from the repository root."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st
import pandas as pd
from app.agent import CarbonLedgerAgent
from app.report_generator import generate_narrative, build_pdf_report

st.set_page_config(page_title="CarbonLedger", page_icon=":material/eco:", layout="wide")
st.title("CarbonLedger")
st.caption(
    "Scope 1/2/3 calculation with demonstration factors and item-level audit records."
)
mode_label = st.segmented_control(
    "Input mode", ["Structured JSON", "Live invoice text"], default="Structured JSON"
)
mode = "live" if mode_label == "Live invoice text" else "structured"
if st.session_state.get("last_mode") != mode:
    st.session_state.update(last_mode=mode, result=None, pdf=None)
if mode == "structured":
    st.info(
        "Offline mode reads the quantities and categories you supply. Choose live mode to extract invoice text using Gemini."
    )
    sample = (
        Path(__file__).resolve().parents[1] / "data/sample_activities.json"
    ).read_text()
else:
    st.info(
        "Live extraction needs GEMINI_API_KEY and GEMINI_MODEL in the environment. Provider usage may be billable."
    )
    sample = "Invoice DEMO-001: diesel generator fuel, 100 litres."


@st.cache_resource(max_entries=4)
def get_agent(input_mode, allow_experimental):
    return CarbonLedgerAgent(
        mode=input_mode, allow_experimental_model_decisions=allow_experimental
    )


with st.form("invoice"):
    company = st.text_input("Company name", "Sample Exports Pvt Ltd")
    period = st.text_input("Reporting period", "Demo period")
    document = st.text_area(
        "Activity JSON" if mode == "structured" else "Invoice text",
        sample,
        height=240,
        key=f"document_{mode}",
    )
    experimental = st.checkbox(
        "Calculate with experimental model suggestions",
        value=False,
        help="The small synthetic-data classifier is weakly validated. Leave this off to require checked activity keys.",
    )
    create_pdf = st.checkbox("Create a PDF with the audit appendix", value=True)
    submitted = st.form_submit_button(
        "Process activities", type="primary", width="stretch"
    )
if submitted:
    st.session_state.update(result=None, pdf=None)
    try:
        with st.spinner("Processing activities..."):
            result = get_agent(mode, experimental).process_document(document)
            st.session_state.result = result
            if create_pdf:
                path = (
                    Path(os.getenv("CARBONLEDGER_REPORT_DIR", "data/generated_reports"))
                    / f"{result.run_id}.pdf"
                )
                summary = result.emissions_report.summary()
                build_pdf_report(
                    company,
                    period,
                    summary,
                    generate_narrative(summary),
                    output_path=str(path),
                    audit_trail=result.audit_trail,
                    run_id=result.run_id,
                    mode=result.mode,
                )
                st.session_state.pdf = path.read_bytes()
    except Exception as exc:
        st.error(f"Processing failed: {exc}")
result = st.session_state.get("result")
if result is not None:
    st.caption(f"Run {result.run_id}. Input mode: {result.mode}.")
    if result.unmatched_items:
        st.warning(
            "Partial result: some items need review and are excluded from the totals."
        )
    elif not result.audit_trail:
        st.info(
            "No activity items were found. A zero result does not establish zero organizational emissions."
        )
    else:
        st.success(f"Calculated {len(result.emissions_report.records)} activity items.")
    summary = result.emissions_report.summary()
    for column, label, key in zip(
        st.columns(4),
        ["Scope 1", "Scope 2", "Scope 3", "Total"],
        ["scope_1_tco2e", "scope_2_tco2e", "scope_3_tco2e", "total_tco2e"],
    ):
        column.metric(f"{label} (tCO2e)", summary[key])
    st.subheader("Item audit")
    if result.audit_trail:
        st.dataframe(
            pd.DataFrame([vars(a) for a in result.audit_trail]),
            hide_index=True,
            alt="Classification and unit-normalization decisions for each activity",
        )
    st.download_button(
        "Download audit JSON",
        Path(result.audit_path).read_bytes(),
        file_name=f"audit-{result.run_id}.json",
        mime="application/json",
    )
    if st.session_state.get("pdf"):
        st.download_button(
            "Download draft PDF",
            st.session_state.pdf,
            file_name=f"carbonledger-{result.run_id}.pdf",
            mime="application/pdf",
        )
st.caption(
    "Demonstration factors and static reporting scopes require independent review before real disclosures."
)
