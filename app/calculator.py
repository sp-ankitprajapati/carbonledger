"""
calculator.py
-------------
Deterministic Scope 1 / Scope 2 / Scope 3 emissions calculation engine.

Design note: emissions math should NEVER be left to an LLM (hallucination
risk on numbers is unacceptable for a compliance product). The LLM/agent
layer (agent.py) is only used for: parsing unstructured documents into
structured activity data, and writing the narrative sections of the report.
All arithmetic happens here, in plain deterministic Python, so the output
numbers are reproducible and auditable — this separation of concerns is
itself a key design decision worth explaining in an interview.
"""

from dataclasses import dataclass, field
from typing import List, Dict
from app.emission_factors import get_factor, EmissionFactor


@dataclass
class ActivityRecord:
    activity_key: str          # must match a key in EMISSION_FACTORS
    quantity: float            # amount in the factor's native unit
    source_label: str = ""     # e.g. "Electricity bill - March 2026"


@dataclass
class EmissionResult:
    activity_key: str
    quantity: float
    unit: str
    factor_kgco2e: float
    emissions_kgco2e: float
    emissions_tco2e: float
    scope: int
    category: str
    source_label: str


@dataclass
class EmissionsReport:
    records: List[EmissionResult] = field(default_factory=list)

    def total_by_scope(self, scope: int) -> float:
        return round(
            sum(r.emissions_tco2e for r in self.records if r.scope == scope), 4
        )

    def total_by_category(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for r in self.records:
            out[r.category] = round(out.get(r.category, 0) + r.emissions_tco2e, 4)
        return out

    def grand_total(self) -> float:
        return round(sum(r.emissions_tco2e for r in self.records), 4)

    def summary(self) -> Dict:
        return {
            "scope_1_tco2e": self.total_by_scope(1),
            "scope_2_tco2e": self.total_by_scope(2),
            "scope_3_tco2e": self.total_by_scope(3),
            "total_tco2e": self.grand_total(),
            "by_category": self.total_by_category(),
            "scope_3_share_pct": round(
                100 * self.total_by_scope(3) / self.grand_total(), 1
            ) if self.grand_total() > 0 else 0,
        }


def calculate_emissions(activities: List[ActivityRecord]) -> EmissionsReport:
    """Pure function: list of activity records -> full emissions report."""
    report = EmissionsReport()
    for act in activities:
        factor: EmissionFactor = get_factor(act.activity_key)
        emissions_kg = act.quantity * factor.factor_kgco2e
        report.records.append(
            EmissionResult(
                activity_key=act.activity_key,
                quantity=act.quantity,
                unit=factor.unit,
                factor_kgco2e=factor.factor_kgco2e,
                emissions_kgco2e=round(emissions_kg, 3),
                emissions_tco2e=round(emissions_kg / 1000, 5),
                scope=factor.scope,
                category=factor.category,
                source_label=act.source_label,
            )
        )
    return report


if __name__ == "__main__":
    # Quick smoke test
    sample = [
        ActivityRecord("diesel_litre", 1200, "Generator fuel - Q1"),
        ActivityRecord("electricity_india_kwh", 84000, "Factory electricity - Q1"),
        ActivityRecord("freight_road_tkm", 15000, "Inbound raw material freight"),
        ActivityRecord("purchased_goods_textile_kg", 22000, "Cotton yarn purchases"),
        ActivityRecord("waste_landfill_kg", 3400, "Production waste"),
    ]
    rep = calculate_emissions(sample)
    import json
    print(json.dumps(rep.summary(), indent=2))
