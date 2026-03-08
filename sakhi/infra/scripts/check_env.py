"""Validate environment-variable contracts for local, CI, and production profiles."""

from __future__ import annotations

import argparse
import os
from typing import Mapping

from dotenv import load_dotenv

TRUTHY_VALUES = {"1", "true", "yes", "y", "on"}

PROFILE_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    # Local runtime: API + worker + web proxy variables expected in .env/.env.local.
    "local": (
        "DATABASE_URL",
        "OPENAI_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "ENCRYPTION_KEY",
        "SAKHI_ENCRYPTION_KEY",
        "MODEL_CHAT",
        "MODEL_TOOL",
        "MODEL_REFLECT",
        "MODEL_EMBED",
        "SAKHI_JOURNAL_MASTER_KEY",
        "NEXT_PUBLIC_SUPABASE_URL",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY",
        "NEXT_PUBLIC_API_BASE_URL",
        "REDIS_URL",
    ),
    # Railway API/worker profile.
    "prod_api": (
        "DATABASE_URL",
        "OPENAI_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "ENCRYPTION_KEY",
        "SAKHI_ENCRYPTION_KEY",
        "SAKHI_JOURNAL_MASTER_KEY",
        "MODEL_CHAT",
        "MODEL_TOOL",
        "MODEL_REFLECT",
        "MODEL_EMBED",
        "REDIS_URL",
    ),
    # Vercel web profile.
    "prod_web": (
        "NEXT_PUBLIC_SUPABASE_URL",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY",
        "NEXT_PUBLIC_API_BASE_URL",
    ),
    # CI profile keeps checks aligned with test workflow contract.
    "ci": (
        "DATABASE_URL",
        "ENCRYPTION_KEY",
    ),
}

# Canonical env keys mapped to fallback aliases.
ALIASES: dict[str, tuple[str, ...]] = {
    "SUPABASE_SERVICE_ROLE_KEY": ("SUPABASE_SERVICE_KEY",),
    "NEXT_PUBLIC_API_BASE_URL": ("NEXT_PUBLIC_API_BASE",),
}

PLACEHOLDER_VALUES = {
    "OPENAI_API_KEY": {"sk-...", "your-openai-key"},
    "ENCRYPTION_KEY": {"replace-with-32-plus-char-secret", "your-strong-32-plus-char-secret"},
    "SAKHI_ENCRYPTION_KEY": {"your-fernet-key"},
    "SAKHI_JOURNAL_MASTER_KEY": {"replace-with-journal-master-key"},
    "SAKHI_OPERATOR_ACCESS_TOKEN": {"replace-with-breakglass-token"},
    "SUPABASE_URL": {"https://<project-ref>.supabase.co"},
    "SUPABASE_SERVICE_ROLE_KEY": {"your-service-role-key"},
    "NEXT_PUBLIC_SUPABASE_URL": {"https://<project-ref>.supabase.co"},
    "NEXT_PUBLIC_SUPABASE_ANON_KEY": {"your-anon-key"},
}


def _as_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in TRUTHY_VALUES


def _is_positive_int(value: str | None, *, minimum: int = 1) -> bool:
    if value is None or not str(value).strip():
        return True
    try:
        parsed = int(str(value).strip())
    except Exception:
        return False
    return parsed >= minimum


def _resolve_value(values: Mapping[str, str], name: str) -> str | None:
    direct = values.get(name)
    if direct:
        return direct
    for alias in ALIASES.get(name, ()):
        aliased = values.get(alias)
        if aliased:
            return aliased
    return None


def _is_placeholder(name: str, value: str) -> bool:
    value_clean = value.strip()
    if not value_clean:
        return True
    candidates = PLACEHOLDER_VALUES.get(name, set())
    if value_clean in candidates:
        return True
    if name == "OPENAI_API_KEY" and value_clean.endswith("..."):
        return True
    return False


def validate_env(
    values: Mapping[str, str],
    *,
    profile: str,
    strict_monitoring: bool = False,
) -> list[str]:
    if profile not in PROFILE_REQUIREMENTS:
        raise ValueError(f"Unsupported profile: {profile}")

    required = list(PROFILE_REQUIREMENTS[profile])
    # Inline queue mode does not require Redis in local profile.
    if profile == "local" and _resolve_value(values, "SAKHI_DISABLE_QUEUE") == "1":
        required = [key for key in required if key != "REDIS_URL"]

    missing: list[str] = []
    for name in required:
        value = _resolve_value(values, name)
        if not value or _is_placeholder(name, value):
            missing.append(name)
            continue
        if name == "SAKHI_JOURNAL_MASTER_KEY" and len(value.strip()) < 32:
            missing.append(name)

    monitoring_enabled = strict_monitoring or _as_bool(_resolve_value(values, "SAKHI_MONITORING_ENABLED"))
    if profile in {"local", "prod_api"} and monitoring_enabled:
        has_webhook = bool(_resolve_value(values, "SAKHI_ALERT_WEBHOOK_URL"))
        has_sentry = bool(_resolve_value(values, "SAKHI_SENTRY_DSN"))
        if not has_webhook and not has_sentry:
            missing.append("SAKHI_ALERT_WEBHOOK_URL or SAKHI_SENTRY_DSN")
        threshold_specs = (
            ("SAKHI_ALERT_DEDUPE_WINDOW_SEC", 30),
            ("SAKHI_ALERT_AUTH_FAILURE_THRESHOLD", 2),
            ("SAKHI_ALERT_AUTH_FAILURE_WINDOW_SEC", 60),
            ("SAKHI_ALERT_CRASH_LOOP_THRESHOLD", 2),
            ("SAKHI_ALERT_CRASH_LOOP_WINDOW_SEC", 60),
            ("SAKHI_ALERT_DATA_ACCESS_SPIKE_THRESHOLD", 2),
            ("SAKHI_ALERT_DATA_ACCESS_WINDOW_SEC", 60),
        )
        for key, minimum in threshold_specs:
            if not _is_positive_int(_resolve_value(values, key), minimum=minimum):
                missing.append(key)

    if profile == "prod_api" and _as_bool(_resolve_value(values, "SAKHI_ENABLE_INTERNAL_ROUTES_IN_PROD")):
        operator_token = (_resolve_value(values, "SAKHI_OPERATOR_ACCESS_TOKEN") or "").strip()
        if (
            not operator_token
            or _is_placeholder("SAKHI_OPERATOR_ACCESS_TOKEN", operator_token)
            or len(operator_token) < 24
        ):
            missing.append("SAKHI_OPERATOR_ACCESS_TOKEN")

    return missing


def _load_dotenv_for_profile(profile: str) -> None:
    # Local workflow contract explicitly allows .env.local to override .env.
    if profile == "local":
        load_dotenv(".env", override=False)
        load_dotenv(".env.local", override=True)
        return
    # Other profiles rely on the current process environment.


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=tuple(PROFILE_REQUIREMENTS.keys()),
        default="local",
        help="Validation profile to enforce.",
    )
    parser.add_argument(
        "--strict-monitoring",
        action="store_true",
        help="Require at least one monitoring sink (Sentry or webhook).",
    )
    parser.add_argument(
        "--no-dotenv",
        action="store_true",
        help="Do not load .env/.env.local files before validation.",
    )
    args = parser.parse_args(argv)

    if not args.no_dotenv:
        _load_dotenv_for_profile(args.profile)

    missing = validate_env(
        os.environ,
        profile=args.profile,
        strict_monitoring=args.strict_monitoring,
    )
    if missing:
        print(f"Environment contract failed ({args.profile}):")
        for name in missing:
            print(f"- Missing or invalid: {name}")
        return 1

    print(f"Environment contract passed ({args.profile}).")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
