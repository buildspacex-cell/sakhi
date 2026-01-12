-- Energy layer schema (derived, deterministic, auditable)
-- Idempotent migration for Supabase Postgres

-- Enable UUID generation (safe no-op if already present)
create extension if not exists "pgcrypto";

-- 1) energy_summary_weekly
-- Immutable weekly energy summaries computed from elemental summaries.
create table if not exists energy_summary_weekly (
  id uuid primary key default gen_random_uuid(),

  person_id uuid not null,
  week_start date not null,

  activation_load numeric(4,3) not null,
  grounding numeric(4,3) not null,
  circulation numeric(4,3) not null,
  recovery_efficiency numeric(4,3) not null,

  confidence numeric(4,3) not null,

  created_at timestamptz not null default now(),

  unique (person_id, week_start)
);

create index if not exists idx_energy_summary_weekly_person_week on energy_summary_weekly (person_id, week_start);

-- 2) energy_summary_monthly
-- Smoothed monthly energy trends derived from weekly energy summaries.
create table if not exists energy_summary_monthly (
  id uuid primary key default gen_random_uuid(),

  person_id uuid not null,
  month_start date not null,

  activation_load numeric(4,3) not null,
  grounding numeric(4,3) not null,
  circulation numeric(4,3) not null,
  recovery_efficiency numeric(4,3) not null,

  confidence numeric(4,3) not null,

  created_at timestamptz not null default now(),

  unique (person_id, month_start)
);

create index if not exists idx_energy_summary_monthly_person_month on energy_summary_monthly (person_id, month_start);

-- 3) personal_model_energy
-- Slow-moving energy traits (integrator, not state).
create table if not exists personal_model_energy (
  person_id uuid primary key,

  baseline jsonb not null,          -- typical energy profile
  volatility jsonb not null,        -- how reactive energy is
  recovery_profile jsonb not null,  -- recovery half-life / efficiency
  circulation_stability jsonb not null,

  confidence numeric(4,3) not null default 0.5,

  updated_at timestamptz not null default now()
);
