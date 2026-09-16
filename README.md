# CarbonLedger — AI-Agent Powered Carbon Accounting Platform

An end-to-end system that turns unstructured invoices/bills into structured
Scope 1/2/3 GHG emissions data and an ESRS E1 (CSRD)-aligned PDF report,
using a multi-component AI pipeline: LLM document parsing, a trained neural
network classifier, retrieval-augmented escalation, and a deterministic
calculation engine — with a full audit trail for compliance traceability.

Built as a portfolio project demonstrating end-to-end 
applied AI engineering and full-stack development.

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


**working:**
- Full pipeline runs end-to-end, tested (`pytest tests/` — 8 passing tests)
- Genuine trained neural network (not just calling an API and calling it "AI")
- Deterministic, auditable calculation engine with full test coverage
- Working FastAPI backend + Streamlit frontend, runnable locally in minutes
- PDF report generation produces a real, structured, ESRS E1-style document
- Runs entirely on free tiers — Gemini API, Railway, Streamlit Cloud, Supabase

**Known limitations**
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


