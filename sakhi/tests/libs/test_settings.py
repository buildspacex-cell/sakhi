from sakhi.libs.schemas import get_settings


def test_get_settings_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("SAKHI_APP_NAME", "TestSakhi")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/postgres")
    monkeypatch.setenv("LLM_ROUTER", "OPENROUTER")
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.app_name == "TestSakhi"
    assert settings.redis_url.startswith("redis://")
    assert settings.postgres_dsn == "postgresql://user:pass@localhost:5432/postgres"
    assert settings.llm_router == "OPENROUTER"
