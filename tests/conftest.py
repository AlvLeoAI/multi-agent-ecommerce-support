"""
Phase 0–4 Offline Test Harness & Isolation Fixtures.

Enforces:
1. 100% offline execution (`block_outbound_network` autouse fixture).
2. Isolated temporary SQLite databases (`isolated_sqlite_dbs` autouse fixture)
   for chat memory, product catalog, discount codes, orders, payment/grant evidence,
   support tickets, and quality metrics.
3. Deterministic Google ADK 2.14.1 runner stubbing (`stub_adk_runner` fixture)
   implementing `run_async(user_id=..., session_id=..., new_message=...)`.
"""

from __future__ import annotations

import os
import socket
import sqlite3
import sys
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

# Ensure dummy API key is present before any backend module is imported
os.environ.setdefault("GOOGLE_API_KEY", "offline-test-key")

# Ensure backend/ is on sys.path for legacy imports (`from routers import ...`)
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Redirect module-import-time SQLite side effects (`my_agent_data.db` and `ecommerce_agent.db`)
# into a session-wide temporary directory so importing `main` never pollutes the working tree.
_IMPORT_TEMP_DIR = tempfile.TemporaryDirectory(prefix="phase0_import_dbs_")
_ORIG_SQLITE_CONNECT = sqlite3.connect


def _redirected_sqlite_connect(
    database: str | Path, *args: Any, **kwargs: Any
) -> sqlite3.Connection:
    db_str = str(database)
    if db_str.endswith("my_agent_data.db") or db_str.endswith("ecommerce_agent.db"):
        redirected = Path(_IMPORT_TEMP_DIR.name) / Path(db_str).name
        return _ORIG_SQLITE_CONNECT(str(redirected), *args, **kwargs)
    return _ORIG_SQLITE_CONNECT(database, *args, **kwargs)


sqlite3.connect = _redirected_sqlite_connect
try:
    import main as backend_main  # noqa: E402
    from database import catalog_db, chat_memory, orders_db, quality_tracker  # noqa: E402
    from routers import chat as chat_router  # noqa: E402
finally:
    sqlite3.connect = _ORIG_SQLITE_CONNECT

# Alias modules so `backend.database.*` and `database.*` resolve to the exact same module object
sys.modules.setdefault("backend.main", backend_main)
sys.modules.setdefault("backend.database.catalog_db", catalog_db)
sys.modules.setdefault("backend.database.chat_memory", chat_memory)
sys.modules.setdefault("backend.database.orders_db", orders_db)
sys.modules.setdefault("backend.database.quality_tracker", quality_tracker)
sys.modules.setdefault("backend.routers.chat", chat_router)


@pytest.fixture(autouse=True)
def block_outbound_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Block all external TCP/UDP socket connections during pytest execution.
    Allows local AF_UNIX sockets used internally by asyncio event loops.
    """
    monkeypatch.setenv("GOOGLE_API_KEY", "offline-test-key")

    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _is_allowed_local_socket(sock: socket.socket, address: Any) -> bool:
        if getattr(sock, "family", None) == socket.AF_UNIX:
            return True
        return False

    def guarded_connect(self: socket.socket, address: Any) -> Any:
        if _is_allowed_local_socket(self, address):
            return real_connect(self, address)
        raise RuntimeError("Outbound network call blocked by Phase 0 offline test guard")

    def guarded_connect_ex(self: socket.socket, address: Any) -> Any:
        if _is_allowed_local_socket(self, address):
            return real_connect_ex(self, address)
        raise RuntimeError("Outbound network call blocked by Phase 0 offline test guard")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)


@pytest.fixture(autouse=True)
def isolated_sqlite_dbs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """
    Redirect `chat_memory.DB_PATH`, `catalog_db.DB_PATH`, `orders_db.DB_PATH`,
    and `routers.chat.quality_tracker` to isolated per-test SQLite files inside `tmp_path`.
    """
    chat_db_path = tmp_path / "test_chat_memory.db"
    quality_db_path = tmp_path / "test_quality.db"

    monkeypatch.setattr(chat_memory, "DB_PATH", chat_db_path)
    monkeypatch.setattr(catalog_db, "DB_PATH", chat_db_path)
    monkeypatch.setattr(orders_db, "DB_PATH", chat_db_path)
    chat_memory.init_chat_memory_db(db_path=chat_db_path)
    catalog_db.init_catalog_db(db_path=chat_db_path)
    orders_db.init_orders_db(db_path=chat_db_path)

    isolated_tracker = quality_tracker.QualityTracker(str(quality_db_path))
    monkeypatch.setattr(chat_router, "quality_tracker", isolated_tracker)

    return {
        "chat_db": chat_db_path,
        "quality_db": quality_db_path,
    }


def _extract_message_text(new_message: Any) -> str:
    if isinstance(new_message, str):
        return new_message
    parts = getattr(new_message, "parts", None)
    if parts and isinstance(parts, (list, tuple)):
        texts = [str(getattr(p, "text", "")) for p in parts if getattr(p, "text", None) is not None]
        if texts:
            return "\n".join(texts)
    return str(new_message)


class StubADKController:
    """Controller for inspecting captured ADK Agent configurations and configuring turn outputs."""

    def __init__(self) -> None:
        self.instances: list[StubInMemoryRunner] = []
        self.last_agent: Any = None
        self.queries: list[str] = []
        self.user_ids: list[str] = []
        self.session_ids: list[str] = []
        self.response_text: str = "Stubbed deterministic agent response."
        self.custom_turns: Any = None
        self.raise_error: Exception | None = None

    def make_turn(
        self, text: str, *, thought: bool = False, author: str | None = None
    ) -> SimpleNamespace:
        return SimpleNamespace(
            author=author,
            content=SimpleNamespace(parts=[SimpleNamespace(text=text, thought=thought)]),
        )


class StubInMemoryRunner:
    """
    Deterministic offline replacement for `google.adk.runners.InMemoryRunner`
    enforcing the real ADK 2.14.1 `run_async(user_id=..., session_id=..., new_message=...)` contract.
    """

    controller: StubADKController

    def __init__(
        self,
        agent: Any = None,
        *,
        app_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.agent = agent
        self.app_name = app_name
        self.auto_create_session: bool = False
        self.name = getattr(agent, "name", None)
        self.instruction = getattr(agent, "instruction", None)
        self.tools = getattr(agent, "tools", None)
        self.model = getattr(agent, "model", None)
        self.controller.instances.append(self)
        self.controller.last_agent = agent

    def run(self, *args: Any, **kwargs: Any) -> Any:
        raise TypeError(
            "Runner.run() takes 1 positional argument but 2 were given; "
            "use run_async(user_id=..., session_id=..., new_message=...)"
        )

    async def run_async(
        self,
        *,
        user_id: str,
        session_id: str,
        new_message: Any,
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        extracted_text = _extract_message_text(new_message)
        self.controller.queries.append(extracted_text)
        self.controller.user_ids.append(user_id)
        self.controller.session_ids.append(session_id)

        if self.controller.raise_error is not None:
            raise self.controller.raise_error

        turns = (
            self.controller.custom_turns
            if self.controller.custom_turns is not None
            else [self.controller.make_turn(self.controller.response_text)]
        )
        for turn in turns:
            yield turn


@pytest.fixture
def stub_adk_runner(monkeypatch: pytest.MonkeyPatch) -> StubADKController:
    """
    Monkeypatch `routers.chat.InMemoryRunner` with a deterministic `StubInMemoryRunner`.
    Returns a `StubADKController` for inspecting captured `Agent` attributes and customizing turns.
    """
    controller = StubADKController()

    class _BoundStubRunner(StubInMemoryRunner):
        pass

    _BoundStubRunner.controller = controller
    monkeypatch.setattr(chat_router, "InMemoryRunner", _BoundStubRunner)
    return controller
