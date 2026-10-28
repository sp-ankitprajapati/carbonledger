"""Deterministic Scope 1, Scope 2 and Scope 3 emissions calculations.

Activity quantities are normalized before applying the static factor table.
Model-assisted parsing is separate from the arithmetic and report totals.
"""

from dataclasses import dataclass, field
from typing import List, Dict
import math
from app.emission_factors import get_factor, EmissionFactor
from app.units import normalize_quantity


@dataclass
class ActivityRecord:
    activity_key: str  # must match a key in EMISSION_FACTORS
    quantity: float  # amount in source_unit, or native units for legacy Python callers
    source_label: str = ""  # e.g. "Electricity bill - March 2026"
    source_unit: str = (
        ""  # blank only for Python callers explicitly supplying native units
    )


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
    source_quantity: float = 0
    source_unit: str = ""
    factor_set: str = "demo-reference-v1"


@dataclass
class EmissionsReport:
    records: List[EmissionResult] = field(default_factory=list)

    def total_by_scope(self, scope: int) -> float:
        return round(
            math.fsum(r.emissions_tco2e for r in self.records if r.scope == scope), 4
        )

    def total_by_category(self) -> Dict[str, float]:
        return {
            category: round(
                math.fsum(
                    r.emissions_tco2e for r in self.records if r.category == category
                ),
                4,
            )
            for category in sorted({r.category for r in self.records})
        }

    def grand_total(self) -> float:
        return round(math.fsum(r.emissions_tco2e for r in self.records), 4)

    def summary(self) -> Dict:
        return {
            "scope_1_tco2e": self.total_by_scope(1),
            "scope_2_tco2e": self.total_by_scope(2),
            "scope_3_tco2e": self.total_by_scope(3),
            "total_tco2e": self.grand_total(),
            "by_category": self.total_by_category(),
            "scope_3_share_pct": round(
                100 * self.total_by_scope(3) / self.grand_total(), 1
            )
            if self.grand_total() > 0
            else 0,
        }


def calculate_emissions(activities: List[ActivityRecord]) -> EmissionsReport:
    """Pure function: list of activity records -> full emissions report."""
    report = EmissionsReport()
    for act in activities:
        factor: EmissionFactor = get_factor(act.activity_key)
        quantity = normalize_quantity(
            act.quantity, act.source_unit or factor.unit, factor.unit
        )
        emissions_kg = quantity * factor.factor_kgco2e
        if not math.isfinite(emissions_kg):
            raise ValueError("Calculated emissions overflowed")
        report.records.append(
            EmissionResult(
                activity_key=act.activity_key,
                quantity=quantity,
                unit=factor.unit,
                factor_kgco2e=factor.factor_kgco2e,
                emissions_kgco2e=emissions_kg,
                emissions_tco2e=emissions_kg / 1000,
                scope=factor.scope,
                category=factor.category,
                source_label=act.source_label,
                source_quantity=float(act.quantity),
                source_unit=act.source_unit or factor.unit,
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
