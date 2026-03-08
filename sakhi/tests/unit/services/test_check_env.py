from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_check_env_module():
    root = Path(__file__).resolve().parents[4]
    module_path = root / "sakhi" / "infra" / "scripts" / "check_env.py"
    spec = importlib.util.spec_from_file_location("check_env_module", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base_local_env() -> dict[str, str]:
    return {
        "DATABASE_URL": "postgresql://localhost:5432/sakhi",
        "OPENAI_API_KEY": "sk-test-123",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
        "ENCRYPTION_KEY": "super-secret-encryption-key-32chars",
        "SAKHI_ENCRYPTION_KEY": "fernet-abc",
        "SAKHI_JOURNAL_MASTER_KEY": "journal-master-secret-1234567890-abcdef",
        "MODEL_CHAT": "gpt-4o-mini",
        "MODEL_TOOL": "gpt-4o-mini",
        "MODEL_REFLECT": "gpt-4o-mini",
        "MODEL_EMBED": "text-embedding-3-small",
        "NEXT_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY": "anon-key",
        "NEXT_PUBLIC_API_BASE_URL": "https://api.example.com",
        "REDIS_URL": "redis://localhost:6379/0",
    }


def test_validate_local_profile_passes_with_complete_env():
    module = _load_check_env_module()
    missing = module.validate_env(_base_local_env(), profile="local")
    assert missing == []


def test_validate_local_profile_allows_api_base_alias():
    module = _load_check_env_module()
    values = _base_local_env()
    values.pop("NEXT_PUBLIC_API_BASE_URL")
    values["NEXT_PUBLIC_API_BASE"] = "https://api.example.com"
    missing = module.validate_env(values, profile="local")
    assert missing == []


def test_validate_local_profile_requires_redis_when_queue_enabled():
    module = _load_check_env_module()
    values = _base_local_env()
    values.pop("REDIS_URL")
    values["SAKHI_DISABLE_QUEUE"] = "0"
    missing = module.validate_env(values, profile="local")
    assert "REDIS_URL" in missing


def test_validate_local_profile_skips_redis_when_inline_queue():
    module = _load_check_env_module()
    values = _base_local_env()
    values.pop("REDIS_URL")
    values["SAKHI_DISABLE_QUEUE"] = "1"
    missing = module.validate_env(values, profile="local")
    assert "REDIS_URL" not in missing


def test_validate_monitoring_contract_when_enabled():
    module = _load_check_env_module()
    values = _base_local_env()
    values["SAKHI_MONITORING_ENABLED"] = "1"
    missing = module.validate_env(values, profile="local")
    assert "SAKHI_ALERT_WEBHOOK_URL or SAKHI_SENTRY_DSN" in missing


def test_validate_monitoring_contract_satisfied_by_webhook():
    module = _load_check_env_module()
    values = _base_local_env()
    values["SAKHI_MONITORING_ENABLED"] = "1"
    values["SAKHI_ALERT_WEBHOOK_URL"] = "https://hooks.example.com/sakhi"
    missing = module.validate_env(values, profile="local")
    assert "SAKHI_ALERT_WEBHOOK_URL or SAKHI_SENTRY_DSN" not in missing


def test_validate_monitoring_contract_rejects_invalid_threshold():
    module = _load_check_env_module()
    values = _base_local_env()
    values["SAKHI_MONITORING_ENABLED"] = "1"
    values["SAKHI_ALERT_WEBHOOK_URL"] = "https://hooks.example.com/sakhi"
    values["SAKHI_ALERT_CRASH_LOOP_THRESHOLD"] = "0"
    missing = module.validate_env(values, profile="local")
    assert "SAKHI_ALERT_CRASH_LOOP_THRESHOLD" in missing


def test_validate_ci_profile_minimal_contract():
    module = _load_check_env_module()
    values = {"DATABASE_URL": "postgresql://localhost:5432/sakhi", "ENCRYPTION_KEY": "secret-key"}
    missing = module.validate_env(values, profile="ci")
    assert missing == []


def test_validate_prod_api_requires_journal_master_key():
    module = _load_check_env_module()
    values = _base_local_env()
    values.pop("SAKHI_JOURNAL_MASTER_KEY")
    missing = module.validate_env(values, profile="prod_api")
    assert "SAKHI_JOURNAL_MASTER_KEY" in missing


def test_validate_prod_api_passes_with_journal_master_key():
    module = _load_check_env_module()
    values = _base_local_env()
    values["SAKHI_JOURNAL_MASTER_KEY"] = "journal-master-secret-1234567890-abcdef"
    missing = module.validate_env(values, profile="prod_api")
    assert "SAKHI_JOURNAL_MASTER_KEY" not in missing


def test_validate_local_profile_rejects_short_journal_master_key():
    module = _load_check_env_module()
    values = _base_local_env()
    values["SAKHI_JOURNAL_MASTER_KEY"] = "too-short"
    missing = module.validate_env(values, profile="local")
    assert "SAKHI_JOURNAL_MASTER_KEY" in missing


def test_validate_prod_api_requires_operator_token_when_internal_routes_enabled():
    module = _load_check_env_module()
    values = _base_local_env()
    values["SAKHI_ENABLE_INTERNAL_ROUTES_IN_PROD"] = "1"
    missing = module.validate_env(values, profile="prod_api")
    assert "SAKHI_OPERATOR_ACCESS_TOKEN" in missing


def test_validate_prod_api_accepts_operator_token_when_internal_routes_enabled():
    module = _load_check_env_module()
    values = _base_local_env()
    values["SAKHI_ENABLE_INTERNAL_ROUTES_IN_PROD"] = "1"
    values["SAKHI_OPERATOR_ACCESS_TOKEN"] = "breakglass-operator-token-1234567890"
    missing = module.validate_env(values, profile="prod_api")
    assert "SAKHI_OPERATOR_ACCESS_TOKEN" not in missing
