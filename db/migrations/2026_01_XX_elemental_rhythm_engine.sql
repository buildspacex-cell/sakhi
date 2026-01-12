-- Sakhi Deterministic Rhythm Engine / Elemental Intelligence Schema
-- Idempotent migration for Supabase Postgres

-- Enable UUID generation (safe no-op if already present)
create extension if not exists "pgcrypto";

-- 1) elemental_signal_stm
-- Volatile, short-term elemental projections derived from STM signals.
-- TTL via expires_at; safe to delete after expiry. No interpretation stored.
create table if not exists elemental_signal_stm (
  id uuid primary key default gen_random_uuid(),

  person_id uuid not null,
  source_signal_id uuid not null, -- logical reference to memory_short_term.id
  source_type text not null check (source_type in ('journal', 'signal')),

  dimension text not null check (dimension in ('body', 'mind', 'emotion')),

  earth numeric(4,3) not null default 0,
  water numeric(4,3) not null default 0,
  fire  numeric(4,3) not null default 0,
  air   numeric(4,3) not null default 0,
  ether numeric(4,3) not null default 0,
  magnitude numeric(6,3) not null default 0,

  confidence numeric(4,3) not null default 1.0,

  created_at timestamptz not null default now(),
  expires_at timestamptz not null
);

create index if not exists idx_elemental_signal_stm_person_created on elemental_signal_stm (person_id, created_at);
create index if not exists idx_elemental_signal_stm_expires on elemental_signal_stm (expires_at);
create unique index if not exists uq_elemental_signal_stm_source_dim on elemental_signal_stm (person_id, source_signal_id, dimension);

-- 2) elemental_summary_weekly
-- Immutable weekly rollups that survive STM expiry.
create table if not exists elemental_summary_weekly (
  id uuid primary key default gen_random_uuid(),

  person_id uuid not null,
  week_start date not null,

  dimension text not null check (dimension in ('body', 'mind', 'emotion')),

  earth_avg numeric(4,3) not null,
  water_avg numeric(4,3) not null,
  fire_avg  numeric(4,3) not null,
  air_avg   numeric(4,3) not null,
  ether_avg numeric(4,3) not null,

  volatility numeric(4,3) not null,
  signal_count integer not null,

  created_at timestamptz not null default now(),

  unique (person_id, week_start, dimension)
);

create index if not exists idx_elemental_summary_weekly_person_week on elemental_summary_weekly (person_id, week_start);

-- 3) elemental_summary_monthly
-- Slow aggregation for long-range trends; immutable after write.
create table if not exists elemental_summary_monthly (
  id uuid primary key default gen_random_uuid(),

  person_id uuid not null,
  month_start date not null,

  dimension text not null check (dimension in ('body', 'mind', 'emotion')),

  earth_avg numeric(4,3) not null,
  water_avg numeric(4,3) not null,
  fire_avg  numeric(4,3) not null,
  air_avg   numeric(4,3) not null,
  ether_avg numeric(4,3) not null,

  volatility numeric(4,3) not null,
  week_count integer not null,

  created_at timestamptz not null default now(),

  unique (person_id, month_start, dimension)
);

create index if not exists idx_elemental_summary_monthly_person_month on elemental_summary_monthly (person_id, month_start);

-- 4) personal_model_elemental
-- Slow-changing ledger of long-term elemental traits; updated by promotion pipelines.
create table if not exists personal_model_elemental (
  person_id uuid primary key,

  baseline jsonb not null,      -- average elemental balance by dimension
  volatility jsonb not null,    -- reactivity per dimension
  recovery_rate jsonb not null, -- how fast imbalances settle
  coupling jsonb not null,      -- cross-dimension influence

  confidence numeric(4,3) not null default 0.5,

  updated_at timestamptz not null default now()
);

-- 5) elemental_episode_link
-- Links episodic memories to elemental patterns without embedding elements in the episode record.
create table if not exists elemental_episode_link (
  id uuid primary key default gen_random_uuid(),

  episode_id uuid not null, -- references memory_episodic.id
  person_id uuid not null,

  dominant_dimension text not null,
  dominant_elements text[] not null,

  created_at timestamptz not null default now()
);

create index if not exists idx_elemental_episode_link_person_episode on elemental_episode_link (person_id, episode_id);

-- Validation notes:
-- - STM data (elemental_signal_stm) expires via expires_at and can be safely pruned.
-- - Weekly/monthly aggregates persist beyond STM expiry for history.
-- - Episodic memory stays clean; links are external via elemental_episode_link.
-- - personal_model_elemental is a slow ledger; updates are controlled and auditable.
