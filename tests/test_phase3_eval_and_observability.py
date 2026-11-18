"""
Phase 3 Offline Evaluation Suite & Observability Hardening Tests (Resolves F-07).

Covers:
1. 100% pass rate across all 24 golden evaluation cases in `eval/cases.jsonl`.
2. `QualityTracker` parameterized SQL safety, empty-database `NaN` sanitization,
   and user rating persistence.
3. `resolve_delegated_agent` specialist attribution from ADK turn metadata and
   function call parts (`ProductAgent`, `CalculationAgent`, `OrderSupportAgent`,
   `GeneralAgent`, `CoordinatorAgent`).
4. Explicit runner error surfacing (`success=False`, `error_occurred=True`, HTTP 500)
   when ADK turns are empty or malformed.
"""

from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace

import pytest
from eval.runner import format_scorecard, run_eval_suite
from fastapi.testclient import TestClient

import main as backend_main
from database.quality_tracker import QualityTracker
from routers.chat import resolve_delegated_agent


@pytest.fixture
def client() -> TestClient:
    return TestClient(backend_main.app)


def test_offline_eval_harness_passes_all_24_golden_cases() -> None:
    """Verify `run_eval_suite()` executes all 24 golden cases across 4 categories at 100%."""
    summary = run_eval_suite()
    assert summary["total"] == 24
    assert summary["passed"] == 24
    assert summary["failed"] == 0
    assert summary["pass_rate"] == 1.0

    expected_categories = {
        "catalog_grounding",
        "deterministic_pricing",
        "evidence_verification",
        "adversarial_security",
    }
    assert set(summary["by_category"].keys()) == expected_categories
    for cat_stats in summary["by_category"].values():
        assert cat_stats["total"] == 6
        assert cat_stats["passed"] == 6
        assert cat_stats["failed"] == 0
        assert cat_stats["pass_rate"] == 1.0

    scorecard_md = format_scorecard(summary)
    assert "| **TOTAL** | **24** | **24** | **0** | **100.0%** |" in scorecard_md


def test_quality_tracker_empty_db_nan_sanitization_and_ratings(tmp_path: Path) -> None:
    """
    Verify `QualityTracker.get_metrics_summary()` never returns `None` or `NaN`
    on an empty SQLite table and accurately records user ratings.
    """
    tracker = QualityTracker(str(tmp_path / "empty_quality.db"))
    empty_summary = tracker.get_metrics_summary(days=7)

    assert empty_summary["total_conversations"] == 0
    for key, val in empty_summary.items():
        assert val is not None, f"Key {key} was None on empty DB"
        assert not (isinstance(val, float) and math.isnan(val)), f"Key {key} was NaN"

    tracker.track_conversation(
        conversation_id="conv_rated_1",
        response_time=0.42,
        tokens_used=120,
        steps_count=2,
        agent_used="OrderSupportAgent",
        success=True,
        error_occurred=False,
    )
    tracker.save_user_rating("conv_rated_1", 1)

    populated = tracker.get_metrics_summary(days=7)
    assert populated["total_conversations"] == 1
    assert populated["total_ratings"] == 1
    assert populated["satisfaction_score"] == 100.0

    by_agent_df = tracker.get_metrics_by_agent(days=7)
    assert len(by_agent_df) == 1
    assert by_agent_df.iloc[0]["agent_used"] == "OrderSupportAgent"

    trends_df = tracker.get_trends(days=7)
    assert len(trends_df) == 1
    assert int(trends_df.iloc[0]["conversations"]) == 1


def test_resolve_delegated_agent_from_turn_attributes_and_tool_calls() -> None:
    """
    Verify `resolve_delegated_agent` accurately attributes turns to `ProductAgent`,
    `CalculationAgent`, `OrderSupportAgent`, `GeneralAgent`, or `CoordinatorAgent`.
    """
    calc_turn = SimpleNamespace(
        content=SimpleNamespace(
            parts=[
                SimpleNamespace(
                    function_call=SimpleNamespace(name="calculate_quote"),
                    text=None,
                )
            ]
        )
    )
    final_turn = SimpleNamespace(
        content=SimpleNamespace(parts=[SimpleNamespace(text="Your total is $1,402.92.")])
    )
    assert resolve_delegated_agent([calc_turn, final_turn]) == "CalculationAgent"

    order_turn = SimpleNamespace(
        content=SimpleNamespace(
            parts=[
                SimpleNamespace(
                    function_response=SimpleNamespace(name="verify_order_claim"),
                    text=None,
                )
            ]
        )
    )
    assert resolve_delegated_agent([order_turn, final_turn]) == "OrderSupportAgent"

    author_turn = SimpleNamespace(
        author="GeneralAgent",
        content=SimpleNamespace(parts=[SimpleNamespace(text="Hello!")]),
    )
    assert resolve_delegated_agent([author_turn]) == "GeneralAgent"

    direct_turn = SimpleNamespace(
        content=SimpleNamespace(parts=[SimpleNamespace(text="Direct coordinator reply.")])
    )
    assert resolve_delegated_agent([direct_turn]) == "CoordinatorAgent"


def test_chat_endpoint_records_delegated_subagent_and_rejects_empty_turns(
    client: TestClient,
    stub_adk_runner: object,
) -> None:
    """
    Verify `POST /api/v1/chat/` records the delegated specialist agent in `QualityTracker`
    on success and records `success=False, error_occurred=True` (HTTP 500) on empty turns.
    """
    stub_adk_runner.custom_turns = [
        SimpleNamespace(
            content=SimpleNamespace(
                parts=[SimpleNamespace(function_call=SimpleNamespace(name="calculate_quote"))]
            )
        ),
        SimpleNamespace(
            content=SimpleNamespace(
                parts=[SimpleNamespace(text="Quote calculated: $1,455.08 total.")]
            )
        ),
    ]
    ok_resp = client.post(
        "/api/v1/chat/",
        json={"message": "Quote 1 Dell XPS 15 with WELCOME10", "session_id": "sess_calc_ok"},
    )
    assert ok_resp.status_code == 200
    ok_data = ok_resp.json()
    assert ok_data["metadata"]["agent_used"] == "CalculationAgent"
    assert ok_data["metadata"]["steps_count"] == 2

    # Empty turn list must fail loudly (HTTP 500) and record error_occurred=True
    stub_adk_runner.custom_turns = []
    err_resp = client.post(
        "/api/v1/chat/",
        json={"message": "Trigger empty turn error", "session_id": "sess_empty_err"},
    )
    assert err_resp.status_code == 500

    qm = client.get("/api/v1/chat/quality-metrics", params={"days": 7}).json()
    assert qm["summary"]["total_conversations"] == 2
    assert qm["summary"]["error_rate"] == 50.0
