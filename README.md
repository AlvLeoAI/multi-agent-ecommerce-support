# Multi-Agent E-Commerce Support & Evidence Verification Service

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.163-009688?logo=fastapi&logoColor=white)
![Google ADK](https://img.shields.io/badge/Orchestration-Google_ADK_2.14-4285F4?logo=google&logoColor=white)
![Tests](https://img.shields.io/badge/Pytest-66_Passed_%7C_0_XFail-2ea44f)
![Offline Eval](https://img.shields.io/badge/Offline_Eval-24%2F24_(100%25)-2ea44f)
![License](https://img.shields.io/badge/License-MIT-green)

## 1. Executive Technical Summary

`multi-agent-ecommerce-support` is the commercial front-office and post-purchase dispute verification layer of a **Transactional AI & Agentic Payments** engineering portfolio. Built with **Google Agent Development Kit (ADK)**, **Gemini 2.5 Flash**, **FastAPI**, **Pydantic v2**, **SQLite**, and **Streamlit**, it coordinates specialized support agents for catalog discovery, deterministic cart quote calculation, order/payment evidence verification, and verifiable human escalation.

### Core Architectural Invariant

> **Probabilistic LLM reasoning is strictly decoupled from financial arithmetic, inventory validation, state mutations, and payment/fulfillment evidence verification.**

The LLM acts exclusively as a conversational router and parameter extractor (`product_id`, integer `quantity`, allowlisted `discount_code`, `tax_jurisdiction`, `order_id`, and `claim_type`). All unit prices, stock counts, promotional discount caps, tax calculations, settlement checks, and dispute verdicts are computed deterministically by pure Python services backed by SQLite.

---

## 2. Portfolio Ecosystem Integration

This repository is contractually aligned with four sibling repositories in the portfolio:

| Sibling Repository | Shared Architectural Contract & Integration Surface | Implementation in This Repository |
| :--- | :--- | :--- |
| **[`Agentic-Payments-Lab`](https://github.com/AlvLeoAI/Agentic-Payments-Lab)** | Dual monetary representation (`amount_cents: int` at $10^2$ USD scale and `sim_usdc_micros: int` at $10^6$ `SIM-USDC` atomic scale), `x402` settlement protocol metadata, and `PurchaseEvidence` / `GrantEvidence` envelopes. | `backend/services/pricing.py` outputs `total_cents` and `total_sim_usdc_micros` on every quote; `backend/models/schemas.py` and `backend/database/orders_db.py` store `PurchaseEvidence` (`x402`, `tx_hash`, `sim_usdc_micros`, `charge_count`, `authorized_by_mandate`) and `GrantEvidence`. |
| **[`ticket-prioritization-api`](https://github.com/AlvLeoAI/ticket-prioritization-api)** | Deterministic dispute verification over the 4 canonical claim types (`charged_not_delivered`, `duplicate_charge`, `unauthorized_purchase`, `charged_but_denied`) producing a strict verdict (`confirmed`, `contradicted`, `unverifiable`), `reason_code`, and `recommended_priority`. | `backend/services/order_verification.py` (`verify_order_claim`) and `POST /api/v1/orders/{order_id}/verify-claim` deterministically evaluate claims against SQLite `PurchaseEvidence` and `GrantEvidence`. |
| **[`Agent-Transaction-Monitoring`](https://github.com/AlvLeoAI/Agent-Transaction-Monitoring)** | Know-Your-Agent (KYA) mandate authorization boundary (`authorized_by_mandate: bool` and `mandate_id: str \| None`) where compliance/risk decisions are owned by deterministic rules rather than LLM inference. | `verify_order_claim` checks `PurchaseEvidence.authorized_by_mandate` and flags settled orders lacking a KYA mandate (`ORD-1004`) as `confirmed` `unauthorized_purchase` with `reason_code="MISSING_KYA_MANDATE_AUTHORIZATION"` and `recommended_priority="critical"`. |
| **[`Clinic-Scheduling-Agent`](https://github.com/AlvLeoAI/Clinic-Scheduling-Agent)** | Strict separation between untrusted conversational context and deterministic SQLite state transitions, paired with a reproducible offline evaluation harness (`eval/`). | `CoordinatorAgent.instruction` is immutable; untrusted history is role-sanitized and passed via turn payloads (`build_turn_input_with_context`), and `eval/runner.py` verifies 24 golden cases 100% offline. |

---

## 3. Staged Refactor Audit Trail (`v0-baseline` Flaws `F-01`–`F-07` vs. Hardened Architecture)

During **Phase 0**, the initial prototype (`v0-baseline`) was audited and frozen with characterization and `@pytest.mark.xfail(strict=True)` tests before systematically resolving each structural flaw across **Phases 1–3**:

| Flaw ID | `v0-baseline` Vulnerability | Phase Resolved | Hardened Engineering Resolution | Enforcing Test Suite |
| :--- | :--- | :---: | :--- | :--- |
| **F-01** | Missing `backend/database/products.json` caused immediate `FileNotFoundError` at module import time; unpinned `git+https://.../adk-python.git` dependency. | **Phase 0 & 1** | Added deterministic seed catalog `backend/database/products.json`, migrated catalog & discount codes to SQLite (`backend/database/catalog_db.py`), and pinned all dependencies (`google-adk==2.14.1`) in `pyproject.toml`. | `test_products_and_metrics_contracts` |
| **F-02** | `CalculationAgent` used `BuiltInCodeExecutor()` to run LLM-generated Python `float` math with zero catalog grounding or discount validation. | **Phase 1** | Removed `BuiltInCodeExecutor()` completely. Wired `CalculationAgent` to pure `decimal.Decimal` (`ROUND_HALF_UP`) tools (`calculate_quote`, `lookup_product`) in `backend/services/pricing.py`. | `test_calculation_agent_decoupled_from_llm_code_executor`, `test_phase1_deterministic_commerce.py` |
| **F-03** | Raw untrusted `user_query` and conversation history were string-interpolated directly into `CoordinatorAgent.instruction`, enabling prompt-injected discounts and role spoofing. | **Phase 1** | Locked `COORDINATOR_INSTRUCTION` as an immutable constant. Isolated user queries and history into `build_turn_input_with_context` with regex role-spoof neutralization (`sanitize_untrusted_text`). | `test_prompt_injection_cannot_contaminate_coordinator_system_instruction`, `test_turn_input_neutralizes_embedded_role_spoofing` |
| **F-04** | Active `ProductAgent` in `routers/chat.py` used `google_search` (hallucinating web products/prices) while `backend/agents/` was orphaned dead code with hardcoded prices in prompts. | **Phase 1** | Removed `google_search`. Unified `ProductAgent` and `backend/agents/` around deterministic SQLite catalog tools (`get_product_info`, `search_products`, `check_inventory`) and stripped hardcoded prompt prices. | `test_active_product_agent_uses_deterministic_local_catalog_not_google_search`, `test_canonical_agents_have_no_hardcoded_prompt_prices_and_use_sqlite_tools` |
| **F-05** | `escalate_to_human_support` returned an ephemeral in-memory UUID (`TICKET-xxxxxx`) with zero database persistence or order/dispute linkage. | **Phase 2** | Implemented `support_tickets`, `orders`, and `order_evidence` tables in `backend/database/orders_db.py` and `create_escalation_ticket` in `backend/services/order_verification.py`. | `test_escalation_persists_verifiable_ticket_state`, `test_escalation_ticket_linked_to_order_claim_and_retrieved_via_api` |
| **F-06** | `get_session_history` used `ORDER BY timestamp ASC LIMIT 20`, returning the *oldest* 20 messages and dropping recent turns once a session exceeded 20 messages. | **Phase 1** | Rewrote `get_session_history` and `get_session_context` in `backend/database/chat_memory.py` using an `ORDER BY id DESC LIMIT ?` subquery wrapped in `ORDER BY id ASC`. | `test_session_context_returns_most_recent_messages_in_chronological_order` |
| **F-07** | Bare `except:` blocks in `routers/chat.py` masked malformed ADK runner turns as `success=True`, hardcoded `agent_used="CoordinatorAgent"`, and used f-string SQL interpolation in `QualityTracker`. | **Phase 3** | Added `resolve_delegated_agent`, replaced bare `except:` with strict turn validation that logs `success=False, error_occurred=True` on failure, parameterized all SQL in `QualityTracker`, and sanitized empty-DB `NaN` aggregates. | `test_quality_tracker_records_actual_subagent_and_surfaces_runner_errors`, `test_phase3_eval_and_observability.py` |

---

## 4. System Architecture & Deterministic Domain Contracts

```mermaid
flowchart TD
    Client["Client / Streamlit UI"] --> API["FastAPI Router Layer (/api/v1/*)"]
    API --> Sanitizer["Prompt Boundary Sanitizer (build_turn_input_with_context)"]
    Sanitizer --> Coord["CoordinatorAgent (Immutable System Instruction)"]

    Coord -->|Catalog & Stock| ProdAgent["ProductAgent"]
    Coord -->|Quotes, Discounts & Tax| CalcAgent["CalculationAgent"]
    Coord -->|Orders, x402 Evidence & Escalation| OrdAgent["OrderSupportAgent / GeneralAgent"]

    ProdAgent --> CatalogSvc["catalog_db.py & pricing.py (SQLite)"]
    CalcAgent --> PricingSvc["pricing.py (Decimal ROUND_HALF_UP + 10^6 SIM-USDC)"]
    OrdAgent --> VerifySvc["order_verification.py & orders_db.py (SQLite)"]
```

### 4.1 Fixed-Point Pricing & Dual Atomic Units (`backend/services/pricing.py`)
* **Zero Caller-Supplied Prices**: `calculate_quote` rejects any item payload containing `unit_price`, `price`, `discount_percent`, or `discount` (`error_code="UNAUTHORIZED_PRICE_OVERRIDE"`).
* **Inventory & Split-Line Protection**: Quantities are aggregated by canonical `product_id` across all cart lines before checking SQLite `stock`, preventing multi-line split bypasses (`OUT_OF_STOCK` / `INSUFFICIENT_STOCK`).
* **Allowlisted Discounts & Caps**: Discount codes are validated against SQLite `discount_codes` (`WELCOME10`: 10% capped at \$200.00; `VIP15`: 15% capped at \$500.00; `SAVE5`: 5% capped at \$100.00; `EXPIRED20`: rejected with `EXPIRED_DISCOUNT_CODE`).
* **Dual Representation**: Every quote returns `Decimal` fields quantized to `0.01` with `ROUND_HALF_UP`, integer `total_cents` ($10^2$), and integer `total_sim_usdc_micros` ($10^6$).

### 4.2 Reference Orders & Evidence Ledger (`backend/database/orders_db.py`)
Six canonical orders are idempotently seeded in SQLite for deterministic verification via `GET /api/v1/orders/{order_id}` and `POST /api/v1/orders/{order_id}/verify-claim`:

| Order ID | Product (`total_sim_usdc_micros`) | `PurchaseEvidence` (`x402`) | `GrantEvidence` | Deterministic Dispute Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **`ORD-1001`** | `Dell XPS 15` (`1,299,000,000`) | `settled`, `charge_count=1`, `authorized_by_mandate=True` | `delivered`, `return_eligible=True` | All dispute claims -> `contradicted` (`priority="low"`) |
| **`ORD-1002`** | `iPhone 15 Pro` (`999,000,000`) | `settled`, `charge_count=1`, `authorized_by_mandate=True` | `pending`, `delivered_at=None` | `charged_not_delivered` -> `confirmed` (`SETTLED_WITHOUT_DELIVERY_GRANT`, `priority="high"`) |
| **`ORD-1003`** | `Logitech MX Master 3S` (`99,000,000`) | `settled`, `charge_count=2`, `authorized_by_mandate=True` | `delivered`, `return_eligible=True` | `duplicate_charge` -> `confirmed` (`MULTIPLE_SETTLED_CHARGES`, `priority="high"`) |
| **`ORD-1004`** | `iPhone 15 Pro` (`999,000,000`) | `settled`, `charge_count=1`, `authorized_by_mandate=False` | `shipped` | `unauthorized_purchase` -> `confirmed` (`MISSING_KYA_MANDATE_AUTHORIZATION`, `priority="critical"`) |
| **`ORD-1005`** | `Sony WH-1000XM5` (`399,000,000`) | `settled`, `charge_count=1`, `authorized_by_mandate=True` | `denied` | `charged_but_denied` -> `confirmed` (`SETTLED_BUT_ACCESS_GRANT_DENIED`, `priority="high"`) |
| **`ORD-1006`** | `Logitech MX Master 3S` (`99,000,000`) | `None` (Missing settlement evidence) | `None` (Missing grant evidence) | Any claim -> `unverifiable` (`MISSING_EVIDENCE`, `priority="high"`) |

---

## 5. Reproducible Offline Verification & Evaluation

All tests and evaluation suites run **100% offline** with outbound TCP/UDP sockets blocked by `tests/conftest.py` (`block_outbound_network`) and isolated temporary SQLite databases (`isolated_sqlite_dbs`).

### 5.1 Linting, Test Suite & Offline Evaluation Commands

```bash
# 1. Static analysis & import formatting check
uv run ruff check

# 2. Full offline characterization, commerce, evidence, observability & production hardening suite (66 tests)
uv run pytest -v

# 3. Standalone 24-case deterministic evaluation harness
uv run python -m eval.runner
```

### 5.2 Offline Evaluation Scorecard (`eval/cases.jsonl`)

| Category | Total | Passed | Failed | Pass Rate |
| :--- | :---: | :---: | :---: | :---: |
| `catalog_grounding` | 6 | 6 | 0 | 100.0% |
| `deterministic_pricing` | 6 | 6 | 0 | 100.0% |
| `evidence_verification` | 6 | 6 | 0 | 100.0% |
| `adversarial_security` | 6 | 6 | 0 | 100.0% |
| **TOTAL** | **24** | **24** | **0** | **100.0%** |

### 5.3 Running the Application Locally

```bash
# Clone the repository and sync the environment
git clone https://github.com/AlvLeoAI/multi-agent-ecommerce-support.git
cd multi-agent-ecommerce-support
uv sync

# Start the FastAPI backend (from repository root)
PYTHONPATH=backend uv run uvicorn main:app --reload --port 8000

# Start the Streamlit frontend in a second terminal
uv run streamlit run frontend/Home.py
```

---

## 6. Honest Scope & Known Limitations

1. **Local SQLite Persistence vs. Distributed Concurrency**: Catalog, session memory, orders, tickets, and quality metrics use local SQLite files (`my_agent_data.db` and `ecommerce_agent.db`) for self-contained reproducibility. High-concurrency multi-replica deployments (e.g., Cloud Run with $>1$ instance) require migrating to PostgreSQL / Cloud SQL with `SELECT ... FOR UPDATE` row-level inventory locking.
2. **Offline ADK Runner Double vs. Live Gemini 2.0 Flash Execution**: Automated tests and `eval/runner.py` execute deterministically offline without calling external LLM endpoints. Live multi-turn agent orchestration via `POST /api/v1/chat/` requires a valid `GOOGLE_API_KEY` environment variable.
3. **Heuristic Token Estimation**: `QualityTracker` uses a deterministic character-based heuristic (`len(text) // 4`) so token accounting remains reproducible across offline and stubbed runs; production cost accounting should read exact `usage_metadata` token counts from the model provider response.
4. **Simulated `x402` Settlement Evidence**: `PurchaseEvidence` records in `orders_db.py` represent pre-recorded settlement envelopes matching the schema of `Agentic-Payments-Lab` rather than live on-chain RPC queries.
