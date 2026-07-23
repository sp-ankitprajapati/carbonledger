"""
agent.py
--------
The orchestration layer — this is the "AI agent" of CarbonLedger.

An agent, properly defined, is not "an LLM you talk to." It is a system
that (1) breaks a goal into steps, (2) takes actions using tools, (3)
observes results, and (4) decides the next action based on those results,
including when to escalate to a more expensive/capable resource. That loop
is what's implemented here.

Pipeline for one document:
  1. document_parser.extract_activity_data()  -> raw line items (Gemini)
  2. classifier.classify_line_item()          -> fast local NN classification
  3. IF confidence >= threshold: accept classifier's label directly
     IF confidence <  threshold: agent escalates --
       a. retrieval.retrieve() pulls top-3 candidate emission factors
       b. Gemini is given the line item + retrieved candidates and asked
          to make the final call, grounded in the retrieved options
          (this is the RAG step — Gemini is not guessing from memory,
          it is choosing from a constrained, retrieved candidate set)
  4. calculator.calculate_emissions()          -> deterministic math
  5. Full audit trail is returned: every decision, which component made
     it, and the confidence/reasoning behind it. This audit trail is
     itself a compliance requirement (ESRS / CSRD calls for traceability
     of disclosed figures) and a good thing to highlight in interviews —
     it shows you thought about auditability, not just "getting an answer."

Uses Google Gemini (free tier) as the LLM. Get a free API key at
https://aistudio.google.com/apikey and set it as GEMINI_API_KEY.
"""

import os
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any

from app.classifier import classify_line_item, load_classifier
from app.retrieval import EmissionFactorRetriever
from app.calculator import ActivityRecord, calculate_emissions, EmissionsReport
from app.document_parser import extract_activity_data

try:
    from google import genai
    _HAS_GENAI = True
except ImportError:
    _HAS_GENAI = False

MODEL = "gemini-2.5-flash"

ESCALATION_SYSTEM_PROMPT = """You are an expert carbon accounting analyst.
You will be given a line item description from an invoice and a short list
of candidate emission activity categories retrieved from a knowledge base.

Choose the single best matching activity_key from the candidates. Respond
ONLY with JSON: {"activity_key": "<chosen key>", "reasoning": "<one sentence>"}

If none of the candidates are a reasonable match, respond with:
{"activity_key": "UNMATCHED", "reasoning": "<why none fit>"}"""


@dataclass
class AuditEntry:
    line_item: str
    decision_source: str       # "neural_network" | "llm_escalation" | "mock"
    activity_key: str
    confidence_or_reasoning: str


@dataclass
class AgentRunResult:
    emissions_report: EmissionsReport
    audit_trail: List[AuditEntry] = field(default_factory=list)
    unmatched_items: List[str] = field(default_factory=list)


class CarbonLedgerAgent:
    def __init__(self):
        self.classifier_model = load_classifier()
        self.retriever = EmissionFactorRetriever()
        api_key = os.environ.get("GEMINI_API_KEY")
        self.gemini_client = (
            genai.Client(api_key=api_key)
            if (_HAS_GENAI and api_key) else None
        )

    def _escalate_to_llm(self, line_item_text: str) -> Dict[str, Any]:
        candidates = self.retriever.retrieve(line_item_text, top_k=3)

        if self.gemini_client is None:
            # No API key — deterministic, clearly-labeled fallback so the
            # pipeline still runs end-to-end in a demo without credentials.
            top = candidates[0]
            return {
                "activity_key": top["activity_key"],
                "reasoning": "[MOCK - no API key] fell back to top TF-IDF retrieval candidate",
            }

        prompt = (
            f"Line item: \"{line_item_text}\"\n\n"
            f"Candidates:\n" +
            "\n".join(f"- {c['activity_key']}: {c['context']} (similarity={c['score']})"
                       for c in candidates)
        )

        response = self.gemini_client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config={
                "system_instruction": ESCALATION_SYSTEM_PROMPT,
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        )
        text_out = (response.text or "").strip()
        if text_out.startswith("```"):
            text_out = text_out.strip("`").replace("json\n", "", 1).strip()

        try:
            return json.loads(text_out)
        except json.JSONDecodeError:
            return {"activity_key": "UNMATCHED", "reasoning": "LLM response unparseable"}

    def process_document(self, raw_document_text: str) -> AgentRunResult:
        # Step 1: extract structured line items from unstructured text
        line_items = extract_activity_data(raw_document_text)

        audit_trail: List[AuditEntry] = []
        unmatched: List[str] = []
        activities: List[ActivityRecord] = []

        for item in line_items:
            desc = item.get("description", "")
            quantity = float(item.get("quantity", 0))
            source_label = item.get("source_label", "")

            # Step 2: fast local neural-network classification
            cls_result = classify_line_item(desc, self.classifier_model)

            if not cls_result["needs_llm_review"]:
                activity_key = cls_result["predicted_activity_key"]
                audit_trail.append(AuditEntry(
                    line_item=desc,
                    decision_source="neural_network",
                    activity_key=activity_key,
                    confidence_or_reasoning=f"confidence={cls_result['confidence']}",
                ))
            else:
                # Step 3: escalate to retrieval + Gemini
                llm_result = self._escalate_to_llm(desc)
                activity_key = llm_result.get("activity_key", "UNMATCHED")
                audit_trail.append(AuditEntry(
                    line_item=desc,
                    decision_source="llm_escalation",
                    activity_key=activity_key,
                    confidence_or_reasoning=llm_result.get("reasoning", ""),
                ))

            if activity_key == "UNMATCHED":
                unmatched.append(desc)
                continue

            activities.append(ActivityRecord(
                activity_key=activity_key,
                quantity=quantity,
                source_label=source_label or desc,
            ))

        # Step 4: deterministic calculation — never delegated to the LLM
        emissions_report = calculate_emissions(activities)

        return AgentRunResult(
            emissions_report=emissions_report,
            audit_trail=audit_trail,
            unmatched_items=unmatched,
        )


if __name__ == "__main__":
    agent = CarbonLedgerAgent()
    sample_doc = """
    Invoice: Bharat Petroleum
    Item: Diesel fuel for backup generator, 1200 litres

    Invoice: State Electricity Board
    Item: Industrial electricity consumption, 84000 kWh

    Invoice: XYZ Logistics
    Item: Road freight transport of raw materials, 15000 tonne-km

    Invoice: Cotton Traders Co
    Item: Cotton yarn raw material purchase, 22000 kg
    """
    result = agent.process_document(sample_doc)
    print("=== EMISSIONS SUMMARY ===")
    print(json.dumps(result.emissions_report.summary(), indent=2))
    print("\n=== AUDIT TRAIL ===")
    for entry in result.audit_trail:
        print(entry)
