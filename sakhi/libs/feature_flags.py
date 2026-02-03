"""
Feature Flags for Sakhi

Simple feature flag system for gradual rollouts and A/B testing.
Flags can be set via environment variables or database.

Usage:
    from sakhi.libs.feature_flags import is_enabled, get_flag

    if is_enabled("new_conversation_engine"):
        # Use new engine
    else:
        # Use old engine

    # With percentage rollout
    if is_enabled("new_memory_recall", person_id=user_id):
        # Deterministic per-user rollout
"""

import os
import hashlib
from typing import Optional, Dict, Any
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Flag Definitions
# ─────────────────────────────────────────────────────────────────────────────

# Define all feature flags here with their defaults
# Format: "flag_name": {"default": bool, "rollout_pct": int (0-100), "description": str}
FLAG_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    # Conversation & Response
    "new_conversation_engine_v3": {
        "default": False,
        "rollout_pct": 0,
        "description": "Enable v3 conversation engine with improved context",
    },
    "adaptive_response_enhanced": {
        "default": True,
        "rollout_pct": 100,
        "description": "Enhanced adaptive response pipeline",
    },

    # Memory System
    "memory_graph_enabled": {
        "default": True,
        "rollout_pct": 100,
        "description": "Enable graph-based memory relations",
    },
    "memory_hybrid_recall": {
        "default": True,
        "rollout_pct": 100,
        "description": "Hybrid semantic + keyword memory recall",
    },

    # Workers
    "async_workers_enabled": {
        "default": True,
        "rollout_pct": 100,
        "description": "Run workers asynchronously via Redis queue",
    },
    "episodic_consolidation_v21": {
        "default": True,
        "rollout_pct": 100,
        "description": "Use v21 episodic consolidation algorithm",
    },

    # Ayurvedic Engine
    "ayurvedic_causal_reasoning": {
        "default": True,
        "rollout_pct": 100,
        "description": "Enable causal reasoning for Ayurvedic insights",
    },
    "ayurvedic_pattern_learning": {
        "default": True,
        "rollout_pct": 100,
        "description": "Learn patterns from user behavior",
    },

    # Agent / Vision
    "desktop_agent_enabled": {
        "default": False,
        "rollout_pct": 0,
        "description": "Enable desktop agent integration",
    },
    "vision_loop_enabled": {
        "default": False,
        "rollout_pct": 0,
        "description": "Enable vision/screenshot analysis",
    },

    # Mesh / Multi-Sakhi
    "mesh_coordination_enabled": {
        "default": False,
        "rollout_pct": 0,
        "description": "Enable inter-Sakhi mesh coordination",
    },

    # Experimental
    "experimental_soul_engine": {
        "default": False,
        "rollout_pct": 0,
        "description": "Experimental soul/identity engine",
    },
    "experimental_rhythm_forecast": {
        "default": False,
        "rollout_pct": 0,
        "description": "Experimental rhythm forecasting",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Core Functions
# ─────────────────────────────────────────────────────────────────────────────

def get_flag(flag_name: str) -> Dict[str, Any]:
    """
    Get flag definition with current value.

    Args:
        flag_name: Name of the flag

    Returns:
        Dict with flag definition and current enabled state
    """
    if flag_name not in FLAG_DEFINITIONS:
        logger.warning(f"Unknown feature flag: {flag_name}")
        return {"default": False, "rollout_pct": 0, "description": "Unknown flag"}

    flag_def = FLAG_DEFINITIONS[flag_name].copy()

    # Check environment override
    env_key = f"SAKHI_FLAG_{flag_name.upper()}"
    env_value = os.environ.get(env_key)

    if env_value is not None:
        flag_def["env_override"] = env_value.lower() in ("1", "true", "yes")

    return flag_def


def is_enabled(
    flag_name: str,
    person_id: Optional[str] = None,
) -> bool:
    """
    Check if a feature flag is enabled.

    Args:
        flag_name: Name of the flag to check
        person_id: Optional user ID for percentage rollouts

    Returns:
        True if the flag is enabled for this context
    """
    flag = get_flag(flag_name)

    # Environment override takes precedence
    if "env_override" in flag:
        return flag["env_override"]

    # Check percentage rollout
    rollout_pct = flag.get("rollout_pct", 0)

    if rollout_pct >= 100:
        return True
    if rollout_pct <= 0:
        return flag.get("default", False)

    # Deterministic rollout based on person_id
    if person_id:
        hash_input = f"{flag_name}:{person_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        user_bucket = hash_value % 100
        return user_bucket < rollout_pct

    # No person_id, use default
    return flag.get("default", False)


def set_flag_env(flag_name: str, enabled: bool) -> None:
    """
    Set a flag via environment variable (useful for testing).

    Args:
        flag_name: Name of the flag
        enabled: Whether to enable it
    """
    env_key = f"SAKHI_FLAG_{flag_name.upper()}"
    os.environ[env_key] = "1" if enabled else "0"


def clear_flag_env(flag_name: str) -> None:
    """
    Clear a flag's environment override.

    Args:
        flag_name: Name of the flag
    """
    env_key = f"SAKHI_FLAG_{flag_name.upper()}"
    os.environ.pop(env_key, None)


# ─────────────────────────────────────────────────────────────────────────────
# Utility Functions
# ─────────────────────────────────────────────────────────────────────────────

def list_all_flags() -> Dict[str, Dict[str, Any]]:
    """
    List all defined flags with their current state.

    Returns:
        Dict of flag_name -> flag definition with current state
    """
    return {name: get_flag(name) for name in FLAG_DEFINITIONS}


def get_enabled_flags(person_id: Optional[str] = None) -> list[str]:
    """
    Get list of all enabled flags.

    Args:
        person_id: Optional user ID for rollout checks

    Returns:
        List of enabled flag names
    """
    return [
        name for name in FLAG_DEFINITIONS
        if is_enabled(name, person_id)
    ]


def flags_context(person_id: Optional[str] = None) -> Dict[str, bool]:
    """
    Get all flags as a simple bool dict for logging/debugging.

    Args:
        person_id: Optional user ID

    Returns:
        Dict of flag_name -> bool
    """
    return {
        name: is_enabled(name, person_id)
        for name in FLAG_DEFINITIONS
    }


# ─────────────────────────────────────────────────────────────────────────────
# Context Manager for Testing
# ─────────────────────────────────────────────────────────────────────────────

class flag_override:
    """
    Context manager for temporarily overriding flags in tests.

    Usage:
        with flag_override("new_feature", True):
            # Flag is enabled in this block
            assert is_enabled("new_feature")
        # Flag reverts to original state
    """

    def __init__(self, flag_name: str, enabled: bool):
        self.flag_name = flag_name
        self.enabled = enabled
        self.original_value = None

    def __enter__(self):
        env_key = f"SAKHI_FLAG_{self.flag_name.upper()}"
        self.original_value = os.environ.get(env_key)
        set_flag_env(self.flag_name, self.enabled)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        env_key = f"SAKHI_FLAG_{self.flag_name.upper()}"
        if self.original_value is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = self.original_value
        return False
