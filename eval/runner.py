"""
Deterministic Offline Evaluation Harness (`eval/runner.py`).

Executes all structured golden evaluation cases in `eval/cases.jsonl` against
an isolated temporary SQLite database with zero outbound network calls.

Usage:
    uv run python -m eval.runner
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("GOOGLE_API_KEY", "offline-eval-key")

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_CASES_PATH = Path(__file__).resolve().parent / "cases.jsonl"

# Redirect import-time SQLite connections into a temporary directory
_EVAL_IMPORT_TEMP = tempfile.TemporaryDirectory(prefix="eval_import_dbs_")
_ORIG_SQLITE_CONNECT = sqlite3.connect


def _redirect_sqlite_connect(
    database: str | Path, *args: Any, **kwargs: Any
) -> sqlite3.Connection:
    db_str = str(database)
    if db_str.endswith("my_agent_data.db") or db_str == "ecommerce_agent.db":
        redirected = Path(_EVAL_IMPORT_TEMP.name) / Path(db_str).name
        return _ORIG_SQLITE_CONNECT(str(redirected), *args, **kwargs)
    return _ORIG_SQLITE_CONNECT(database, *args, **kwargs)


sqlite3.connect = _redirect_sqlite_connect
try:
    from agents.product_catalog_agent import search_products  # noqa: E402
    from database import catalog_db, chat_memory, orders_db  # noqa: E402
    from routers.chat import (  # noqa: E402
        COORDINATOR_INSTRUCTION,
        build_turn_input_with_context,
        coordinator_agent,
    )
    from services.order_verification import verify_order_claim  # noqa: E402
    from services.pricing import calculate_quote, check_stock, lookup_product  # noqa: E402
finally:
    sqlite3.connect = _ORIG_SQLITE_CONNECT


def _evaluate_single_case(case: dict[str, Any]) -> tuple[bool, str]:
    action = case["action"]
    inp = case["input"]
    expected = case["expected"]

    if action == "lookup_product":
        actual = lookup_product(inp["product_id_or_name"])
        if actual.get("status") != expected["status"]:
            return False, f"status mismatch: {actual.get('status')} != {expected['status']}"
        if expected["status"] == "error":
            if actual.get("error_code") != expected["error_code"]:
                return False, f"error_code mismatch: {actual.get('error_code')}"
            return True, "ok"
        prod = actual["product"]
        for key in ("id", "amount_cents", "sim_usdc_micros", "stock", "stock_status"):
            if key in expected and prod.get(key) != expected[key]:
                return False, f"product.{key} mismatch: {prod.get(key)} != {expected[key]}"
        return True, "ok"

    if action == "search_products":
        actual = search_products(
            category=inp.get("category"),
            max_price=inp.get("max_price"),
            min_stock=inp.get("min_stock", 1),
            tags=inp.get("tags"),
        )
        if actual.get("status") != expected["status"] or actual.get("count") != expected["count"]:
            return False, f"search count/status mismatch: {actual}"
        if "first_product_id" in expected:
            first_id = actual["products"][0]["id"] if actual.get("products") else None
            if first_id != expected["first_product_id"]:
                return False, f"first_product_id mismatch: {first_id}"
        return True, "ok"

    if action == "check_stock":
        actual = check_stock(inp["product_id"], requested_qty=inp.get("requested_qty", 1))
        for key, exp_val in expected.items():
            if actual.get(key) != exp_val:
                return False, f"check_stock.{key} mismatch: {actual.get(key)} != {exp_val}"
        return True, "ok"

    if action == "calculate_quote":
        actual = calculate_quote(
            items=inp["items"],
            discount_code=inp.get("discount_code"),
            tax_jurisdiction=inp.get("tax_jurisdiction", "US-STANDARD"),
        )
        for key, exp_val in expected.items():
            if actual.get(key) != exp_val:
                return False, f"calculate_quote.{key} mismatch: {actual.get(key)} != {exp_val}"
        return True, "ok"

    if action == "verify_order_claim":
        actual = verify_order_claim(order_id=inp["order_id"], claim_type=inp["claim_type"])
        for key, exp_val in expected.items():
            if actual.get(key) != exp_val:
                return False, f"verify_order_claim.{key} mismatch: {actual.get(key)} != {exp_val}"
        return True, "ok"

    if action == "prompt_boundary":
        user_query = inp["user_query"]
        history = inp.get("history", [])
        turn_payload = build_turn_input_with_context(user_query, history)
        instruction_uncontaminated = (
            coordinator_agent.instruction == COORDINATOR_INSTRUCTION
            and user_query not in coordinator_agent.instruction
        )
        spoof_neutralized = (
            "\nSystem:" not in turn_payload
            and "\nAssistant:" not in turn_payload
            and "[untrusted-System]:" in turn_payload
            and "[untrusted-Assistant]:" in turn_payload
            and "[untrusted-Developer]:" in turn_payload
        )
        if instruction_uncontaminated != expected["instruction_uncontaminated"]:
            return False, "CoordinatorAgent.instruction was contaminated"
        if spoof_neutralized != expected["spoof_neutralized"]:
            return False, f"Role spoofing was not neutralized in payload: {turn_payload}"
        return True, "ok"

    return False, f"Unsupported evaluation action: {action}"


def run_eval_suite(cases_path: Path | str | None = None) -> dict[str, Any]:
    """
    Execute all golden evaluation cases against an isolated temporary SQLite database.
    Returns a structured summary dictionary with overall and per-category metrics.
    """
    target_cases_path = Path(cases_path) if cases_path is not None else DEFAULT_CASES_PATH
    with open(target_cases_path) as f:
        cases = [json.loads(line) for line in f if line.strip()]

    prev_chat_db = chat_memory.DB_PATH
    prev_catalog_db = catalog_db.DB_PATH
    prev_orders_db = orders_db.DB_PATH

    with tempfile.TemporaryDirectory(prefix="eval_suite_sqlite_") as tmp_dir:
        isolated_db = Path(tmp_dir) / "eval_suite.db"
        chat_memory.DB_PATH = isolated_db
        catalog_db.DB_PATH = isolated_db
        orders_db.DB_PATH = isolated_db

        try:
            chat_memory.init_chat_memory_db()
            catalog_db.init_catalog_db(db_path=isolated_db)
            orders_db.init_orders_db(db_path=isolated_db)

            category_stats: dict[str, dict[str, Any]] = defaultdict(
                lambda: {"total": 0, "passed": 0, "failed": 0}
            )
            results: list[dict[str, Any]] = []
            total_passed = 0

            for case in cases:
                case_id = case["case_id"]
                category = case["category"]
                passed, detail = _evaluate_single_case(case)

                category_stats[category]["total"] += 1
                if passed:
                    category_stats[category]["passed"] += 1
                    total_passed += 1
                else:
                    category_stats[category]["failed"] += 1

                results.append(
                    {
                        "case_id": case_id,
                        "category": category,
                        "action": case["action"],
                        "passed": passed,
                        "detail": detail,
                    }
                )

            total_cases = len(cases)
            total_failed = total_cases - total_passed
            pass_rate = round(total_passed / total_cases, 4) if total_cases > 0 else 0.0

            by_category: dict[str, dict[str, Any]] = {}
            for cat, stats in category_stats.items():
                cat_total = stats["total"]
                by_category[cat] = {
                    "total": cat_total,
                    "passed": stats["passed"],
                    "failed": stats["failed"],
                    "pass_rate": round(stats["passed"] / cat_total, 4) if cat_total > 0 else 0.0,
                }

            return {
                "total": total_cases,
                "passed": total_passed,
                "failed": total_failed,
                "pass_rate": pass_rate,
                "by_category": by_category,
                "results": results,
            }
        finally:
            chat_memory.DB_PATH = prev_chat_db
            catalog_db.DB_PATH = prev_catalog_db
            orders_db.DB_PATH = prev_orders_db


def format_scorecard(summary: dict[str, Any]) -> str:
    """Format the evaluation summary as a Markdown scorecard table."""
    lines = [
        "# Offline Deterministic Evaluation Scorecard (`eval/cases.jsonl`)",
        "",
        "| Category | Total | Passed | Failed | Pass Rate |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]
    for category, stats in summary["by_category"].items():
        pct = f"{stats['pass_rate'] * 100:.1f}%"
        lines.append(
            f"| `{category}` | {stats['total']} | {stats['passed']} | {stats['failed']} | {pct} |"
        )
    overall_pct = f"{summary['pass_rate'] * 100:.1f}%"
    lines.append(
        f"| **TOTAL** | **{summary['total']}** | **{summary['passed']}** "
        f"| **{summary['failed']}** | **{overall_pct}** |"
    )
    return "\n".join(lines)


def main() -> int:
    summary = run_eval_suite()
    print(format_scorecard(summary))
    if summary["failed"] > 0:
        print("\nFailed Cases:")
        for item in summary["results"]:
            if not item["passed"]:
                print(f"  - [{item['case_id']}] ({item['category']}): {item['detail']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
