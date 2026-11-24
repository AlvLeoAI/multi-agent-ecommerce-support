"""
Phase 5: Request Admission Limits, Sanitized Error Envelopes & CORS Allowlist.

Covers:
1. Body-size admission (`RequestBodyLimitMiddleware`, HTTP 413) ahead of routing.
2. Chat input caps: message length, non-blank text, and identifier charset/length (HTTP 422),
   with no agent turn started for a rejected request.
3. Failed agent turns return a fixed 500 message and never echo the exception text.
4. CORS is an exact-origin allowlist without credentials; wildcards are ignored.
5. Model-supplied escalation ticket fields are bounded before storage.
6. The fabricated per-product query metric endpoint is gone.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import main as backend_main
from models.schemas import MAX_CHAT_MESSAGE_CHARS
from request_limits import (
    DEFAULT_CORS_ORIGINS,
    MAX_REQUEST_BODY_BYTES,
    parse_cors_origins,
)
from routers import chat as chat_router
from services.order_verification import (
    MAX_TICKET_IDENTIFIER_CHARS,
    MAX_TICKET_REASON_CHARS,
    create_escalation_ticket,
)

CHAT_URL = "/api/v1/chat/"
SECRET_ERROR_TEXT = "boom: key=AIza-NOT-A-REAL-KEY path=/app/my_agent_data.db"


@pytest.fixture
def client() -> TestClient:
    return TestClient(backend_main.app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# 1. Body-size admission
# ---------------------------------------------------------------------------


def test_oversized_body_is_rejected_with_413_before_any_agent_turn(
    client: TestClient, stub_adk_runner: Any
) -> None:
    payload = {"message": "A" * (MAX_REQUEST_BODY_BYTES + 1), "session_id": "sess_big"}
    response = client.post(CHAT_URL, json=payload)

    assert response.status_code == 413
    assert str(MAX_REQUEST_BODY_BYTES) in response.json()["detail"]
    assert stub_adk_runner.queries == []


def test_chunked_body_without_content_length_is_still_bounded(
    client: TestClient, stub_adk_runner: Any
) -> None:
    def chunks() -> Any:
        yield b'{"message": "'
        for _ in range(MAX_REQUEST_BODY_BYTES // 1024 + 2):
            yield b"A" * 1024
        yield b'"}'

    response = client.post(CHAT_URL, content=chunks(), headers={"Content-Type": "application/json"})

    assert response.status_code == 413
    assert stub_adk_runner.queries == []


def test_body_at_the_limit_is_admitted_and_then_validated(client: TestClient) -> None:
    """A body within the byte limit reaches validation, which applies the tighter field cap."""
    padding = MAX_REQUEST_BODY_BYTES - len('{"message": ""}')
    response = client.post(
        CHAT_URL,
        content=('{"message": "' + "A" * padding + '"}').encode(),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 2. Chat input caps
# ---------------------------------------------------------------------------


def test_message_at_the_cap_is_accepted(client: TestClient, stub_adk_runner: Any) -> None:
    response = client.post(
        CHAT_URL, json={"message": "A" * MAX_CHAT_MESSAGE_CHARS, "session_id": "sess_cap"}
    )
    assert response.status_code == 200
    assert len(stub_adk_runner.queries) == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"message": "A" * (MAX_CHAT_MESSAGE_CHARS + 1)},
        {"message": "   \n\t  "},
        {"message": "hi", "session_id": "S" * 129},
        {"message": "hi", "session_id": "bad id with spaces"},
        {"message": "hi", "session_id": "line\nbreak"},
        {"message": "hi", "session_id": ""},
        {"message": "hi", "user_id": "U" * 129},
        {"message": "hi", "user_id": "../../etc/passwd"},
    ],
    ids=[
        "message-too-long",
        "blank-message",
        "session-id-too-long",
        "session-id-spaces",
        "session-id-newline",
        "session-id-empty",
        "user-id-too-long",
        "user-id-path-chars",
    ],
)
def test_invalid_chat_input_is_rejected_without_starting_an_agent_turn(
    client: TestClient, stub_adk_runner: Any, payload: dict[str, str]
) -> None:
    response = client.post(CHAT_URL, json=payload)

    assert response.status_code == 422
    assert stub_adk_runner.queries == []


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/v1/chat/sessions/" + "S" * 129),
        ("delete", "/api/v1/chat/sessions/" + "S" * 129),
        ("get", "/api/v1/chat/users/" + "U" * 129 + "/sessions"),
        ("get", "/api/v1/chat/users/bad%20id/preferences"),
    ],
)
def test_path_identifiers_follow_the_same_pattern(
    client: TestClient, method: str, path: str
) -> None:
    assert getattr(client, method)(path).status_code == 422


def test_oversized_preferences_are_rejected(client: TestClient) -> None:
    too_big = {"note": "x" * chat_router.MAX_PREFERENCES_BYTES}
    assert client.post("/api/v1/chat/users/alice/preferences", json=too_big).status_code == 422

    small = {"theme": "dark"}
    assert client.post("/api/v1/chat/users/alice/preferences", json=small).status_code == 200
    assert client.get("/api/v1/chat/users/alice/preferences").json()["preferences"] == small


@pytest.mark.parametrize("days", [0, -5, 366])
def test_agent_metrics_lookback_window_is_bounded(client: TestClient, days: int) -> None:
    assert client.get(f"/metrics/agents?days={days}").status_code == 422
    assert client.get("/metrics/agents?days=30").status_code == 200


# ---------------------------------------------------------------------------
# 3. Sanitized error envelopes
# ---------------------------------------------------------------------------


def test_failed_agent_turn_returns_fixed_message_and_never_echoes_the_exception(
    client: TestClient, stub_adk_runner: Any, caplog: pytest.LogCaptureFixture
) -> None:
    stub_adk_runner.raise_error = RuntimeError(SECRET_ERROR_TEXT)

    with caplog.at_level("ERROR"):
        response = client.post(CHAT_URL, json={"message": "hi", "session_id": "sess_err"})

    assert response.status_code == 500
    assert response.json() == {"detail": chat_router.GENERIC_CHAT_ERROR}
    assert "AIza" not in response.text and "my_agent_data" not in response.text
    # The detail is still available to operators in the server log.
    assert SECRET_ERROR_TEXT in caplog.text

    summary = chat_router.quality_tracker.get_metrics_summary(days=1)
    assert summary["total_conversations"] == 1
    assert summary["error_rate"] == 100.0


def test_quality_metrics_failure_returns_fixed_message(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError(SECRET_ERROR_TEXT)

    monkeypatch.setattr(chat_router.quality_tracker, "get_metrics_summary", explode)
    response = client.get("/api/v1/chat/quality-metrics")

    assert response.status_code == 500
    assert response.json() == {"detail": chat_router.GENERIC_METRICS_ERROR}


# ---------------------------------------------------------------------------
# 4. CORS allowlist
# ---------------------------------------------------------------------------


def _preflight(client: TestClient, origin: str) -> Any:
    return client.options(
        CHAT_URL,
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )


def test_cors_allows_only_listed_origins_and_never_credentials(client: TestClient) -> None:
    listed_origin = backend_main.CORS_ALLOWED_ORIGINS[0]
    allowed = _preflight(client, listed_origin)
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == listed_origin
    assert "access-control-allow-credentials" not in allowed.headers

    denied = _preflight(client, "https://evil.example")
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers

    simple = client.get("/health", headers={"Origin": "https://evil.example"})
    assert simple.status_code == 200
    assert "access-control-allow-origin" not in simple.headers


def test_configured_cors_origins_are_an_exact_allowlist() -> None:
    configured = backend_main.CORS_ALLOWED_ORIGINS
    assert configured
    assert all("*" not in origin for origin in configured)
    assert all(origin.startswith(("http://", "https://")) for origin in configured)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, list(DEFAULT_CORS_ORIGINS)),
        ("", list(DEFAULT_CORS_ORIGINS)),
        ("*", list(DEFAULT_CORS_ORIGINS)),
        ("https://*.example.com", list(DEFAULT_CORS_ORIGINS)),
        ("https://shop.example.com", ["https://shop.example.com"]),
        (
            " https://a.example.com/ ,https://b.example.com,, https://a.example.com",
            ["https://a.example.com", "https://b.example.com"],
        ),
        ("*, https://a.example.com", ["https://a.example.com"]),
    ],
)
def test_parse_cors_origins_drops_wildcards_and_normalizes(
    raw: str | None, expected: list[str]
) -> None:
    assert parse_cors_origins(raw) == expected


# ---------------------------------------------------------------------------
# 5. Bounded escalation ticket fields
# ---------------------------------------------------------------------------


def test_escalation_ticket_fields_are_truncated_before_storage(client: TestClient) -> None:
    ticket = create_escalation_ticket(
        reason="r" * (MAX_TICKET_REASON_CHARS + 500),
        session_id="s" * 500,
        user_id="u" * 500,
    )

    stored = client.get(f"/api/v1/tickets/{ticket['ticket_id']}").json()
    assert len(stored["reason"]) == MAX_TICKET_REASON_CHARS
    assert len(stored["session_id"]) == MAX_TICKET_IDENTIFIER_CHARS
    assert len(stored["user_id"]) == MAX_TICKET_IDENTIFIER_CHARS


# ---------------------------------------------------------------------------
# 6. Removed fabricated metric
# ---------------------------------------------------------------------------


def test_fabricated_top_queried_metric_endpoint_is_removed(client: TestClient) -> None:
    assert client.get("/metrics/products/top-queried").status_code == 404
    paths = backend_main.app.openapi()["paths"]
    assert not any("top-queried" in path for path in paths)
