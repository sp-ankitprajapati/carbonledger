"""
test_classifier.py
-------------------
Run with: pytest tests/
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.classifier import train_classifier, classify_line_item


def test_classifier_trains_without_error():
    model = train_classifier(save=False)
    assert model is not None


def test_classifier_predicts_known_category_correctly():
    model = train_classifier(save=False)
    result = classify_line_item("diesel fuel bill for backup generator", model)
    assert result["predicted_activity_key"] == "diesel_litre"
    assert result["confidence"] > 0.5


def test_classifier_returns_confidence_and_escalation_flag():
    model = train_classifier(save=False)
    result = classify_line_item("monthly electricity invoice", model)
    assert "confidence" in result
    assert "needs_llm_review" in result
    assert isinstance(result["needs_llm_review"], bool)
