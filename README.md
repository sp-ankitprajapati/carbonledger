# CarbonLedger — AI-Agent Powered Carbon Accounting Platform

An end-to-end system that turns unstructured invoices/bills into structured
Scope 1/2/3 GHG emissions data and an ESRS E1 (CSRD)-aligned PDF report,
using a multi-component AI pipeline: LLM document parsing, a trained neural
network classifier, retrieval-augmented escalation, and a deterministic
calculation engine — with a full audit trail for compliance traceability.

Built as a portfolio/technical project to demonstrate full-stack + applied
AI engineering skills relevant to SDE, ML, and AI-agent roles.

**LLM used: Google Gemini (free tier)** — chosen so the entire project can
be run, demoed, and iterated on at zero cost. Get a free API key at
https://aistudio.google.com/apikey (no credit card required).

---

## 1. Architecture overview

```
 Unstructured invoice/bill text
            │
            ▼
 ┌─────────────────────────┐
 │ document_parser.py       │  Gemini API — extracts structured line items
 │ (LLM extraction)          │  (description, quantity, unit) from messy text
 └─────────────────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │ classifier.py             │  sklearn MLPClassifier (feedforward neural
 │ (Neural Network)          │  network, TF-IDF → 64→32 hidden layers)
 └─────────────────────────┘
            │
     confidence ≥ 0.55? ──── yes ──► use NN prediction directly
            │
            no
            ▼
 ┌─────────────────────────┐
 │ retrieval.py               │  TF-IDF + cosine similarity retrieval over
 │ (RAG retriever)            │  the emission factors knowledge base
 └─────────────────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │ agent.py → Gemini          │  Gemini chooses the best match from the
 │ (LLM escalation, grounded) │  retrieved candidates (not free-form guessing)
 └─────────────────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │ calculator.py               │  Pure deterministic Python — converts
 │ (calculation engine)        │  activity × emission factor → tCO2e.
 │                              │  LLM NEVER touches this step.
 └─────────────────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │ report_generator.py         │  Gemini writes narrative sections (grounded
 │ (narrative + PDF)           │  in the computed numbers) → ReportLab builds
 │                              │  the final ESRS E1-structured PDF
 └─────────────────────────┘
            │
            ▼
   Full audit trail + PDF report
   (every decision traceable to its source: NN / LLM / deterministic calc)
```

This is exposed via a **FastAPI** REST backend (`main.py`) and a
**Streamlit** interactive demo frontend (`frontend/streamlit_app.py`).

---

## 2. Why this architecture (the part to say out loud in an interview)

**"Why not just call an LLM for everything?"**
Cost and reliability. Classifying every line item via an LLM API call
doesn't scale and risks hallucinated numbers. The neural network classifier
handles the bulk of cases locally in milliseconds at near-zero cost; the
LLM is reserved for genuinely ambiguous cases (confidence-gated escalation)
— this mirrors how production systems at companies like Watershed/Persefoni
actually architect cost-sensitive AI pipelines.

**"Why is the LLM never used for the actual math?"**
Auditability and correctness. Regulatory/compliance numbers cannot be
"approximately right" — they need to be deterministic and reproducible.
Separating "LLM extracts/classifies/writes prose" from "plain Python does
arithmetic" is a deliberate reliability decision, not a limitation.

**"Why TF-IDF instead of a neural embedding model for retrieval?"**
Honest tradeoff: neural embedding models (sentence-transformers, or a
hosted embeddings API) require downloading pretrained weights or calling
an external service at runtime. TF-IDF is dependency-light and works fully
offline. The known limitation — it misses synonyms ("cotton fabric" vs.
"textile") — is a real, acknowledged tradeoff with a clear upgrade path
(swap the retriever class for an embedding-based one without touching the
agent's orchestration logic, since retrieval is cleanly abstracted behind
`EmissionFactorRetriever.retrieve()`).

**"Why Gemini instead of GPT-4 or Claude?"**
Cost, for a student/portfolio project: Gemini's free tier (Gemini 2.5
Flash via Google AI Studio) requires no credit card and provides a
generous daily quota — enough for full development, testing, and demoing
without spending anything. The architecture is provider-agnostic: swapping
in a different LLM means changing the client initialization in three files
(`document_parser.py`, `agent.py`, `report_generator.py`) — the rest of
the pipeline (classifier, retrieval, calculator) is untouched, since the
LLM is cleanly isolated behind narrow function boundaries.

**"What does 'agent' mean here, technically?"**
Not "a chatbot." `CarbonLedgerAgent` implements a decision loop: it takes
an action (classify), observes the result (confidence score), and
conditionally takes a different action (escalate to LLM with retrieved
context) based on that observation — the defining characteristic of an
agentic system vs. a single LLM call.

---

## 3. What's real vs. what's a known limitation (be honest about both)

**Real and working:**
- Full pipeline runs end-to-end, tested (`pytest tests/` — 8 passing tests)
- Genuine trained neural network (not just calling an API and calling it "AI")
- Deterministic, auditable calculation engine with full test coverage
- Working FastAPI backend + Streamlit frontend, runnable locally in minutes
- PDF report generation produces a real, structured, ESRS E1-style document
- Runs entirely on free tiers — Gemini API, Railway, Streamlit Cloud, Supabase

**Known limitations (own these proactively in interviews — it reads as
maturity, not weakness):**
- Emission factors are reference-grade public values, not licensed/audited
  figures — a production version needs verified, jurisdiction-specific,
  annually-updated factors.
- TF-IDF retrieval has real recall limitations on synonyms/paraphrases.
- The MLP classifier is trained on a small synthetic dataset (~50 examples)
  — works well for the demo but would need real labeled data at scale.
- This has not been used by real customers and is not a CSRD/ESRS
  compliance-certified product. The PDF explicitly says so in its disclaimer.
- Gemini's free tier has rate limits (requests per minute/day) — fine for
  demos and development, would need a paid tier for production traffic.

---

## 4. Setup & running it

```bash
pip install -r requirements.txt

# Get a FREE Gemini API key: https://aistudio.google.com/apikey
# (no credit card required)
export GEMINI_API_KEY="your-key-here"
# Or copy .env.example to .env and fill it in

# Run tests
pytest tests/ -v

# Run the calculation engine / classifier / agent standalone (smoke tests)
python3 -m app.calculator
python3 -m app.classifier
python3 -m app.agent
python3 -m app.report_generator     # generates data/sample_report.pdf

# Run the API
uvicorn main:app --reload --port 8000
# Visit http://localhost:8000/docs for interactive API docs

# Run the interactive demo UI
streamlit run frontend/streamlit_app.py
```

The system runs fully in a clearly-labeled **mock mode** with zero setup
if you don't set `GEMINI_API_KEY` — useful for testing the pipeline logic,
UI, and PDF generation without needing an API key at all.

---

## 5. How to honestly describe this on your resume

**Good (honest, specific, technically substantive):**
> "Built CarbonLedger, an AI-agent powered carbon accounting pipeline:
> Gemini-based document extraction, a trained neural network classifier for
> line-item categorization with confidence-gated LLM escalation (RAG over
> a custom knowledge base), a deterministic Scope 1/2/3 calculation engine,
> and automated ESRS E1-aligned PDF report generation. FastAPI backend,
> Streamlit demo UI, full test coverage, runs entirely on free-tier infra."

**Avoid (dishonest, will fail under interview questioning):**
> "Founded a carbon accounting startup with paying customers, generating
> $X revenue, EU CSRD compliant." — None of this is true yet. Claiming
> fake traction or false compliance certification is exactly the kind of
> claim an interviewer will probe ("tell me about a customer call," "who
> audited your compliance claim") and it will actively damage your
> credibility once it unravels.

The honest version is *more* impressive to a technical interviewer at
Google/Microsoft than a vague unverifiable traction claim — it gives them
concrete things to ask you about (architecture decisions, tradeoffs,
testing approach), which is exactly where you can shine since you
understand every line of this system.

---

## 6. Natural extensions (good answers to "what would you build next?")

- Swap TF-IDF retrieval for a real embedding-based vector store (FAISS +
  sentence-transformers, or Gemini's own embedding model)
- Add a human-in-the-loop review UI for `UNMATCHED` and low-confidence items
- Add supplier-facing data collection portal (the actual Scope 3 data
  bottleneck in real CSRD compliance work)
- Persist results to a real database (Postgres/Supabase) instead of
  in-memory dataclasses
- Add authentication + multi-tenant support to the FastAPI backend
- Expand the classifier's training set and add active learning (flag
  low-confidence predictions for labeling, retrain periodically)
