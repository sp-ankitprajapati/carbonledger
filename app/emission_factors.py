"""
emission_factors.py
--------------------
Static knowledge base of GHG emission factors used to convert raw activity
data (litres of diesel, kWh of electricity, km of freight, kg of waste)
into CO2-equivalent emissions (tCO2e).

Sources (publicly published, standard reference factors):
  - GHG Protocol Corporate Standard, Cross-Sector Tools
  - IEA / CEA (Central Electricity Authority, India) grid emission factor
  - DEFRA (UK) freight/logistics factors, used as international fallback

NOTE: These are reference-grade factors suitable for a demo / portfolio
project. A production compliance product would need factors licensed or
verified against the latest published GHG Protocol / DEFRA tables and
country-specific grid factors updated annually.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class EmissionFactor:
    activity: str
    unit: str
    factor_kgco2e: float   # kg CO2e per unit of activity
    scope: int
    category: str
    description: str


# Core factor table. factor_kgco2e = kg CO2 equivalent emitted per 1 unit.
EMISSION_FACTORS: Dict[str, EmissionFactor] = {
    "diesel_litre": EmissionFactor(
        activity="diesel_litre", unit="litre", factor_kgco2e=2.68,
        scope=1, category="Stationary/Mobile Combustion",
        description="Diesel combustion in owned vehicles or generators"
    ),
    "petrol_litre": EmissionFactor(
        activity="petrol_litre", unit="litre", factor_kgco2e=2.31,
        scope=1, category="Mobile Combustion",
        description="Petrol combustion in owned vehicles"
    ),
    "natural_gas_m3": EmissionFactor(
        activity="natural_gas_m3", unit="cubic metre", factor_kgco2e=2.03,
        scope=1, category="Stationary Combustion",
        description="Natural gas combustion for heating/processing"
    ),
    "electricity_india_kwh": EmissionFactor(
        activity="electricity_india_kwh", unit="kWh", factor_kgco2e=0.716,
        scope=2, category="Purchased Electricity",
        description="India national grid average emission factor (CEA baseline)"
    ),
    "electricity_eu_kwh": EmissionFactor(
        activity="electricity_eu_kwh", unit="kWh", factor_kgco2e=0.231,
        scope=2, category="Purchased Electricity",
        description="EU-27 average grid emission factor"
    ),
    "freight_road_tkm": EmissionFactor(
        activity="freight_road_tkm", unit="tonne-km", factor_kgco2e=0.107,
        scope=3, category="Upstream Transportation & Distribution",
        description="Road freight, average heavy goods vehicle"
    ),
    "freight_sea_tkm": EmissionFactor(
        activity="freight_sea_tkm", unit="tonne-km", factor_kgco2e=0.011,
        scope=3, category="Upstream Transportation & Distribution",
        description="Sea freight container shipping"
    ),
    "freight_air_tkm": EmissionFactor(
        activity="freight_air_tkm", unit="tonne-km", factor_kgco2e=0.602,
        scope=3, category="Upstream Transportation & Distribution",
        description="Air freight"
    ),
    "purchased_goods_textile_kg": EmissionFactor(
        activity="purchased_goods_textile_kg", unit="kg", factor_kgco2e=8.40,
        scope=3, category="Purchased Goods & Services",
        description="Generic textile/apparel raw material, cradle-to-gate"
    ),
    "purchased_goods_steel_kg": EmissionFactor(
        activity="purchased_goods_steel_kg", unit="kg", factor_kgco2e=2.00,
        scope=3, category="Purchased Goods & Services",
        description="Generic steel/metal component, cradle-to-gate"
    ),
    "purchased_goods_plastic_kg": EmissionFactor(
        activity="purchased_goods_plastic_kg", unit="kg", factor_kgco2e=3.10,
        scope=3, category="Purchased Goods & Services",
        description="Generic plastic/polymer input, cradle-to-gate"
    ),
    "business_travel_air_km": EmissionFactor(
        activity="business_travel_air_km", unit="passenger-km", factor_kgco2e=0.158,
        scope=3, category="Business Travel",
        description="Domestic/short-haul flight, economy class"
    ),
    "employee_commute_km": EmissionFactor(
        activity="employee_commute_km", unit="passenger-km", factor_kgco2e=0.104,
        scope=3, category="Employee Commuting",
        description="Average passenger vehicle commute"
    ),
    "waste_landfill_kg": EmissionFactor(
        activity="waste_landfill_kg", unit="kg", factor_kgco2e=0.467,
        scope=3, category="Waste Generated in Operations",
        description="Mixed waste sent to landfill"
    ),
    "water_supply_m3": EmissionFactor(
        activity="water_supply_m3", unit="cubic metre", factor_kgco2e=0.149,
        scope=3, category="Purchased Goods & Services",
        description="Municipal water supply and treatment"
    ),
}


def get_factor(activity_key: str) -> EmissionFactor:
    if activity_key not in EMISSION_FACTORS:
        raise KeyError(f"No emission factor found for activity '{activity_key}'")
    return EMISSION_FACTORS[activity_key]


def list_factors_by_scope(scope: int):
    return [f for f in EMISSION_FACTORS.values() if f.scope == scope]


def search_factors_text() -> Dict[str, str]:
    """Returns activity_key -> searchable text blob, used by the retrieval module."""
    return {
        k: f"{v.activity} {v.category} {v.description} unit {v.unit}"
        for k, v in EMISSION_FACTORS.items()
    }
