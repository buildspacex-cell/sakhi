from __future__ import annotations

from sakhi.apps.api.core.operator_access import is_operator_protected_path
from sakhi.apps.api.core.operator_access import validate_operator_access


def test_protected_path_detection_covers_operator_routes():
    assert is_operator_protected_path("/admin/metrics")
    assert is_operator_protected_path("/debug/person_snapshot")
    assert is_operator_protected_path("/memory/dev/reset")
    assert is_operator_protected_path("/system/audit")
    assert not is_operator_protected_path("/memory/123/weekly")
    assert not is_operator_protected_path("/v2/turn")


def test_validate_operator_access_requires_token_configuration():
    decision = validate_operator_access({}, expected_token="")
    assert decision.ok is False
    assert decision.code == "operator_token_not_configured"


def test_validate_operator_access_rejects_missing_breakglass_headers():
    headers = {"x-sakhi-operator-token": "valid-token"}
    decision = validate_operator_access(headers, expected_token="valid-token")
    assert decision.ok is False
    assert decision.code == "operator_id_missing"


def test_validate_operator_access_accepts_valid_breakglass_headers():
    headers = {
        "x-sakhi-operator-token": "valid-token",
        "x-sakhi-operator-id": "oncall.engineer",
        "x-sakhi-approval-ref": "INC-2026-03-08-001",
        "x-sakhi-breakglass-reason": "Investigating production incident with user consent.",
    }
    decision = validate_operator_access(headers, expected_token="valid-token")
    assert decision.ok is True
    assert decision.code == "ok"
    assert decision.operator_id == "oncall.engineer"
    assert decision.approval_ref == "INC-2026-03-08-001"

