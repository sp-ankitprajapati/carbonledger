import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from pypdf import PdfReader
from fastapi.testclient import TestClient
from app.agent import CarbonLedgerAgent
from app.calculator import ActivityRecord, calculate_emissions
from app.document_parser import extract_activity_data


def item(**updates):
    return {
        "description": "Electricity",
        "quantity": 2,
        "unit": "MWh",
        "activity_key": "electricity_india_kwh",
        **updates,
    }


def test_mwh_and_kwh_produce_identical_emissions():
    first = calculate_emissions(
        [ActivityRecord("electricity_india_kwh", 2, source_unit="MWh")]
    )
    second = calculate_emissions(
        [ActivityRecord("electricity_india_kwh", 2000, source_unit="kWh")]
    )
    assert first.grand_total() == second.grand_total() == 1.432
    assert first.records[0].source_quantity == 2
    assert first.records[0].quantity == 2000


@pytest.mark.parametrize("quantity", [-1, float("nan"), float("inf"), True])
def test_invalid_quantities_cannot_reach_arithmetic(quantity):
    with pytest.raises(ValueError):
        calculate_emissions([ActivityRecord("diesel_litre", quantity)])


@pytest.mark.parametrize("unit", ["kg", "unknown", "km"])
def test_incompatible_or_ambiguous_units_require_review(unit):
    with pytest.raises(ValueError):
        calculate_emissions([ActivityRecord("diesel_litre", 10, source_unit=unit)])


def test_aggregate_before_rounding_preserves_small_records():
    report = calculate_emissions(
        [ActivityRecord("diesel_litre", 0.001) for _ in range(100)]
    )
    assert report.grand_total() == 0.0003
    assert sum(report.total_by_category().values()) == 0.0003


def test_unstructured_text_never_silently_becomes_fixed_mock_data():
    with pytest.raises(ValueError, match="JSON array"):
        extract_activity_data("Invoice: diesel, 100 litres")
    assert extract_activity_data("[]") == []


@pytest.mark.parametrize(
    "bad", [{"quantity": -1}, {"unit": ""}, {"quantity": True}, {"description": " "}]
)
def test_extraction_contract_rejects_bad_items(bad):
    with pytest.raises(ValueError):
        extract_activity_data(json.dumps([item(**bad)]))


def test_changed_input_changes_actual_total_and_durable_audit(tmp_path):
    agent = CarbonLedgerAgent(audit_dir=tmp_path)
    a = agent.process_document(json.dumps([item()]))
    b = agent.process_document(json.dumps([item(quantity=4)]))
    assert a.emissions_report.grand_total() == 1.432
    assert b.emissions_report.grand_total() == 2.864
    saved = json.loads(Path(a.audit_path).read_text())
    assert saved["audit_trail"][0]["normalized_quantity"] == 2000
    assert saved["audit_trail"][0]["source_unit"] == "MWh"
    assert saved["partial_result"] is False
    assert a.call_counts == {"extraction": 0, "classification": 0}
    assert a.run_id != b.run_id


def test_partial_result_does_not_count_rejected_units(tmp_path):
    result = CarbonLedgerAgent(audit_dir=tmp_path).process_document(
        json.dumps([item(), item(unit="kg")])
    )
    assert result.emissions_report.grand_total() == 1.432
    assert result.audit_trail[1].status == "rejected"
    assert len(result.unmatched_items) == 1


def test_model_suggestion_needs_confirmation_unless_explicitly_opted_in(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "app.agent.classify_line_item",
        lambda *a: {
            "needs_llm_review": False,
            "predicted_activity_key": "electricity_india_kwh",
            "confidence": 0.99,
        },
    )
    text = json.dumps([{k: v for k, v in item().items() if k != "activity_key"}])
    default = CarbonLedgerAgent(
        classifier_model=object(), audit_dir=tmp_path
    ).process_document(text)
    assert default.audit_trail[0].status == "needs_confirmation"
    assert default.emissions_report.grand_total() == 0
    experimental = CarbonLedgerAgent(
        classifier_model=object(),
        audit_dir=tmp_path,
        allow_experimental_model_decisions=True,
    ).process_document(text)
    assert experimental.emissions_report.grand_total() == 1.432
    assert experimental.experimental_decisions is True


def test_llm_cannot_select_known_factor_outside_retrieved_candidates(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("GEMINI_MODEL", "fake-model")
    responses = iter(
        [
            json.dumps([{k: v for k, v in item().items() if k != "activity_key"}]),
            '{"activity_key":"diesel_litre","reasoning":"invented match"}',
        ]
    )
    client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **_: SimpleNamespace(text=next(responses))
        )
    )
    retriever = SimpleNamespace(
        retrieve=lambda *a, **k: [
            {
                "activity_key": "electricity_india_kwh",
                "score": 1,
                "context": "Electricity",
            }
        ]
    )
    monkeypatch.setattr(
        "app.agent.classify_line_item", lambda *a: {"needs_llm_review": True}
    )
    result = CarbonLedgerAgent(
        mode="live",
        client=client,
        classifier_model=object(),
        retriever=retriever,
        audit_dir=tmp_path,
    ).process_document("unstructured invoice")
    assert result.emissions_report.grand_total() == 0
    assert result.audit_trail[0].activity_key == "UNMATCHED"
    assert result.call_counts == {"extraction": 1, "classification": 1}


def test_zero_similarity_and_offline_escalation_never_guess_first_factor(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "app.agent.classify_line_item", lambda *a: {"needs_llm_review": True}
    )
    retriever = SimpleNamespace(
        retrieve=lambda *a, **k: [{"activity_key": "diesel_litre", "score": 0}]
    )
    result = CarbonLedgerAgent(
        classifier_model=object(), retriever=retriever, audit_dir=tmp_path
    ).process_document(
        json.dumps([{k: v for k, v in item().items() if k != "activity_key"}])
    )
    assert result.audit_trail[0].decision_source == "manual_review"
    assert result.emissions_report.grand_total() == 0


def test_api_report_download_and_audit_include_normalization(tmp_path, monkeypatch):
    monkeypatch.setenv("CARBONLEDGER_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("CARBONLEDGER_REPORT_DIR", str(tmp_path / "reports"))
    from main import app, get_agent

    get_agent.cache_clear()
    with TestClient(app) as client:
        response = client.post(
            "/generate-report",
            json={
                "document_text": json.dumps([item()]),
                "company_name": "../Acme <test> & Co",
                "reporting_period": "DEMO",
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()
        pdf = client.get(data["report_url"])
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
        audit = client.get(data["audit_url"]).json()
        assert audit["records"][0]["source_unit"] == "MWh"
        text = "\n".join(
            p.extract_text()
            for p in PdfReader(tmp_path / "reports" / (data["run_id"] + ".pdf")).pages
        )
        assert "<test> & Co" in text and "2000.0 kWh" in text
        assert client.get("/reports/not-a-uuid").status_code == 422
        assert (
            client.post("/process", json={"document_text": "plain invoice"}).status_code
            == 422
        )
    get_agent.cache_clear()


def test_streamlit_offline_flow_uses_actual_quantities(tmp_path, monkeypatch):
    monkeypatch.setenv("CARBONLEDGER_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("CARBONLEDGER_REPORT_DIR", str(tmp_path / "reports"))
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(
        str(Path(__file__).parents[1] / "frontend/streamlit_app.py"), default_timeout=30
    ).run()
    assert not app.exception
    app.text_area[0].set_value(json.dumps([item(quantity=4)]))
    app.button[0].click().run()
    assert not app.exception
    assert app.metric[3].value == "2.864"
