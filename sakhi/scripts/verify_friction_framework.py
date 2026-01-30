#!/usr/bin/env python3
"""
Deterministic Intelligence Verification Script

Run this script to verify that ALL deterministic intelligence fields are properly
set up in the database and being populated correctly.

This includes:
- Friction Framework (operating_system, state_vector, guna_vector)
- Brain States (long_term, forecast_state, coherence_state, alignment_state)
- Cache Tables (daily_reflection, morning_preview, focus_path, etc.)
- Engine States (nudge_state, continuity)
- Computed States (reflection_trace)

Usage:
    python sakhi/scripts/verify_friction_framework.py

Or from the sakhi directory:
    python -m scripts.verify_friction_framework
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import date

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEMO_USER_ID = os.getenv("DEMO_USER_ID", "565bdb63-124b-4692-a039-846fddceff90")

# Expected tables for deterministic intelligence
EXPECTED_TABLES = [
    "personal_model",
    "memory_episodic",
    "daily_reflection_cache",
    "daily_closure_cache",
    "morning_preview_cache",
    "morning_ask_cache",
    "morning_momentum_cache",
    "micro_momentum_cache",
    "micro_recovery_cache",
    "focus_path_cache",
    "mini_flow_cache",
    "micro_journey_cache",
    "continuity_state",
    "reflection_trace",
]

PERSONAL_MODEL_COLUMNS = [
    "operating_system",
    "life_context",
    "decision_profile",
    "long_term",
    "nudge_state",
    "forecast_state",
    "coherence_state",
    "alignment_state",
]

EPISODIC_COLUMNS = ["state_vector", "guna_vector", "emotional_state", "rhythm_state"]


async def main():
    from sakhi.apps.api.core.db import q

    print("\n" + "=" * 70)
    print("DETERMINISTIC INTELLIGENCE DATABASE VERIFICATION")
    print("=" * 70)

    issues = []
    today = date.today()

    # ==========================================================================
    # 1. SCHEMA VERIFICATION
    # ==========================================================================
    print("\n[1] SCHEMA VERIFICATION")
    print("-" * 40)

    # Check tables
    print("\nRequired tables:")
    for table in EXPECTED_TABLES:
        row = await q(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = $1
            """,
            table,
            one=True,
        )
        if row:
            print(f"  [OK] {table}")
        else:
            print(f"  [MISSING] {table}")
            issues.append(f"Missing table: {table}")

    # Check personal_model columns
    print("\npersonal_model columns:")
    for col in PERSONAL_MODEL_COLUMNS:
        row = await q(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'personal_model' AND column_name = $1
            """,
            col,
            one=True,
        )
        if row:
            print(f"  [OK] {col} ({row.get('data_type')})")
        else:
            print(f"  [MISSING] {col}")
            issues.append(f"Missing column: personal_model.{col}")

    # Check memory_episodic columns
    print("\nmemory_episodic columns:")
    for col in EPISODIC_COLUMNS:
        row = await q(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'memory_episodic' AND column_name = $1
            """,
            col,
            one=True,
        )
        if row:
            print(f"  [OK] {col} ({row.get('data_type')})")
        else:
            print(f"  [MISSING] {col}")
            issues.append(f"Missing column: memory_episodic.{col}")

    # ==========================================================================
    # 2. DEMO USER DATA CHECK
    # ==========================================================================
    print(f"\n[2] DEMO USER DATA ({DEMO_USER_ID})")
    print("-" * 40)

    # Check personal_model
    pm_row = await q(
        """
        SELECT
            operating_system,
            life_context,
            decision_profile,
            long_term,
            updated_at
        FROM personal_model
        WHERE person_id = $1
        """,
        DEMO_USER_ID,
        one=True,
    )

    if not pm_row:
        print("  [WARNING] Demo user not found in personal_model")
    else:
        print("\npersonal_model fields:")

        # Operating System
        os_data = pm_row.get("operating_system")
        if os_data:
            if isinstance(os_data, str):
                os_data = json.loads(os_data)
            print(f"  operating_system:")
            print(f"    type: {os_data.get('type', 'N/A')}")
            print(f"    primary: {os_data.get('primary', 'N/A')}")
            print(f"    secondary: {os_data.get('secondary', 'N/A')}")
            dosha = os_data.get("dosha_baseline", {})
            print(f"    dosha_baseline: vata={dosha.get('vata')}, pitta={dosha.get('pitta')}, kapha={dosha.get('kapha')}")
        else:
            print("  operating_system: [NOT SET] - User needs to complete onboarding")

        # Life Context
        life_ctx = pm_row.get("life_context")
        if life_ctx:
            if isinstance(life_ctx, str):
                life_ctx = json.loads(life_ctx)
            print(f"  life_context: {json.dumps(life_ctx, indent=4)[:200]}...")
        else:
            print("  life_context: [NOT SET]")

        # Decision Profile
        dec_profile = pm_row.get("decision_profile")
        if dec_profile:
            if isinstance(dec_profile, str):
                dec_profile = json.loads(dec_profile)
            print(f"  decision_profile: {json.dumps(dec_profile, indent=4)[:200]}...")
        else:
            print("  decision_profile: [NOT SET]")

        # Long-term layers
        long_term = pm_row.get("long_term")
        if long_term:
            if isinstance(long_term, str):
                long_term = json.loads(long_term)
            layers = long_term.get("layers", {})
            print(f"  long_term.layers:")
            print(f"    emotion: {'SET' if layers.get('emotion') else 'NOT SET'}")
            print(f"    mind: {'SET' if layers.get('mind') else 'NOT SET'}")
            print(f"    soul: {'SET' if layers.get('soul') else 'NOT SET'}")
        else:
            print("  long_term: [NOT SET]")

    # ==========================================================================
    # 3. EPISODIC ENTRIES CHECK
    # ==========================================================================
    print(f"\n[3] EPISODIC ENTRIES WITH STATE VECTORS")
    print("-" * 40)

    # Count total entries
    count_row = await q(
        "SELECT COUNT(*) as total FROM memory_episodic WHERE person_id = $1",
        DEMO_USER_ID,
        one=True,
    )
    total_entries = (count_row or {}).get("total", 0)
    print(f"  Total episodic entries: {total_entries}")

    # Count entries with state vectors
    sv_count_row = await q(
        """
        SELECT COUNT(*) as total
        FROM memory_episodic
        WHERE person_id = $1 AND state_vector IS NOT NULL
        """,
        DEMO_USER_ID,
        one=True,
    )
    sv_count = (sv_count_row or {}).get("total", 0)
    print(f"  Entries with state_vector: {sv_count}")

    gv_count_row = await q(
        """
        SELECT COUNT(*) as total
        FROM memory_episodic
        WHERE person_id = $1 AND guna_vector IS NOT NULL
        """,
        DEMO_USER_ID,
        one=True,
    )
    gv_count = (gv_count_row or {}).get("total", 0)
    print(f"  Entries with guna_vector: {gv_count}")

    # Show recent entries with state vectors
    if sv_count > 0 or gv_count > 0:
        print("\n  Recent entries with state vectors:")
        recent = await q(
            """
            SELECT id, state_vector, guna_vector, created_at
            FROM memory_episodic
            WHERE person_id = $1
              AND (state_vector IS NOT NULL OR guna_vector IS NOT NULL)
            ORDER BY created_at DESC
            LIMIT 3
            """,
            DEMO_USER_ID,
        )
        for i, row in enumerate(recent or []):
            sv = row.get("state_vector")
            gv = row.get("guna_vector")
            if isinstance(sv, str):
                sv = json.loads(sv)
            if isinstance(gv, str):
                gv = json.loads(gv)
            print(f"\n    Entry {i+1} ({row.get('created_at')}):")
            if sv:
                dosha = sv.get("dosha", {})
                print(f"      state_vector.dosha: v={dosha.get('vata')}, p={dosha.get('pitta')}, k={dosha.get('kapha')}")
            if gv:
                print(f"      guna_vector: s={gv.get('sattva')}, r={gv.get('rajas')}, t={gv.get('tamas')}")

    # ==========================================================================
    # 4. FRICTION STATE SIMULATION
    # ==========================================================================
    print(f"\n[4] FRICTION STATE SIMULATION")
    print("-" * 40)

    if pm_row and pm_row.get("operating_system") and sv_count > 0:
        os_data = pm_row.get("operating_system")
        if isinstance(os_data, str):
            os_data = json.loads(os_data)
        baseline = os_data.get("dosha_baseline", {"vata": 0.33, "pitta": 0.33, "kapha": 0.34})

        # Get recent state vectors
        recent_sv = await q(
            """
            SELECT state_vector
            FROM memory_episodic
            WHERE person_id = $1
              AND state_vector IS NOT NULL
              AND created_at > NOW() - INTERVAL '7 days'
            ORDER BY created_at DESC
            LIMIT 10
            """,
            DEMO_USER_ID,
        )

        if recent_sv:
            current = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}
            count = 0
            for row in recent_sv:
                sv = row.get("state_vector")
                if isinstance(sv, str):
                    sv = json.loads(sv)
                dosha = (sv or {}).get("dosha", {})
                if dosha:
                    current["vata"] += dosha.get("vata", 0)
                    current["pitta"] += dosha.get("pitta", 0)
                    current["kapha"] += dosha.get("kapha", 0)
                    count += 1

            if count > 0:
                current = {k: round(v / count, 2) for k, v in current.items()}

                print(f"  Baseline dosha: {baseline}")
                print(f"  Current dosha (avg of {count} entries): {current}")

                # Calculate drift
                drifts = {
                    "vata": round(current["vata"] - baseline.get("vata", 0.33), 2),
                    "pitta": round(current["pitta"] - baseline.get("pitta", 0.33), 2),
                    "kapha": round(current["kapha"] - baseline.get("kapha", 0.34), 2),
                }
                print(f"  Drift from baseline: {drifts}")

                # Determine friction state
                max_drift = max(drifts.items(), key=lambda x: x[1])
                if max_drift[1] >= 0.25:
                    friction_map = {
                        "vata": "Chaos Friction",
                        "pitta": "Intensity Friction",
                        "kapha": "Stagnation Friction",
                    }
                    print(f"\n  FRICTION STATE: {friction_map.get(max_drift[0], 'Unknown')}")
                    print(f"  Severity: {'High' if max_drift[1] >= 0.4 else 'Moderate'}")
                else:
                    print(f"\n  FRICTION STATE: Balanced (no significant drift)")
        else:
            print("  [SKIP] No recent state vectors in last 7 days")
    else:
        print("  [SKIP] Missing baseline or state vectors")

    # ==========================================================================
    # 5. CACHE TABLES
    # ==========================================================================
    print(f"\n[5] CACHE TABLES (Today: {today})")
    print("-" * 40)

    # Daily reflection
    dr_row = await q(
        "SELECT summary FROM daily_reflection_cache WHERE person_id = $1 AND reflection_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  daily_reflection: {'SET' if dr_row else 'NOT SET'}")

    # Daily closure
    dc_row = await q(
        "SELECT summary FROM daily_closure_cache WHERE person_id = $1 AND closure_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  evening_closure: {'SET' if dc_row else 'NOT SET'}")

    # Morning context
    mp_row = await q(
        "SELECT focus_areas FROM morning_preview_cache WHERE person_id = $1 AND preview_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  morning_preview: {'SET' if mp_row else 'NOT SET'}")

    ma_row = await q(
        "SELECT question FROM morning_ask_cache WHERE person_id = $1 AND ask_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  morning_ask: {'SET' if ma_row else 'NOT SET'}")

    mm_row = await q(
        "SELECT momentum_hint FROM morning_momentum_cache WHERE person_id = $1 AND momentum_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  morning_momentum: {'SET' if mm_row else 'NOT SET'}")

    # Micro context
    micro_mom = await q(
        "SELECT nudge FROM micro_momentum_cache WHERE person_id = $1 AND nudge_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  micro_momentum: {'SET' if micro_mom else 'NOT SET'}")

    micro_rec = await q(
        "SELECT nudge FROM micro_recovery_cache WHERE person_id = $1 AND recovery_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  micro_recovery: {'SET' if micro_rec else 'NOT SET'}")

    # Scaffolds
    fp_row = await q(
        "SELECT anchor_step FROM focus_path_cache WHERE person_id = $1 AND path_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  focus_path: {'SET' if fp_row else 'NOT SET'}")

    mf_row = await q(
        "SELECT warmup_step FROM mini_flow_cache WHERE person_id = $1 AND flow_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  mini_flow: {'SET' if mf_row else 'NOT SET'}")

    mj_row = await q(
        "SELECT journey FROM micro_journey_cache WHERE person_id = $1",
        DEMO_USER_ID, one=True,
    )
    print(f"  micro_journey: {'SET' if mj_row else 'NOT SET'}")

    # ==========================================================================
    # 6. ADDITIONAL STATES
    # ==========================================================================
    print(f"\n[6] ADDITIONAL STATES")
    print("-" * 40)

    # Continuity state
    cont_row = await q(
        "SELECT * FROM continuity_state WHERE person_id = $1",
        DEMO_USER_ID, one=True,
    )
    print(f"  continuity_state: {'SET' if cont_row else 'NOT SET'}")

    # Reflection trace
    rt_row = await q(
        "SELECT * FROM reflection_trace WHERE person_id = $1 ORDER BY created_at DESC LIMIT 1",
        DEMO_USER_ID, one=True,
    )
    print(f"  reflection_trace: {'SET' if rt_row else 'NOT SET'}")

    # Personal model states
    state_row = await q(
        """
        SELECT nudge_state, forecast_state, coherence_state, alignment_state
        FROM personal_model
        WHERE person_id = $1
        """,
        DEMO_USER_ID,
        one=True,
    )
    if state_row:
        print(f"  nudge_state: {'SET' if state_row.get('nudge_state') else 'NOT SET'}")
        print(f"  forecast_state: {'SET' if state_row.get('forecast_state') else 'NOT SET'}")
        print(f"  coherence_state: {'SET' if state_row.get('coherence_state') else 'NOT SET'}")
        print(f"  alignment_state: {'SET' if state_row.get('alignment_state') else 'NOT SET'}")

    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    # Check data issues
    if not pm_row or not pm_row.get("operating_system"):
        issues.append("Demo user missing operating_system (onboarding not complete)")

    if sv_count == 0:
        issues.append("No episodic entries with state_vector (episodic consolidation not writing vectors)")

    if issues:
        print(f"\n[ISSUES FOUND: {len(issues)}]")
        for issue in issues:
            print(f"  - {issue}")
        print("\nRECOMMENDATIONS:")
        if any("Missing table" in i for i in issues):
            print("  - Run pending database migrations")
        if any("Missing column" in i for i in issues):
            print("  - Run migration: 0028_friction_framework.sql and 0032_episodic_state_vectors.sql")
        if any("onboarding" in i for i in issues):
            print("  - Complete onboarding flow for demo user")
        if any("episodic consolidation" in i for i in issues):
            print("  - Trigger episodic consolidation job or wait for new entries")
    else:
        print("\n[OK] All schema checks passed!")

    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
