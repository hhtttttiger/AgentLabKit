"""Memory API — route-level contract tests (no DB required).

These tests verify route definitions, schema shapes, and method semantics.
For full integration tests, run with Docker:
    docker compose exec backend pytest tests/test_memory.py -v
"""

from __future__ import annotations

import pytest


# ── Deactivate semantics (M1 fix) ─────────────────────────────────────

def test_deactivate_uses_patch_method():
    """M1 fix: soft-deactivate should use PATCH, hard-delete uses DELETE."""
    from modules.memory.router import router

    deactivate_routes = [
        route for route in router.routes
        if route.path == "/{memory_id}"
    ]
    assert deactivate_routes, "Route /{memory_id} not registered"

    methods = set()
    for route in deactivate_routes:
        methods.update(route.methods)
    assert "PATCH" in methods, f"Soft-deactivate (PATCH) missing in {methods}"
    assert "DELETE" in methods, f"Hard-delete (DELETE) missing in {methods}"


# ── Schema contract (C1 fix) ──────────────────────────────────────────

def test_memory_search_request_no_user_id_field():
    """C1 fix: MemorySearchRequest should not accept client-provided user_id."""
    from modules.memory.schemas import MemorySearchRequest

    fields = MemorySearchRequest.model_fields
    assert "user_id" not in fields, (
        "user_id must not be in MemorySearchRequest — derived from JWT via CurrentUser"
    )


def test_consolidate_request_no_user_id_field():
    """C1 fix: ConsolidateRequest should not accept client-provided user_id."""
    from modules.memory.schemas import ConsolidateRequest

    fields = ConsolidateRequest.model_fields
    assert "user_id" not in fields, (
        "user_id must not be in ConsolidateRequest — derived from JWT via CurrentUser"
    )


# ── Enum validation (M3 fix) ──────────────────────────────────────────

def test_consolidate_request_rejects_invalid_memory_type():
    """M3 fix: ConsolidateRequest validates memory_type against MemoryType enum."""
    from pydantic import ValidationError
    from modules.memory.schemas import ConsolidateRequest

    with pytest.raises(ValidationError):
        ConsolidateRequest(memory_type="bogus", batch_size=5)


def test_consolidate_request_accepts_valid_types():
    """M3 fix: Valid memory_type values should pass validation."""
    from modules.memory.schemas import ConsolidateRequest

    for valid_type in ("episodic", "semantic", "procedural"):
        req = ConsolidateRequest(memory_type=valid_type, batch_size=10)
        assert req.memory_type == valid_type


# ── Config validation (H5 fix) ────────────────────────────────────────

def test_memory_settings_rejects_out_of_range_values():
    """H5 fix: Numeric constraints should reject out-of-range values."""
    from pydantic import ValidationError
    from memory.config import MemorySettings

    with pytest.raises(ValidationError):
        MemorySettings(retrieval_top_k=200)  # max is 100

    with pytest.raises(ValidationError):
        MemorySettings(relevance_threshold=2.0)  # max is 1.0

    with pytest.raises(ValidationError):
        MemorySettings(max_memories_per_user=10)  # min is 100


# ── Auth dependency (C1 fix) ──────────────────────────────────────────

def test_router_endpoints_use_current_user():
    """C1 fix: All endpoints should use CurrentUser, not userId query param."""
    from modules.memory.router import router

    for route in router.routes:
        if not hasattr(route, 'endpoint'):
            continue
        # Get the original function (unwrap any decorators)
        func = route.endpoint
        import inspect
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        # Verify 'userId' is NOT a parameter (C1 fix)
        assert "userId" not in params, (
            f"Route {route.path} [{','.join(route.methods)}] "
            f"still has 'userId' param — should use CurrentUser"
        )
