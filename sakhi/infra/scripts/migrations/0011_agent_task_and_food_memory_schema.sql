-- Migration: 0011_agent_task_and_food_memory_schema
-- Date: 2026-02-27
-- Description: Add food memory tables and widen agent task plan statuses for confirmation flows.

-- =============================================================================
-- UP Migration
-- =============================================================================

CREATE TABLE IF NOT EXISTS food_experiences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id),
    dish_name TEXT NOT NULL,
    cuisine TEXT,
    restaurant_name TEXT,
    restaurant_location TEXT,
    meal_type TEXT,
    context TEXT,
    rating TEXT,
    notes TEXT,
    companions JSONB NOT NULL DEFAULT '[]'::jsonb,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    want_again BOOLEAN NOT NULL DEFAULT FALSE,
    price_paid DOUBLE PRECISION,
    experience_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_food_experiences_person_date
ON food_experiences(person_id, experience_date DESC);

CREATE INDEX IF NOT EXISTS idx_food_experiences_person_restaurant
ON food_experiences(person_id, restaurant_name);

CREATE INDEX IF NOT EXISTS idx_food_experiences_person_cuisine
ON food_experiences(person_id, cuisine);

CREATE TABLE IF NOT EXISTS restaurant_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id),
    restaurant_name TEXT NOT NULL,
    location TEXT,
    cuisine TEXT,
    visit_count INTEGER NOT NULL DEFAULT 0,
    last_visit TIMESTAMPTZ,
    notes TEXT,
    want_to_return BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_restaurant_memory_person_restaurant
ON restaurant_memory(person_id, restaurant_name);

CREATE INDEX IF NOT EXISTS idx_restaurant_memory_person_cuisine
ON restaurant_memory(person_id, cuisine);

ALTER TABLE IF EXISTS agent_task_plans
    DROP CONSTRAINT IF EXISTS agent_task_plans_status_check;

ALTER TABLE IF EXISTS agent_task_plans
    ADD CONSTRAINT agent_task_plans_status_check
    CHECK (
        status = ANY (
            ARRAY[
                'planned'::text,
                'pending_confirmation'::text,
                'confirmed'::text,
                'rejected'::text,
                'executing'::text,
                'completed'::text,
                'failed'::text,
                'cancelled'::text,
                'expired'::text
            ]
        )
    );

-- =============================================================================
-- Notes
-- =============================================================================
-- This migration restores food memory storage and aligns agent task persistence
-- with the confirmation lifecycle used by the chat bridge.
