from pathlib import Path


def test_build88_migration_contains_expected_sql():
    path = Path("infra/sql/20260124_build88_daily_reflection.sql")
    assert path.exists(), "Migration file for Build 88 is missing"
    sql = path.read_text()
    assert "daily_reflection_cache" in sql
    assert "daily_reflection_state" in sql
    assert "PRIMARY KEY (person_id, reflection_date)" in sql
