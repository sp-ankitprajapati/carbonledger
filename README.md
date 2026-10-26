# CarbonLedger

A portfolio carbon-accounting pipeline that validates activity input, suggests emission categories, normalizes compatible units, calculates Scope 1/2/3 totals and exports item-level JSON audits and a draft PDF. Python, FastAPI, scikit-learn, lexical RAG, optional Gemini, Streamlit and ReportLab.

## Verified status

**29 local tests pass**, including API downloads and a headless Streamlit submission. The supplied structured example produces **1.7000 tCO2e**: 100 litres diesel = 0.268 tonnes; 2 MWh electricity = 1.432 tonnes. JSON audits preserve original and normalized quantities, factor-set identity, decisions and rejected items. The PDF includes its audit appendix.

The 48-example / 15-class synthetic corpus is too small for a reliable invoice classifier. Exploratory two-fold stratified CV yields MLP accuracy **39.58%**, macro F1 **0.3474**. At the old 0.55 threshold, only 27.08% of CV predictions are accepted, with 38.46% accuracy among accepted items. These uncalibrated scores do not support the previous 90% API-savings claim. See [evaluation evidence](results/classifier_cv.json) and [model card](docs/MODEL_CARD.md).

**Model suggestions require category confirmation by default.** Supply a checked activity_key in structured input to calculate normally. An explicit experimental opt-in restores confidence-gated automated classification for demonstrations. It is recorded in the response and audit. A high model score is not independent verification.

## Install and run

Use Python 3.12 in a fresh virtual environment:

```bash
python -m venv .venv
# Activate .venv for your shell.
python -m pip install -e ".[dev,ui]"
python -m pytest tests -q
python -m uvicorn main:app --reload
```

In another terminal, launch the independent interface:

```bash
streamlit run frontend/streamlit_app.py
```

The Streamlit screen calls shared Python logic directly. It does not require the REST server. Its default structured example works without credentials or paid calls. API docs are available at http://localhost:8000/docs while the server runs.

## Explicit input modes

**Structured mode (default):** reads a JSON array from document_text. See [sample input](data/sample_activities.json).

```json
[{"description":"Electricity","quantity":2,"unit":"MWh","activity_key":"electricity_india_kwh","source_label":"DEMO-002"}]
```

activity_key is optional. Without it, the classifier/retriever can suggest a category, but the item remains needs_confirmation unless experimental model decisions were explicitly enabled. Incompatible units and unsupported categories are excluded and visibly recorded as partial results. Plain invoice text in structured mode fails validation. There is no automatic 450-litre mock substitute.

**Live mode:** install `python -m pip install -e ".[gemini]"`, set GEMINI_API_KEY and GEMINI_MODEL in the process environment, and submit mode=live. Choose a model currently available to your account. The application does not automatically load .env. Live extraction validates every returned item; malformed output raises an error. The extractor cannot provide activity_key to bypass classification. Escalation accepts only a retrieved, positive-similarity candidate or UNMATCHED. With default controls, check suggested categories before resubmitting structured input.

Provider use can incur charges. No live provider calls were made for the checked run. Tests inject controlled responses. Narrative text is now generated deterministically from the computed totals, so report generation adds no LLM narrative call.

## API

POST /process accepts document_text, mode and optional allow_experimental_model_decisions (default false). POST /generate-report additionally accepts company_name and reporting_period. Responses include summary, run_id, audit_trail, unmatched_items, partial_result, call_counts and audit_url. Report responses include report_url. GET /audit/{run_id} and /reports/{run_id} download the UUID-named artifacts.

Each run writes a separate JSON record atomically to data/audit. PDF names use run IDs instead of company names, preventing filename traversal and repeated-company overwrites. Configure CARBONLEDGER_AUDIT_DIR and CARBONLEDGER_REPORT_DIR when needed. These local output files are mutable records, not a tamper-proof ledger. The API has no authentication or retention service and is intended for local demonstrations.

## Unit and factor contracts

MWh/kWh/Wh, kg/g/metric tonnes, litre/ml and explicit cubic metres support compatible conversions. Freight tonne-km and passenger-km are separate dimensions. The code refuses density conversions and ambiguous passenger occupancy assumptions. Negative, Boolean, NaN and infinite quantities fail validation. Internal arithmetic retains precision until summaries are rounded.

Factors are the original static **demo-reference-v1** table. Their source/year/geography suitability has not been independently verified. Scope assignment follows static activity keys and does not determine organizational reporting boundaries. The ESRS-inspired report structure does not establish ESRS/CSRD compliance, audit assurance or a complete emissions inventory. Scanned-image OCR is not implemented.

## Code and learning map

| File | Responsibility |
| --- | --- |
| app/document_parser.py | Explicit structured/live modes and extraction schema |
| app/classifier.py | TF-IDF + MLP and unrounded confidence gate |
| app/retrieval.py | TF-IDF cosine-similarity candidates |
| app/agent.py | Constrained selection, confirmation, per-item audit and persistence |
| app/units.py / calculator.py | Compatible units, finite quantities and deterministic arithmetic |
| app/report_generator.py | Deterministic prose, escaped text and full PDF audit appendix |
| main.py / frontend/streamlit_app.py | REST and Streamlit entry points |
| scripts/evaluate_classifier.py | Reproducible small-corpus CV with logistic baseline |

Read [Hinglish guide](docs/LEARNING_HINGLISH.md), [model card](docs/MODEL_CARD.md) and [change evidence](results/verification.json). To rerun CV: `python scripts/evaluate_classifier.py` after editable installation. The vectorizer fits each training fold separately. The synthetic CV is diagnostic and is not an independent invoice benchmark.

## Accurate CV wording

- Built a carbon-accounting prototype with compatible-unit normalization, deterministic Scope 1/2/3 calculations and persisted item-level audit records.
- Implemented confidence-gated TF-IDF/MLP and retrieval-assisted category suggestions, with constrained escalation and explicit confirmation for weakly validated model outputs.
- Added FastAPI artifact downloads, Streamlit workflow, audited draft PDFs and29 automated tests; published small-corpus evaluation and limitations.

Next model improvement requires a larger independently labeled invoice set, suitable geography/year-specific factors, calibrated routing and measured provider-call counts. Adding a different model alone does not establish reliable accounting.
