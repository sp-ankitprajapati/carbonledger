"""
test_calculator.py
-------------------
Run with: pytest tests/
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.calculator import ActivityRecord, calculate_emissions


def test_single_activity_calculation():
    activities = [ActivityRecord("diesel_litre", 100, "test")]
    report = calculate_emissions(activities)
    assert report.records[0].emissions_kgco2e == 268.0
    assert report.records[0].scope == 1


def test_scope_totals():
    activities = [
        ActivityRecord("diesel_litre", 1000, "scope1 test"),
        ActivityRecord("electricity_india_kwh", 1000, "scope2 test"),
        ActivityRecord("freight_road_tkm", 1000, "scope3 test"),
    ]
    report = calculate_emissions(activities)
    summary = report.summary()
    assert summary["scope_1_tco2e"] == 2.68
    assert summary["scope_2_tco2e"] == 0.716
    assert summary["scope_3_tco2e"] == 0.107
    assert round(summary["total_tco2e"], 3) == round(2.68 + 0.716 + 0.107, 3)


def test_empty_activities_returns_zero():
    report = calculate_emissions([])
    summary = report.summary()
    assert summary["total_tco2e"] == 0
    assert summary["scope_3_share_pct"] == 0


def test_invalid_activity_key_raises():
    import pytest
    with pytest.raises(KeyError):
        calculate_emissions([ActivityRecord("nonexistent_activity", 10, "bad")])


def test_category_aggregation():
    activities = [
        ActivityRecord("diesel_litre", 100, "a"),
        ActivityRecord("petrol_litre", 100, "b"),  # different activity, same category-ish
    ]
    report = calculate_emissions(activities)
    by_cat = report.total_by_category()
    assert "Stationary/Mobile Combustion" in by_cat or "Mobile Combustion" in by_cat
